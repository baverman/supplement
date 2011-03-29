import sys, os
from os.path import abspath, join, isdir, isfile, exists, normpath, dirname

from .tree import AstProvider
from .module import ModuleProvider, PackageResolver

class Project(object):
    def __init__(self, root):
        self.root = root
        self.paths = [abspath(root)] + sys.path
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

        return self.module_provider.get(self, name)

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
            if not exists(path):
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