import sys
from os.path import dirname, basename, exists, join

from .objects import create_object
from .tree import NodeProvider
from watcher import monitor

class ModuleProvider(object):
    def __init__(self):
        self.cache = {}

    def on_file_change(self, filename, module_name):
        try:
            del sys.modules[module_name]
        except KeyError:
            pass

        try:
            m = self.cache[module_name]
        except KeyError:
            pass

        m.invalidate()

    def get(self, project, name):
        try:
            return self.cache[name]
        except KeyError:
            pass

        m = self.cache[name] = Module(project, name)

        filename = m.filename
        if filename:
            monitor(filename, self.on_file_change, name)

        return m


class PackageResolver(object):
    def __init__(self):
        self.cache = {}

    def get(self, path):
        try:
            return self.cache[path]
        except KeyError:
            pass

        packages = []
        ppath = path
        while True:
            if exists(join(ppath, '__init__.py')):
                packages.append(basename(ppath))
            else:
                break

            newpath = dirname(ppath)
            if newpath == ppath:
                break

            ppath = newpath

        package = self.cache[path] = '.'.join(reversed(packages))
        return package


class ModuleNodeProvider(NodeProvider):
    def __init__(self, module):
        self.module = module

    def get_node(self):
        return self.module.project.get_ast(self.module)


class Module(object):
    def __init__(self, project, name):
        self.project = project
        self.name = name
        self._attrs = {}
        self.node_provider = ModuleNodeProvider(self)

    def get_source(self):
        filename = self.filename
        return filename and open(filename).read()

    @property
    def module(self):
        try:
            return self._module
        except AttributeError:
            pass

        try:
            self._module = sys.modules[self.name]
        except KeyError:
            oldpath = sys.path
            sys.path = self.project.paths

            try:
                __import__(self.name)
            finally:
                sys.path = oldpath

            self._module = sys.modules[self.name]

        return self._module

    def invalidate(self):
        try:
            del self._module
        except AttributeError:
            pass

        try:
            del self._names
        except AttributeError:
            pass

        self.attrs.clear()

    @property
    def filename(self):
        try:
            filename = self.module.__file__
        except AttributeError:
            return None

        if not any(map(filename.endswith, ('.py', '.pyc'))):
            return None

        return filename.replace('.pyc', '.py')

    def get_names(self):
        try:
            return self._names
        except AttributeError:
            pass

        names = self._names = set(dir(self.module))
        return names

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            if name not in self:
                raise

        obj = self._attrs[name] = create_object(self,
            getattr(self.module, name), self.node_provider[name])

        return obj