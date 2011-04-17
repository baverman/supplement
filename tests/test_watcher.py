from supplement import watcher
import time

def test_watcher_must_call_handler_on_file_change(tmpdir):
    f =  tmpdir.join('test.py')
    f.write('content')

    changed = []
    def on_change(fname):
        changed.append(fname)

    watcher.monitor(str(f), on_change)

    f.write('ddddddd')

    time.sleep(2)
    assert changed == [str(f)]