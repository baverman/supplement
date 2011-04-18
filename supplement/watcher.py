import gio
import glib
import time
import threading

monitors = {}
handlers = {}
loop_thread = None

def file_changed(monitor, file1, file2, evt_type):
    if evt_type == gio.FILE_MONITOR_EVENT_CHANGES_DONE_HINT:
        fname = file1.get_path()
        for v in handlers[fname]:
            v[0](fname, *v[1:])

def monitor(filename, handler, *args):
    if not loop_thread:
        run_loop()

    if filename not in monitors:
        gfile = gio.File(filename)
        monitor = gfile.monitor_file()
        monitor.connect('changed', file_changed)
        monitors[filename] = monitor

    handlers.setdefault(filename, set()).add((handler,) + args)

def process_events():
    ctx = glib.main_context_default()
    while True:
        while ctx.pending():
            ctx.iteration(False)

        time.sleep(0.3)

def run_loop():
    global loop_thread
    loop_thread = threading.Thread(target=process_events)
    loop_thread.daemon = True
    loop_thread.start()
