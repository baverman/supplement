import sys, os
from os.path import abspath, join, isdir, isfile, exists, normpath, dirname
import logging

from .tree import AstProvider
from .module import ModuleProvider, PackageResolver

class Project(object):
    def __init__(self, root, config=None):
        self.root = root
        self.config = config or {}

        self.paths = []
        if 'sources' in self.config:
            for p in self.config['sources']:
                self.paths.append(join(abspath(root), p))
        else:
            self.paths.append(abspath(root))

        for p in self.config.get('libs', []):
            self.paths.append(p)

        self.paths.extend(sys.path)

        self.ast_provider = AstProvider()
        self.module_provider = ModuleProvider()
        self.package_resolver = PackageResolver()

    def get_module(self, name, filename=None):
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

        logging.getLogger(__name__).info('Try to import %s', name)
        return self.module_provider.get(self, name)

    def get_ast(self, module):
        return self.ast_provider.get(module)

    def get_possible_imports(self, start, filename=None):
        result = set()
        if not start:
            paths = self.paths
            result.update(r for r, m in sys.modules.items() if m)
        else:
            m = self.get_module(start, filename)

            sub_package_prefix = m.module.__name__ + '.'
            for name, module in sys.modules.items():
                if module and name.startswith(sub_package_prefix):
                    result.add(name[len(sub_package_prefix):])

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
                        result.add(name)
                else:
                    if any(map(name.endswith, ('.py', '.so'))):
                        result.add(name.rpartition('.')[0])

        return result