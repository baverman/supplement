from types import FunctionType, ClassType

from .core import AttributeGetter
from .tree import find_nodes_for_names

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
        fill_dynamic_attributes(self.module, self, self.cls, self._attrs)
        find_nodes_for_names(self.node[-1], self._attrs)

        return self._attrs


def create_object(module, scope, obj, name):
    if type(obj) == FunctionType:
        return FunctionObject(module, scope)

    if type(obj) == ClassType:
        return ClassObject(module, scope, obj)

    return UnknownObject(module, scope)

def fill_dynamic_attributes(module, scope, obj, attrs):
    for name in dir(obj):
        attrs[name] = create_object(module, scope, getattr(obj, name), name)
