import sys
from os.path import dirname, basename, exists, join

from .objects import get_dynamic_attributes
from .core import AttributeGetter
from .tree import NodeProvider


class ModuleProvider(object):
    def __init__(self):
        self.cache = {}

    def get(self, project, name):
        try:
            return self.cache[name]
        except KeyError:
            pass

        try:
            module = sys.modules[name]
        except KeyError:
            oldpath = sys.path
            sys.path = project.paths
            try:
                __import__(name)
            except ImportError:
                sys.path = oldpath
                raise

            module = sys.modules[name]

        m = self.cache[name] = Module(project, module)
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

    def get_filename(self, name):
        return self.module.get_filename()

    def get_project(self):
        return self.module.project


class Module(AttributeGetter):
    def __init__(self, project, module):
        self.module = module
        self.name = module.__name__
        self.project = project
        self.node_provider = ModuleNodeProvider(self)

    def get_source(self):
        filename = self.get_filename()
        return filename and open(filename).read()

    def get_filename(self):
        try:
            filename = self.module.__file__
        except AttributeError:
            return None

        if not any(map(filename.endswith, ('.py', '.pyc'))):
            return None

        return filename.replace('.pyc', '.py')

    def get_attributes(self):
        try:
            return self._attrs
        except AttributeError:
            pass

        self._attrs = get_dynamic_attributes(self.module, self.node_provider)
        return self._attrs