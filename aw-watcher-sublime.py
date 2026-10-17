import sublime
import sublime_plugin

import threading
import webbrowser
from datetime import datetime, timezone
from typing import Any, Optional

from .activitywatch.api import ActivityWatchApi
from .activitywatch import utils

# globals
CLIENT_ID = "aw-watcher-sublime"
SETTINGS_FILE = "ActivityWatch Watcher.sublime-settings"
SETTINGS: sublime.Settings = None  # type: ignore[assignment]
DEBUG = False
CONNECTED = False
RECONNECT_FREQUENCY = 30
api = ActivityWatchApi()

_check_lock = threading.Lock()
_check_running = False
_last_check = datetime.min.replace(tzinfo=timezone.utc)


def plugin_loaded() -> None:
    global SETTINGS
    SETTINGS = sublime.load_settings(SETTINGS_FILE)

    utils.log("Initializing ActivityWatch plugin.")

    after_loaded()


def after_loaded() -> None:
    if DEBUG:
        utils.log("after_loaded() called")
    sync_settings()
    SETTINGS.clear_on_change("ActivityWatch Watcher.settings")
    SETTINGS.add_on_change("ActivityWatch Watcher.settings", sync_settings)


def sync_settings() -> None:
    updated_debug = bool(SETTINGS.get("debug"))

    global DEBUG
    if DEBUG != updated_debug:
        toggle_debugging(updated_debug)
        DEBUG = updated_debug

    hostname = SETTINGS.get("hostname")
    port = SETTINGS.get("port")
    heartbeat_frequency = SETTINGS.get("heartbeat_frequency")
    api.setup(CLIENT_ID, hostname, port, heartbeat_frequency)

    global RECONNECT_FREQUENCY
    reconnect = SETTINGS.get("reconnect_frequency", 30)
    RECONNECT_FREQUENCY = reconnect if isinstance(reconnect, int) else 30

    # initial connection
    request_connection_check(force=True)


def connection_checked(connected: bool) -> None:
    """Update connection status"""
    global CONNECTED, _check_running

    with _check_lock:
        _check_running = False

    was_connected = CONNECTED
    CONNECTED = connected

    if DEBUG:
        utils.log("Connected? {}".format(CONNECTED))

    if connected:
        if not was_connected:
            utils.log("connected to aw-server")
        set_status("")
    else:
        set_status("[aw-watcher-sublime] Could not connect to aw-server")


def request_connection_check(force: bool = False) -> None:
    """Check the connection on a worker thread."""
    global _check_running, _last_check

    now = datetime.now(timezone.utc)

    with _check_lock:
        if _check_running:
            # already reconnecting
            return
        if not force:
            waited = (now - _last_check).total_seconds()
            if waited < RECONNECT_FREQUENCY:
                return
        _check_running = True
        _last_check = now

    bucket_name = SETTINGS.get("bucket_name")

    def task() -> None:
        connected = api.connect(bucket_name)
        sublime.set_timeout(lambda: connection_checked(connected), 0)

    threading.Thread(target=task, daemon=True).start()


def set_status(message: str) -> None:
    """Update current window status"""
    window = sublime.active_window()
    if not window:
        return
    for open_view in window.views():
        open_view.set_status(CLIENT_ID, message)


def toggle_debugging(enable: bool) -> None:
    if enable:
        api.enable_debugging()
    else:
        api.disable_debugging()


def get_file_name(view: sublime.View) -> str:
    return view.file_name() or view.name() or "untitled"


def get_project_name(view: sublime.View) -> str:
    window = view.window()
    project_data = window.project_data() if window else None

    project = "unknown"
    if isinstance(project_data, dict):
        if "name" in project_data:
            project = str(project_data["name"])
        else:
            folders = project_data.get("folders")
            file_name = get_file_name(view)
            if isinstance(folders, list):
                for folder in folders:
                    if not isinstance(folder, dict):
                        continue
                    path = folder.get("path")
                    if isinstance(path, str) and file_name.startswith(path):
                        project = path
                        break

    if DEBUG:
        utils.log("project: {}".format(project))
    return project


def get_language(view: sublime.View) -> Optional[str]:
    try:
        point = view.sel()[0].begin()
    except IndexError:
        return None
    scopes = view.scope_name(point).strip().split(" ")
    if DEBUG:
        utils.log("scopes: {}".format(scopes))
    return scopes[0]


def correct_slashes(path: str) -> str:
    if DEBUG:
        utils.log("correct_slashes() called")
    return path.replace("\\", "/").replace("C:", "/C")


def handle_activity(view: sublime.View) -> None:
    global CONNECTED

    if DEBUG:
        utils.log("handle_activity() fired")

    if not CONNECTED:
        request_connection_check()
        return

    event_data = {
        "file": correct_slashes(get_file_name(view)),
        "project": correct_slashes(get_project_name(view)),
        "language": get_language(view),
    }
    if DEBUG:
        utils.log(
            "file: {}\n\tproject: {}\n\tlanguage: {}".format(
                event_data["file"], event_data["project"], event_data["language"]
            )
        )
    bucket_name = SETTINGS.get("bucket_name")

    if not api.heartbeat(bucket_name, event_data):
        # if a heartbreak fails, mark as disconnected and reconnect
        CONNECTED = False
        request_connection_check()


class ActivityWatchListener(sublime_plugin.EventListener):

    def on_selection_modified_async(self, view: sublime.View) -> None:
        if DEBUG:
            utils.log("on_selection_modified_async fired")
        handle_activity(view)

    def on_modified_async(self, view: sublime.View) -> None:
        if DEBUG:
            utils.log("on_modified_async fired")
        handle_activity(view)


class AwWatcherSublimeOpenDashboardCommand(sublime_plugin.WindowCommand):
    def run(self, **args: Any) -> None:
        hostname = SETTINGS.get("hostname")
        port = SETTINGS.get("port")
        webbrowser.open("http://{}:{}".format(hostname, port))
