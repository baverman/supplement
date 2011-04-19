import pytest
import time

from supplement import watcher

@pytest.mark.slow
def test_watcher_must_call_uniq_handlers_on_file_change(tmpdir):
    f = tmpdir.join('test.py')
    f.write('content')

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

    watcher.monitor(str(f), on_change, changed1)
    watcher.monitor(str(f), on_change, changed1)
    watcher.monitor(str(f), on_change, changed2)
    watcher.monitor(str(f), change_on, changed2)

    f.write('ddddddd')

    time.sleep(2)
    assert changed1.data == [str(f)]
    assert changed2.data == [str(f), str(f)]

@pytest.mark.slow
def test_watcher_must_call_uniq_method_handlers_on_file_change(tmpdir):
    f = tmpdir.join('test.py')
    f.write('content')

    class Handler(object):
        def __init__(self):
            self.changed = []

        def on_change(self, filename):
            self.changed.append(filename)

    h1 = Handler()
    h2 = Handler()

    watcher.monitor(str(f), h1.on_change)
    watcher.monitor(str(f), h1.on_change)
    watcher.monitor(str(f), h2.on_change)

    f.write('ddddddd')

    time.sleep(2)
    assert h1.changed == [str(f)]
    assert h2.changed == [str(f)]