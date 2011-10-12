import sys
from os.path import dirname, basename, exists, join, isfile, isdir, normpath, abspath
import os
import logging
import imp

from .objects import create_object
from .tree import NodeProvider
from .scope import Scope

class ModuleProvider(object):
    def __init__(self):
        self.cache = {}
        self.override = []

    def add_override(self, override):
        self.override.append(override)

    def on_file_change(self, filename, module_name):
        try:
            del sys.modules[module_name]
        except KeyError:
            pass

        try:
            m = self.cache[module_name]
        except KeyError:
            pass
        else:
            m.invalidate()

    def get_absolute_name(self, project, name, filename):
        if name[0] == '.':
            assert filename, 'You should provide source filename to resolve relative imports'

            package_name = project.package_resolver.get(normpath(abspath(dirname(filename))))
            level = len(name) - len(name.lstrip('.')) - 1
            parts = package_name.split('.')
            name = '.'.join(parts[:len(parts)-level]) + (name[level:] if len(name) > level + 1 else '')
        else:
            if filename and exists(join(dirname(filename), '__init__.py')):
                pkg_dir = dirname(filename)
                if exists(join(pkg_dir, name+'.py')):
                    package_name = project.package_resolver.get(normpath(abspath(pkg_dir)))
                    name = package_name + '.' + name

        return name

    def get(self, project, name, filename=None):
        name = self.get_absolute_name(project, name, filename)

        try:
            return self.cache[name]
        except KeyError:
            pass

        m = Module(project, name)
        for o in self.override:
            m = o(project, m)

        self.cache[name] = m

        filename = m.filename
        if filename:
            project.monitor.monitor(filename, self.on_file_change, name)

        return m


def get_possible_project_modules(project):
    for s in project.sources:
        if exists(join(s, '__init__.py')):
            yield basename(s)
        else:
            for n in os.listdir(s):
                fname = join(s, n)
                if isdir(fname) and exists(join(fname, '__init__.py')):
                    yield n

                if isfile(fname) and n.endswith('.py'):
                    yield n[:-3]

def load_module(project, name, package_path):
    pi = set(get_possible_project_modules(project))

    bad_modules = {}
    for k, v in sys.modules.items():
        try:
            v.__file__
        except AttributeError:
            continue

        if not v:
            bad_modules[k] = v
            del sys.modules[k]

        pkg_name = k.partition('.')[0]
        if pkg_name in pi:
            bad_modules[k] = v
            del sys.modules[k]

    oldsyspath = sys.path
    sys.path = project.paths

    if exists(join(project.root, '__init__.py')):
        sys.path.insert(1, dirname(project.root))

    try:
        __import__(name)
        return sys.modules[name]
    except ImportError:
        logging.getLogger(__name__).error('Can\'t import %s. sys.path is: %s', name, sys.path)
        raise
    finally:
        sys.path = oldsyspath

        for k, v in sys.modules.items():
            try:
                v.__file__
            except AttributeError:
                continue

            pkg_name = k.partition('.')[0]
            if pkg_name in pi:
                del sys.modules[k]

        sys.modules.update(bad_modules)


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

        result = self.cache[path] = '.'.join(reversed(packages))
        return result


class ModuleNodeProvider(NodeProvider):
    def __init__(self, module):
        self.module = module

    def get_node(self):
        return self.module.project.get_ast(self.module)


class Module(object):
    def __init__(self, project, name, package_path=None):
        self.project = project
        self.name = name
        self.package_path = package_path
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

        logging.getLogger(__name__).info('Try to import %s', self.name)
        self._module = load_module(self.project, self.name, self.package_path)

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
        obj.declared_in = self

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
            self._scope = scope = DynScope(node, '', None, 'module')
            scope.project = self.project
            scope.filename = self.filename
            scope.module = self

        return scope

    def get_scope_at(self, lineno):
        scope = self.get_scope()
        if not scope:
            return None

        return scope.get_scope_at(self.get_source(), lineno)

    def get_docstring(self):
        return None

class DynScope(Scope):
    def get_name(self, name, lineno=None):
        if lineno is None:
            try:
                return self.module[name]
            except KeyError:
                pass

        return Scope.get_name(self, name, lineno)

