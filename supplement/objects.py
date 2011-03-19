from types import FunctionType, ClassType, TypeType

from .core import AttributeGetter
from .tree import ParentNodeProvider


class FallbackAttributes(object):
    def __init__(self, main, fallback):
        self.main = main
        self.fallback = fallback

    def __getitem__(self, name):
        try:
            return self.main[name]
        except KeyError:
            pass

        for f in self.fallback:
            try:
                return f[name]
            except KeyError:
                pass

        raise KeyError(name)


class FallbackNodeProvider(object):
    def __init__(self, main, fallback):
        self.main = main
        self.fallback = fallback

    def __getitem__(self, name):
        try:
            return self.main[name]
        except KeyError:
            pass

        for f in self.fallback:
            p = f.get_node_provider_for_childs()
            try:
                return p[name]
            except KeyError:
                pass

        raise KeyError(name)

    def get_filename(self, name):
        try:
            self.main[name]
            return self.main.get_filename(name)
        except KeyError:
            pass

        for f in self.fallback:
            p = f.get_node_provider_for_childs()
            try:
                p[name]
                return p.get_filename(name)
            except KeyError:
                pass

        return None


class Object(object):
    def __init__(self, name, node_provider):
        self.name = name
        self.node_provider = node_provider

    def get_location(self):
        node = self.get_node()
        ctx = node[0]

        if ctx == 'imported':
            name, inode = node[1], node[2]
            module = self.node_provider.get_project().get_module(inode.module)
            return module[name].get_location()
        else:
            return node[-1].lineno, self.node_provider.get_filename(self.name)

    def get_node(self):
        return self.node_provider[self.name]

    def get_node_provider_for_childs(self):
        try:
            return self.node_provider_for_childs
        except AttributeError:
            pass

        self.node_provider_for_childs = ParentNodeProvider(self.get_node()[-1], self.node_provider)
        return self.node_provider_for_childs


class FunctionObject(Object):
    pass


class ClassObject(Object, AttributeGetter):
    def __init__(self, name, node_provider, cls):
        Object.__init__(self, name, node_provider)
        self.cls = cls

    def get_attributes(self):
        try:
            return self._attrs
        except AttributeError:
            pass

        fallback = []
        for base in self.cls.__bases__:
            fallback.append(
                self.node_provider.get_project().get_module(base.__module__)[base.__name__])

        np = FallbackNodeProvider(self.get_node_provider_for_childs(), fallback)
        self._attrs = get_dynamic_attributes(self.cls, np)
        return self._attrs


def create_object(name, obj, node_provider):
    if type(obj) == FunctionType:
        return FunctionObject(name, node_provider)

    if type(obj) in (ClassType, TypeType):
        return ClassObject(name, node_provider, obj)

    return Object(name, node_provider)

def get_dynamic_attributes(obj, node_provider):
    result = {}
    for name in dir(obj):
        result[name] = create_object(name, getattr(obj, name), node_provider)

    return result