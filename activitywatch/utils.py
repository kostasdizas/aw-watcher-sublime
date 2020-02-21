import sublime


def log(msg):
    msg = '[aw-watcher-sublime] {}'.format(msg)
    print(msg)
    sublime.status_message(msg)
