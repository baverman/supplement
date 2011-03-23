import sys
import uuid

from supplement.project import Project
from supplement.assistant import assist

class Server(object):
    def __init__(self, conn):
        self.conn = conn
        self.projects = {}

    def get_project_token(self, path):
        token = uuid.uuid1()
        p = Project(path)
        self.projects[token] = p
        return token

    def process(self, name, args, kwargs):
        try:
            is_ok = True
            result = getattr(self, name)(*args, **kwargs)
        except Exception, e:
            is_ok = False
            result = e.__class__.__name__, str(e)

        return result, is_ok

    def assist(self, token, source, position, filename):
        return assist(self.projects[token], source, position, filename)

    def run(self):
        while True:
            if conn.poll():
                try:
                    args = conn.recv()
                except EOFError:
                    break
                except Exception:
                    import traceback
                    traceback.print_exc()
                    break

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
