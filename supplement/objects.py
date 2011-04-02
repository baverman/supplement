from types import FunctionType, ClassType, TypeType

from .tree import CtxNodeProvider

class Object(object):
    def __init__(self, name, node):
        self.name = name
        self.node = node

    def get_location(self):
        return self.node[-1].lineno, self.filename

    def get_names(self):
        return []

    def __contains__(self, name):
        return False

    def __getitem__(self, name):
        raise KeyError(name)


class ImportedObject(object):
    def __init__(self, name, node):
        self.name = name
        self.node = node

    def get_real_object(self):
        try:
            return self._real_object
        except AttributeError:
            pass

        name, inode = self.node[1], self.node[2]
        module = self.project.get_module(inode.module, self.filename)
        obj = self._real_object = module[name]
        return obj

    def get_location(self):
        return self.get_real_object().get_location()

    def get_names(self):
        return self.get_real_object().get_names()

    def __contains__(self, name):
        return name in self.get_real_object()

    def __getitem__(self, name):
        return self.get_real_object()[name]


class FunctionObject(Object):
    pass


class ClassObject(Object):
    def __init__(self, name, node, cls):
        Object.__init__(self, name, node)
        self.cls = cls
        self._attrs = {}
        self.node_provider = CtxNodeProvider(self, self.node[-1])

    def get_names(self):
        try:
            return self._names
        except AttributeError:
            pass

        self._names = {}
        for cls in (self.cls, ) + self.cls.__bases__:
            for k in cls.__dict__:
                if k not in self._names:
                    self._names[k] = cls

        return self._names

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            pass

        cls = self.get_names()[name]
        if cls is self.cls:
            obj = self._attrs[name] = create_object(name, cls.__dict__[name], self.node_provider)
            return obj
        else:
            return self.project.get_module(cls.__module__)[cls.__name__][name]

def create_object(name, obj, node_provider):
    node = node_provider[name]

    if node[0] == 'imported':
        newobj = ImportedObject(name, node)

    elif type(obj) == FunctionType:
        newobj = FunctionObject(name, node)

    elif type(obj) in (ClassType, TypeType):
        newobj = ClassObject(name, node, obj)

    else:
        newobj = Object(name, node)

    newobj.project = node_provider.get_project()
    newobj.filename = node_provider.get_filename(name)

    return newobj