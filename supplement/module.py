import sys
from os.path import dirname, basename, exists, join
import imp
import logging

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


class ModuleLoader(object):
    def __init__(self, project, provider):
        self.project = project
        self.provider = provider
        self.oldmodules = {}
        self.cached_paths = {}

    def imp(self, fullname):
        __import__(fullname)
        return sys.modules[fullname]

    def find_module(self, fullname, path=None):
        logging.getLogger(__name__).info('IP try to import %s %s', fullname, path)

        try:
            sys.modules[fullname].__file__
        except AttributeError:
            self.cached_paths[fullname] = 'sys', None
            return self
        except:
            pass

        package_name, sep, module_name = fullname.rpartition('.')

        if package_name:
            pkg = self.imp(package_name)
            if getattr(pkg, '__path__', None):
                paths = pkg.__path__
            else:
                self.cached_paths[fullname] = 'evaluated', getattr(pkg, module_name)
                return self
        else:
            paths = self.project.paths

        try:
            fr = imp.find_module(module_name, paths)
            self.cached_paths[fullname] = 'load', fr
            return self
        except ImportError:
            return None

    def load_module(self, fullname):
        what, data = self.cached_paths[fullname]
        if what == 'evaluated':
            if fullname in sys.modules:
                if sys.modules[fullname] is not data:
                    self.oldmodules[fullname] = sys.modules[fullname]
                    sys.modules[fullname] = data
            else:
                sys.modules[fullname] = data

        elif what == 'load':
            try:
                self.oldmodules[fullname] = sys.modules[fullname]
            except KeyError:
                pass

            try:
                imp.load_module(fullname, *data)
            finally:
                try:
                    sys.modules[fullname] = self.oldmodules[fullname]
                    del self.oldmodules[fullname]
                except KeyError:
                    pass

                if data[0]:
                    data[0].close()

        return sys.modules[fullname]

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

        loader = ModuleLoader(self.project, self.project.module_provider)
        sys.meta_path.insert(0, loader)
        try:
            self._module = loader.imp(self.name)
        finally:
            sys.meta_path.pop(0)

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

        try:
            del self._scope
        except AttributeError:
            pass

        self._attrs.clear()

    @property
    def filename(self):
        try:
            filename = self.module.__file__
        except AttributeError:
            return None

        if not any(map(filename.endswith, ('.py', '.pyc', '.pyo'))):
            return None

        return filename.replace('.pyc', '.py').replace('.pyo', '.py')

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

    def get_scope(self):
        try:
            return self._scope
        except AttributeError:
            pass

        node = self.node_provider.get_node()

        if not node:
            self._scope = scope = None
        else:
            from .scope import Scope

            self._scope = scope = Scope(node, '', None, 'module')
            scope.project = self.project
            scope.filename = self.filename

        return scope

    def get_scope_at(self, lineno):
        scope = self.get_scope()
        if not scope:
            return None

        return scope.get_scope_at(self.get_source(), lineno)
