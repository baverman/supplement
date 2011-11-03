import sys
from pickle import loads, dumps

from supplement.project import Project
from supplement.assistant import assist, get_location, get_docstring, get_fixed_source
from supplement.scope import get_scope_at
from supplement.watcher import get_monitor
from supplement.fixer import sanitize_encoding

class Server(object):
    def __init__(self, conn):
        self.conn = conn
        self.projects = {}
        self.configs = {}
        self.monitor = get_monitor()
        self.monitor.start()

    def configure_project(self, path, config):
        self.configs[path] = config
        self.projects[path] = self.create_project(path)

    def create_project(self, path):
        config = self.configs.get(path, {})
        config.setdefault('hooks', []).insert(0, 'supplement.hooks.override')
        p = Project(path, self.configs.get(path, {}), monitor=self.monitor)
        return p

    def get_project(self, path):
        try:
            return self.projects[path]
        except KeyError:
            pass

        p = self.projects[path] = self.create_project(path)
        return p

    def process(self, name, args, kwargs):
        try:
            is_ok = True
            result = getattr(self, name)(*args, **kwargs)
        except Exception as e:
            import traceback
            traceback.print_exc()
            is_ok = False
            result = e.__class__.__name__, str(e)

        return result, is_ok

    def get_fixed_source(self, path, source):
        return get_fixed_source(self.get_project(path), source)

    def assist(self, path, source, position, filename):
        return assist(self.get_project(path), source, position, filename)

    def get_location(self, path, source, position, filename):
        return get_location(self.get_project(path), source, position, filename)

    def get_docstring(self, path, source, position, filename):
        return get_docstring(self.get_project(path), source, position, filename)

    def get_scope(self, path, source, lineno, filename, continous):
        return get_scope_at(
            self.get_project(path), sanitize_encoding(source), lineno,
                filename, continous=continous).fullname

    def run(self):
        conn = self.conn
        while True:
            if conn.poll(1):
                try:
                    args = loads(conn.recv_bytes())
                except EOFError:
                    break
                except Exception:
                    import traceback
                    traceback.print_exc()
                    break

                if args[0] == 'close':
                    conn.close()
                    break
                else:
                    result, is_ok = self.process(*args)
                    try:
                        self.conn.send_bytes(dumps((result, is_ok), 2))
                    except:
                        import traceback
                        traceback.print_exc()

if __name__ == '__main__':
    import os
    from multiprocessing.connection import Listener
    import logging

    if 'SUPP_LOG_LEVEL' in os.environ:
        level = int(os.environ['SUPP_LOG_LEVEL'])
    else:
        level = logging.ERROR

    logger = logging.getLogger('supplement')
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(name)s %(levelname)s: %(message)s"))
    logger.addHandler(handler)

    listener = Listener(sys.argv[1])
    conn = listener.accept()
    server = Server(conn)
    server.run()
