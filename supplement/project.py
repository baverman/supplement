import sys
from os.path import abspath

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