import sys

from .objects import create_object
from .core import AttributeGetter
from .tree import NameExtractor

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
        self._fill_dynamic_attributes(self._attrs)
        self._find_static_names(self._attrs)

        return self._attrs

    def _fill_dynamic_attributes(self, attrs):
        for name in dir(self.module):
            attrs[name] = create_object(self, self, getattr(self.module, name), name)

    def _find_static_names(self, attrs):
        ne = NameExtractor()
        static_attrs = ne.process(self.project.get_ast(self))

        for name, node in static_attrs.iteritems():
            if name in attrs:
                attrs[name].node = node