import time
import threading
import logging

class Monitor(object):
    def __init__(self):
        self.handlers = {}

    def file_changed(self, filename):
        logging.getLogger(__name__).info('File changed %s', filename)
        for v in self.handlers[filename]:
            v[0](filename, *v[1:])

    def monitor(self, filename, handler, *args):
        if filename not in self.handlers:
            self._monitor(filename)

        self.handlers.setdefault(filename, set()).add((handler,) + args)


class DummyMonitor(Monitor):
    def __init__(self):
        Monitor.__init__(self)
        self.files = set()

    def _monitor(self, filename):
        self.files.add(filename)

    def boo(self):
        map(self.file_changed, self.files)


class FallbackMonitor(Monitor):
    def __init__(self):
        Monitor.__init__(self)
        self.files = {}
        self.timeout = 5

    def start(self):
        t = threading.Thread(target=self.watch_for_changes)
        t.daemon = True
        t.start()

    def _monitor(self, filename):
        from os.path import getmtime
        if filename not in self.files:
            logging.getLogger(__name__).info('Monitor changes for %s', filename)
            self.files[filename] = getmtime(filename)

    def watch_for_changes(self):
        from os.path import getmtime
        while True:
            for f, mtime in self.files.iteritems():
                new_mtime = getmtime(f)
                if new_mtime != mtime:
                    self.file_changed(f)

                self.files[f] = new_mtime

            time.sleep(self.timeout)

def get_monitor():
    return FallbackMonitor()