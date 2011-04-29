from types import FunctionType, ClassType, TypeType, ModuleType

from .tree import CtxNodeProvider

class Object(object):
    def __init__(self, node):
        self.node = node

    def get_location(self):
        return self.node[-1].lineno, self.filename

    def get_names(self):
        return []

    def __contains__(self, name):
        return False

    def __getitem__(self, name):
        raise KeyError(name)

    def op_call(self, *args):
        return None

class ImportedObject(object):
    def __init__(self, node):
        self.node = node

    def get_object(self):
        name, inode = self.node[1], self.node[2]
        module = self.project.get_module(inode.module, self.filename)
        return module[name]

    def get_location(self):
        return self.get_object().get_location()

    def get_names(self):
        return self.get_object().get_names()

    def __contains__(self, name):
        return name in self.get_object()

    def __getitem__(self, name):
        return self.get_object()[name]


class FunctionObject(Object):
    def __init__(self, node, func):
        Object.__init__(self, node)
        self.func = func

    def op_call(self, args):
        module = self.project.get_module(self.func.__module__)
        scope = module.get_scope_at(self.func.func_code.co_firstlineno)

        if scope:
            return scope.function.op_call(args)
        else:
            return Object(None)

class ClassObject(Object):
    def __init__(self, node, cls):
        Object.__init__(self, node)
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

    def op_call(self, args):
        return FakeInstanceObject(self)

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            pass

        cls = self.get_names()[name][0]
        if cls is self.cls:
            obj = self._attrs[name] = create_object(self, cls.__dict__[name],
                self.node_provider[name])
            return obj
        else:
            return self.project.get_module(cls.__module__)[cls.__name__][name]


class FakeInstanceObject(Object):
    def __init__(self, class_obj):
        Object.__init__(self, ('undefined', None))
        self._class = class_obj

    def get_names(self):
        return self._class.get_names()

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        return self._class[name]

    def get_location():
        return None, None


class InstanceObject(Object):
    def __init__(self, node, obj):
        Object.__init__(self, node)
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
            obj = self._attrs[name] = create_object(self, self.obj.__dict__[name],
                self.node_provider[name])
            return obj
        else:
            return self.get_class()[name]

    def op_getitem(self, idx):
        return create_object(self, self.obj[idx])

    def get_value(self):
        return self.obj


def create_object(owner, obj, node=None):
    from .module import Module

    node = node or ('undefined', None)

    if node[0] == 'imported':
        newobj = ImportedObject(node)

    elif type(obj) == FunctionType:
        newobj = FunctionObject(node, obj)

    elif type(obj) in (ClassType, TypeType):
        newobj = ClassObject(node, obj)

    elif type(obj) == ModuleType:
        return Module(owner.project, obj.__name__)

    else:
        newobj = InstanceObject(node, obj)

    newobj.project = owner.project
    newobj.filename = owner.filename

    return newobj