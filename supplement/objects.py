from types import FunctionType, ClassType

from .core import AttributeGetter
from .tree import NameExtractor

class UnknownObject(object):
    def __init__(self, module, scope):
        self.module = module
        self.scope = scope

    def get_location(self):
        return self.node[-1].lineno, self.module.get_filename()


class FunctionObject(UnknownObject):
    pass


class ClassObject(UnknownObject, AttributeGetter):
    def __init__(self, module, scope, cls):
        UnknownObject.__init__(self, module, scope)
        self.cls = cls

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
        for name in dir(self.cls):
            attrs[name] = create_object(self.module, self, getattr(self.cls, name), name)

    def _find_static_names(self, attrs):
        static_attrs = NameExtractor().process(self.node[-1])
        for name, node in static_attrs.iteritems():
            if name in attrs:
                attrs[name].node = node

def create_object(module, scope, obj, name):
    if type(obj) == FunctionType:
        return FunctionObject(module, scope)

    if type(obj) == ClassType:
        return ClassObject(module, scope, obj)

    return UnknownObject(module, scope)