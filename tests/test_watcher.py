from supplement.watcher import DummyMonitor

def test_watcher_must_call_uniq_handlers_on_file_change():
    fname = 'test.py'

    # Wrap list with hashable object
    class Holder(object):
        def __init__(self):
            self.data = []

    def on_change(fname, l):
        l.data.append(fname)

    def change_on(fname, l):
        l.data.append(fname)

    changed1 = Holder()
    changed2 = Holder()

    watcher = DummyMonitor()
    watcher.monitor(fname, on_change, changed1)
    watcher.monitor(fname, on_change, changed1)
    watcher.monitor(fname, on_change, changed2)
    watcher.monitor(fname, change_on, changed2)

    watcher.boo()

    assert changed1.data == [fname]
    assert changed2.data == [fname, fname]

def test_watcher_must_call_uniq_method_handlers_on_file_change():
    fname = 'test.py'

    class Handler(object):
        def __init__(self):
            self.changed = []

        def on_change(self, filename):
            self.changed.append(filename)

    h1 = Handler()
    h2 = Handler()

    watcher = DummyMonitor()
    watcher.monitor(fname, h1.on_change)
    watcher.monitor(fname, h1.on_change)
    watcher.monitor(fname, h2.on_change)
    watcher.boo()

    assert h1.changed == [fname]
    assert h2.changed == [fname]