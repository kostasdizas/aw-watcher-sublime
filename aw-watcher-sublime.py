import sublime
import sublime_plugin

import webbrowser
from .activitywatch.api import ActivityWatchApi
from .activitywatch import utils

# globals
CLIENT_ID = "aw-watcher-sublime"
SETTINGS_FILE = "ActivityWatch Watcher.sublime-settings"
SETTINGS = {}
DEBUG = False
CONNECTED = False
api = ActivityWatchApi()


def plugin_loaded():
    global SETTINGS
    SETTINGS = sublime.load_settings(SETTINGS_FILE)

    utils.log("Initializing ActivityWatch plugin.")

    after_loaded()


def after_loaded():
    if DEBUG:
        utils.log("after_loaded() called")
    sync_settings()
    update_connection_status()
    SETTINGS.clear_on_change("ActivityWatch Watcher.settings")
    SETTINGS.add_on_change("ActivityWatch Watcher.settings", sync_settings)


def update_connection_status() -> None:
    global CONNECTED
    CONNECTED = api.check()

    if DEBUG:
        utils.log("Connected? {}".format(CONNECTED))


def sync_settings() -> None:
    updated_debug = SETTINGS.get("debug")

    global DEBUG
    if DEBUG != updated_debug:
        toggle_debugging(updated_debug)
        DEBUG = updated_debug

    hostname = SETTINGS.get("hostname")
    port = SETTINGS.get("port")
    heartbeat_frequency = SETTINGS.get("heartbeat_frequency")
    api.setup(CLIENT_ID, hostname, port, heartbeat_frequency)

    bucket_name = SETTINGS.get("bucket_name")
    api.ensure_bucket(bucket_name)


def toggle_debugging(enable: bool) -> None:
    if enable:
        api.enable_debugging()
    else:
        api.disable_debugging()


def get_file_name(view):
    return view.file_name() or view.name() or "untitled"


def get_project_name(view):
    window = view.window()
    project = "unknown"

    if hasattr(window, "project_data"):
        project = window.project_data()
    if not project:
        project = "unknown"
    if "name" in project:
        project = project.get("name")
    elif "folders" in project:
        for folder in project.get("folders"):
            if get_file_name(view).startswith(folder.get("path")):
                project = folder.get("path")
                break
    if DEBUG:
        utils.log("project: {}".format(project))
    return str(project)


def get_language(view):
    try:
        point = view.sel()[0].begin()
    except IndexError:
        return
    scopes = view.scope_name(point).strip().split(" ")
    if DEBUG:
        utils.log("scopes: {}".format(scopes))
    return scopes[0]


def correct_slashes(path):
    if DEBUG:
        utils.log("correct_slashes() called")
    return path.replace("\\", "/").replace("C:", "/C")


def handle_activity(view):
    if DEBUG:
        utils.log("handle_activity() fired")
    if not CONNECTED:
        active_window = sublime.active_window()
        if active_window:
            for view in active_window.views():
                view.set_status(
                    CLIENT_ID,
                    "[aw-watcher-sublime] Could not connect "
                    "to aw-server")
    event_data = {
        "file": correct_slashes(get_file_name(view)),
        "project": correct_slashes(get_project_name(view)),
        "language": get_language(view),
    }
    if DEBUG:
        utils.log("file: {}\n\tproject: {}\n\tlanguage: {}".format(
            event_data["file"],
            event_data["project"],
            event_data["language"]))
    bucket_name = SETTINGS.get("bucket_name")
    api.heartbeat(bucket_name, event_data)


class ActivityWatchListener(sublime_plugin.EventListener):

    def on_selection_modified_async(self, view):
        if DEBUG:
            utils.log("on_selection_modified_async fired")
        if CONNECTED:
            handle_activity(view)

    def on_modified_async(self, view):
        if DEBUG:
            utils.log("on_modified_async fired")
        if CONNECTED:
            handle_activity(view)


class AwWatcherSublimeOpenDashboardCommand(sublime_plugin.WindowCommand):
    def run(self):
        hostname = SETTINGS.get("hostname")
        port = SETTINGS.get("port")        
        webbrowser.open("http://{}:{}".format(hostname, port))

