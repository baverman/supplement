import sys

from .objects import get_dynamic_attributes
from .core import AttributeGetter
from .tree import NodeProvider

class ModuleProvider(object):
    def get(self, project, name):
        try:
            module = sys.modules[name]
        except KeyError:
            try:
                __import__(name)
                module = sys.modules[name]
            except ImportError:
                return None

        return Module(project, module)


class ModuleNodeProvider(NodeProvider):
    def __init__(self, module):
        self.module = module

    def get_node(self):
        return self.module.project.get_ast(self.module)

    def get_filename(self):
        return self.module.get_filename()


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