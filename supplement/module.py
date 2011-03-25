import sys

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
            __import__(name)
            module = sys.modules[name]

        m = self.cache[name] = Module(project, module)
        return m


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