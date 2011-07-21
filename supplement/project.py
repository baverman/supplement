import sys, os
from os.path import abspath, join, isdir, isfile, exists, normpath, dirname
import logging

from .tree import AstProvider
from .module import ModuleProvider, PackageResolver
from .watcher import DummyMonitor

class Project(object):
    def __init__(self, root, config=None, monitor=None):
        self.root = root
        self.config = config or {}
        self._refresh_paths()

        self.monitor = monitor or DummyMonitor()

        self.ast_provider = AstProvider()
        self.module_providers = {
            'default':ModuleProvider()
        }
        self.package_resolver = PackageResolver()
        self.docstring_processors = []

        self.override = [join(dirname(__file__), 'override')]

        for h in self.config.get('hooks', []):
            self.register_hook(h)

    def _refresh_paths(self):
        self.sources = []
        self.paths = []
        if 'sources' in self.config:
            for p in self.config['sources']:
                p = join(abspath(self.root), p)
                self.paths.append(p)
                self.sources.append(p)
        else:
            self.paths.append(abspath(self.root))
            self.sources.append(abspath(self.root))

        for p in self.config.get('libs', []):
            self.paths.append(p)

        self.paths.extend(sys.path)

    def get_module(self, name, filename=None):
        # TODO very weak decision.
        # Should move relative python modules handling into appropriate class
        ctx, sep, name = name.partition(':')
        if not sep:
            ctx, name = 'default', ctx

        if name[0] == '.':
            if not filename:
                raise Exception('You should provide source filename to resolve relative imports')

            package_name = self.package_resolver.get(normpath(abspath(dirname(filename))))
            level = len(name) - len(name.lstrip('.')) - 1
            parts = package_name.split('.')
            name = '.'.join(parts[:len(parts)-level]) + (name[level:] if len(name) > level + 1 else '')

        if filename and filename.endswith('__init__.py'):
            pkg_dir = dirname(filename)
            if exists(join(pkg_dir, name+'.py')):
                package_name = self.package_resolver.get(normpath(abspath(pkg_dir)))
                name = package_name + '.' + name

        return self.module_providers[ctx].get(self, name)

    def get_ast(self, module):
        return self.ast_provider.get(module)

    def get_possible_imports(self, start, filename=None):
        result = []
        if not start:
            paths = self.paths
        else:
            m = self.get_module(start, filename)

            sub_package_prefix = m.module.__name__ + '.'
            for name, module in sys.modules.iteritems():
                if module and name.startswith(sub_package_prefix):
                    result.append(name[len(sub_package_prefix):])

            try:
                paths = m.module.__path__
            except AttributeError:
                paths = []

        for path in paths:
            if not exists(path) or not isdir(path):
                continue

            path = abspath(path)
            for name in os.listdir(path):
                if name == '__init__.py':
                    continue

                filename = join(path, name)
                if isdir(filename):
                    if isfile(join(filename, '__init__.py')):
                        result.append(name)
                else:
                    if any(map(name.endswith, ('.py', '.so'))):
                        result.append(name.rpartition('.')[0])

        return result

    def register_hook(self, name):
        try:
            __import__(name)
            sys.modules[name].init(self)
        except:
            logging.getLogger(__name__).exception('[%s] register failed' % name)

    def add_docstring_processor(self, processor):
        self.docstring_processors.append(processor)

    def add_module_provider(self, ctx, provider):
        self.module_providers[ctx] = provider

    def add_override_processor(self, override):
        self.module_providers['default'].add_override(override)

    def process_docstring(self, docstring, obj):
        for p in self.docstring_processors:
            result = p(docstring, obj)
            if result is not None:
                return result

        return obj

    def get_filename(self, name, rel=None):
        if name.startswith('/'):
            return join(self.root, name[1:])

        return join(dirname(rel), name)

    def add_override(self, path):
        self.override.append(path)