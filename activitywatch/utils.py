try:
    import sublime
except ImportError:  # outside Sublime Text, e.g. under pytest
    sublime = None  # type: ignore[assignment]


def log(msg: str) -> None:
    msg = "[aw-watcher-sublime] {}".format(msg)
    print(msg)
    if sublime is not None:
        sublime.status_message(msg)
