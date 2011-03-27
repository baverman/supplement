import sys, os
from types import ModuleType
from os.path import abspath, join, isdir, isfile, exists

from .tree import AstProvider
from .module import ModuleProvider

class Project(object):
    def __init__(self, root):
        self.root = root
        self.paths = [abspath(root)] + sys.path
        self.ast_provider = AstProvider()
        self.module_provider = ModuleProvider()

    def get_module(self, name):
        return self.module_provider.get(self, name)

    def get_ast(self, module):
        return self.ast_provider.get(module)

    def get_possible_imports(self, start):
        result = []
        if not start:
            paths = self.paths
        else:
            m = self.get_module(start)

            sub_package_prefix = start + '.'
            for name in sys.modules:
                if name.startswith(sub_package_prefix):
                    print name, sub_package_prefix
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
                        result.append(name[:-3])

        return result