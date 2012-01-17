import sys
import os.path
import time

from threading import Thread, Lock
from cPickle import dumps

class Environment(object):
    """Supplement server client"""

    def __init__(self, executable=None, env=None):
        """Environment constructor

        :param executable: path to python executable. May be path to virtualenv interpreter
              start script like ``/path/to/venv/bin/python``.

        :param env: environment variables dict, e.g. ``DJANGO_SETTINGS_MODULE`` value.
        """
        self.executable = executable or sys.executable
        self.env = env

        self.prepare_thread = None
        self.prepare_lock = Lock()

    def _run(self):
        from subprocess import Popen
        from multiprocessing.connection import Client, arbitrary_address

        if sys.platform == 'win32':
            addr = arbitrary_address('AF_PIPE')
        else:
            addr = arbitrary_address('AF_UNIX')

        supp_server = os.path.join(os.path.dirname(__file__), 'server.py')
        args = [self.executable, supp_server, addr]

        env = None
        if self.env:
            env = os.environ.copy()
            env.update(self.env)

        self.proc = Popen(args, env=env)

        start = time.time()
        while True:
            try:
                self.conn = Client(addr)
            except Exception, e:
                if time.time() - start > 5:
                    raise Exception('Supplement server launching timeout exceed: ' + str(e))

                time.sleep(0.3)
            else:
                break

    def _threaded_run(self):
        try:
            self._run()
        finally:
            self.prepare_thread = None

    def prepare(self):
        with self.prepare_lock:
            if self.prepare_thread:
                return

            if hasattr(self, 'conn'):
                return

            self.prepare_thread = Thread(target=self._threaded_run)
            self.prepare_thread.start()

    def run(self):
        with self.prepare_lock:
            if self.prepare_thread:
                self.prepare_thread.join()

            if not hasattr(self, 'conn'):
                self._run()

    def _call(self, name, *args, **kwargs):
        try:
            self.conn
        except AttributeError:
            self.run()

        self.conn.send_bytes(dumps((name, args, kwargs), 2))
        result, is_ok = self.conn.recv()

        if is_ok:
            return result
        else:
            raise Exception(result)

    def get_fixed_source(self, project_path, source):
        return self._call('get_fixed_source', project_path, source)

    def lint(self, project_path, source, filename, syntax_only=False):
        return self._call('lint', project_path, source, filename, syntax_only)

    def check_syntax(self, source):
        """Checks source syntax against current environment

        :param source: unicode or byte string code source
        :returns: None if syntax is valid and tuple ((lineno, offset), error_message) otherwise
        """
        return self._call('check_syntax', source)

    def assist(self, project_path, source, position, filename):
        """Return completion match and list of completion proposals

        :param project_path: absolute project path
        :param source: unicode or byte string code source
        :param position: character or byte cursor position
        :param filename: absolute path of file with source code
        :returns: tuple (completion match, sorted list of proposals)
        """
        return self._call('assist', project_path, source, position, filename)

    def get_location(self, project_path, source, position, filename):
        """Return line number and file path where name under cursor is defined

        If line is None location wasn't finded. If file path is None, defenition is located in
        the same source.

        :param project_path: absolute project path
        :param source: unicode or byte string code source
        :param position: character or byte cursor position
        :param filename: absolute path of file with source code
        :returns: tuple (lineno, file path)
        """
        return self._call('get_location', project_path, source, position, filename)

    def get_docstring(self, project_path, source, position, filename):
        """Return signature and docstring for current cursor call context

        Some examples of call context::

           func(|
           func(arg|
           func(arg,|

           func(arg, func2(|    # call context is func2

        Signature and docstring can be None

        :param project_path: absolute project path
        :param source: unicode or byte string code source
        :param position: character or byte cursor position
        :param filename: absolute path of file with source code
        :returns: tuple (signarure, docstring)
        """
        return self._call('get_docstring', project_path, source, position, filename)

    def configure_project(self, project_path, config):
        """Reconfigure project

        :param project_path: absolute project path
        :param config: dict with config key/values
        """
        return self._call('configure_project', project_path, config)

    def get_scope(self, project_path, source, lineno, filename, continous=True):
        """
        Return scope name at cursor position

        For example::

            class Foo:
                def foo(self):
                    pass
                    |
                def bar(self):
                    pass

        get_scope return Foo.foo if continuous is True and Foo otherwise.

        :param project_path: absolute project path
        :param source: unicode or byte string code source
        :param position: character or byte cursor position
        :param filename: absolute path of file with source code
        :param continous: allow parent scope beetween children if False
        """
        return self._call('get_scope', project_path, source, lineno, filename, continous=continous)

    def close(self):
        """Shutdown server"""

        try:
            self.conn
        except AttributeError:
            pass
        else:
            self.conn.send_bytes(dumps(('close', (), {}), 2))
            self.conn.close()
            del self.conn
