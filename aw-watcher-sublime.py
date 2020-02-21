import sublime
import sublime_plugin

from .activitywatch.api import ActivityWatchApi


class ActivityWatchListener(sublime_plugin.EventListener):
    connected = False
    hostname = None
    port = None
    heartbeat_freq = 0
    bucket_name = None
    client_id = "aw-watcher-sublime"

    def __init__(self, *args, **kwargs):
        sublime_plugin.EventListener.__init__(self, *args, **kwargs)

        self._load_settings()
        self.api = ActivityWatchApi(self.client_id, self.hostname,
                                    self.port, self.heartbeat_freq)
        self.api.debug = self.debug
        self.connected = self.api.check()
        if self.connected:
            self.api.ensure_bucket(self.bucket_name)
        else:
            active_window = sublime.active_window()
            if active_window:
                for view in active_window.views():
                    view.set_status(self.client_id,
                                    "[aw-watcher-sublime] Could not connect "
                                    "to aw-server")

    def _load_settings(self):
        settings = sublime.load_settings("aw-watcher-sublime.sublime-settings")

        self.hostname = settings.get("hostname", "localhost")
        self.port = settings.get("port", 5600)
        self.heartbeat_freq = settings.get("heartbeat_frequency", 10)
        self.bucket_name = settings.get("bucket_name", "aw-watcher-sublime")
        self.debug = settings.get("debug", False)

    def _get_project_name(self, view):
        window = view.window()
        project = "unknown"
        if hasattr(window, "project_data"):
            project = window.project_data()
        if not project:
            project = "unknown"
        if "name" in project:
            project = project.get("name")
        return project

    def _handle(self, view):
        event_data = {
            "file": view.file_name(),
            "project": self._get_project_name(view),
            "language": view.scope_name(view.sel()[-1].b).split(" ")[0]
        }
        self.api.heartbeat(self.bucket_name, event_data)

    def on_selection_modified_async(self, view):
        if self.connected:
            self._handle(view)

    def on_modified_async(self, view):
        if self.connected:
            self._handle(view)
