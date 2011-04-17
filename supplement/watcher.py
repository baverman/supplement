import gio
import glib
import time
import threading

monitors = {}
handlers = {}
loop_thread = []

def file_changed(monitor, file1, file2, evt_type):
    if evt_type == gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT:
        fname = file1.get_path()
        for h, args in handlers[fname]:
            h(fname, *args)

def monitor(filename, handler, *args):
    try:
        loop_thread[0]
    except IndexError:
        run_loop()

    if filename not in monitors:
        gfile = gio.File(filename)
        monitor = gfile.monitor_file()
        monitor.connect('changed', file_changed)
        monitors[filename] = monitor

    handlers.setdefault(filename, []).append((handler, args))

def process_events():
    ctx = glib.main_context_default()
    while True:
        while ctx.pending():
            ctx.iteration(False)

        time.sleep(0.3)

def run_loop():
    t = threading.Thread(target=process_events)
    t.daemon = True
    t.start()

    loop_thread.append(t)