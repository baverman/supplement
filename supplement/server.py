import sys

from supplement.project import Project
from supplement.assistant import assist

class Server(object):
    def __init__(self, conn):
        self.conn = conn
        self.projects = {}
        self.configs = {}

    def configure_project(self, path, config):
        self.configs[path] = config
        self.projects[path] = self.create_project(path)

    def create_project(self, path):
        return Project(path, self.configs.get(path, {}))

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
        except Exception, e:
            import traceback
            traceback.print_exc()
            is_ok = False
            result = e.__class__.__name__, str(e)

        return result, is_ok

    def assist(self, path, source, position, filename):
        return assist(self.get_project(path), source, position, filename)

    def run(self):
        while True:
            if conn.poll(1):
                try:
                    args = conn.recv()
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
                        self.conn.send((result, is_ok))
                    except:
                        import traceback
                        traceback.print_exc()

if __name__ == '__main__':
    from multiprocessing.connection import Listener
    listener = Listener(sys.argv[1])
    conn = listener.accept()
    server = Server(conn)
    server.run()