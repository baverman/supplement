import time
import threading

handlers = {}
main_monitor = [None]

def file_changed(filename):
    for v in handlers[filename]:
        v[0](filename, *v[1:])


class FallbackMonitor(object):
    def __init__(self, callback):
        self.files = {}
        self.timeout = 5
        self.callback = callback

    def start(self):
        t = threading.Thread(target=self.watch_for_changes)
        t.daemon = True
        t.start()

    def monitor(self, filename):
        from os.path import getmtime
        if filename not in self.files:
            self.files[filename] = getmtime(filename)

    def watch_for_changes(self):
        from os.path import getmtime
        while True:
            for f, mtime in self.files.items():
                new_mtime = getmtime(f)
                if new_mtime != mtime:
                    self.callback(f)

                self.files[f] = new_mtime

            time.sleep(self.timeout)


Monitor = FallbackMonitor

def monitor(filename, handler, *args):
    m = main_monitor[0]
    if not m:
        m = main_monitor[0] = Monitor(file_changed)
        m.start()

    if filename not in handlers:
        m.monitor(filename)

    handlers.setdefault(filename, set()).add((handler,) + args)
