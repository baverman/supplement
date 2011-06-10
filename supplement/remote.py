import sys
import os.path
import time
from cPickle import loads, dumps

class Environment(object):
    def __init__(self, executable=None, env=None):
        self.executable = executable or sys.executable
        self.env = env

    def run(self):
        from subprocess import Popen
        from multiprocessing.connection import Client, arbitrary_address

        addr = arbitrary_address('AF_UNIX')

        args = [self.executable, '-m', 'supplement.server', addr]

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

        self.conn.send_bytes(dumps((name, args, kwargs), 2))
        result, is_ok = loads(self.conn.recv_bytes())

        if is_ok:
            return result
        else:
            raise Exception(result)

    def assist(self, project_path, source, position, filename):
        return self._call('assist', project_path, source, position, filename)

    def get_location(self, project_path, source, position, filename):
        return self._call('get_location', project_path, source, position, filename)

    def configure_project(self, project_path, config):
        return self._call('configure_project', project_path, config)

    def close(self):
        try:
            self.conn
            self._call('close')
            self.conn.close()
            del self.conn
        except AttributeError:
            pass