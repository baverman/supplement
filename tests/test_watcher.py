import pytest

from supplement import watcher
import time

@pytest.mark.slow
def test_watcher_must_call_uniq_handlers_on_file_change(tmpdir):
    f = tmpdir.join('test.py')
    f.write('content')

    class Holder(object):
        def __init__(self):
            self.data = []

    def on_change(fname, l):
        l.data.append(fname)

    changed1 = Holder()
    changed2 = Holder()

    watcher.monitor(str(f), on_change, changed1)
    watcher.monitor(str(f), on_change, changed1)
    watcher.monitor(str(f), on_change, changed2)

    f.write('ddddddd')

    time.sleep(2)
    assert changed1.data== [str(f)]
    assert changed2.data == [str(f)]