import sys

from .objects import fill_dynamic_attributes
from .core import AttributeGetter
from .tree import find_nodes_for_names

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


class Module(AttributeGetter):
    def __init__(self, project, module):
        self.module = module
        self.name = module.__name__
        self.project = project

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

        self._attrs = {}
        fill_dynamic_attributes(self, self, self.module, self._attrs)
        find_nodes_for_names(self.project.get_ast(self), self._attrs)

        return self._attrs