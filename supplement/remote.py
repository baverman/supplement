import sys
import os.path
import time

class Environment(object):

    def __init__(self, executable=None, env=None):
        self.executable = executable or sys.executable
        self.env = env

    def run(self):
        from subprocess import Popen
        from multiprocessing.connection import Client, arbitrary_address

        addr = arbitrary_address('AF_UNIX')
        filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.py')

        args = [self.executable, filename, addr]

        env = None
        if self.env:
            env = os.environ.copy()
            env.update(self.env)

        self.proc = Popen(args, env=env)
        start = time.time()
        while not os.path.exists(addr):
            if time.time() - start > 5:
                raise Exception('Supplement server launching timeout exceed')
            time.sleep(0.01)

        self.conn = Client(addr)

    def _call(self, name, *args, **kwargs):
        try:
            self.conn
        except AttributeError:
            self.run()

        self.conn.send((name, args, kwargs))
        result, is_ok = self.conn.recv()

        if is_ok:
            return result
        else:
            raise Exception(result)

    def get_project_token(self, path, config={}):
        return self._call('get_project_token', path=path, config=config)

    def assist(self, token, source, position, filename):
        return self._call('assist', token, source, position, filename)

    def close(self):
        try:
            self.conn
            self._call('close')
            self.conn.close()
            del self.conn
        except AttributeError:
            pass