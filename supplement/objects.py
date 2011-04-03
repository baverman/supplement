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

    def collect_names(self, cls, names, collected_classes, level):
        for k in cls.__dict__:
            if k not in names or names[k][1] > level:
                names[k] = cls, level

        collected_classes.add(cls)
        for cls in cls.__bases__:
            if cls not in collected_classes:
                self.collect_names(cls, names, collected_classes, level + 1)

    def get_names(self):
        try:
            return self._names
        except AttributeError:
            pass

        self._names = {}
        self.collect_names(self.cls, self._names, set(), 0)
        return self._names

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            pass

        cls = self.get_names()[name][0]
        if cls is self.cls:
            obj = self._attrs[name] = create_object(name, cls.__dict__[name], self.node_provider)
            return obj
        else:
            return self.project.get_module(cls.__module__)[cls.__name__][name]


class InstanceObject(Object):
    def __init__(self, name, node, obj):
        Object.__init__(self, name, node)
        self.obj = obj
        self._attrs = {}
        self.node_provider = CtxNodeProvider(self, self.node[-1])

    def get_class(self):
        try:
            return self._class
        except AttributeError:
            pass

        cls = self.obj.__class__
        self._class = self.project.get_module(cls.__module__)[cls.__name__]
        return self._class

    def get_names(self):
        all_names = set(self.get_class().get_names())
        try:
            names = self._names
        except AttributeError:
            names = self._names = set()
            for k in getattr(self.obj, '__dict__', []):
                self._names.add(k)

        all_names.update(names)
        return all_names

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            pass

        if name in self.get_names() and name in self._names:
            obj = self._attrs[name] = create_object(name, self.obj.__dict__[name], self.node_provider)
            return obj
        else:
            return self.get_class()[name]


def create_object(name, obj, node_provider):
    node = node_provider[name]

    if node[0] == 'imported':
        newobj = ImportedObject(name, node)

    elif type(obj) == FunctionType:
        newobj = FunctionObject(name, node)

    elif type(obj) in (ClassType, TypeType):
        newobj = ClassObject(name, node, obj)

    else:
        newobj = InstanceObject(name, node, obj)

    newobj.project = node_provider.get_project()
    newobj.filename = node_provider.get_filename(name)

    return newobj