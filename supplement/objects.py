from types import FunctionType, ModuleType

from .tree import CtxNodeProvider
from .common import Object, GetObjectDelegate

def dir_top(obj):
    try:
        return obj.__dict__
    except AttributeError:
        pass

    try:
        return obj.__members__
    except AttributeError:
        pass

    return []

def get_attr(obj, name):
    try:
        return obj.__dict__[name]
    except AttributeError:
        pass

    return getattr(obj, name)


class LocationObject(Object):
    def __init__(self, node):
        self.node = node

    def get_location(self):
        return self.node[-1].lineno, self.filename


class ImportedObject(GetObjectDelegate):
    def __init__(self, node):
        self.node = node

    def get_object(self):
        name, inode = self.node[1], self.node[2]
        module = self.project.get_module(inode.module, self.filename)
        return module[name]


class FunctionObject(LocationObject):
    def __init__(self, node, func):
        LocationObject.__init__(self, node)
        self.func = func

    def op_call(self, args):
        module = self.project.get_module(self.func.__module__)
        scope = module.get_scope_at(self.func.__code__.co_firstlineno)

        if scope:
            return scope.function.op_call(args)
        else:
            return Object(None)


class MethodObject(GetObjectDelegate):
    def __init__(self, obj, func_obj):
        self.object = obj
        self.function = func_obj

    def get_object(self):
        return self.function

    def op_call(self, args):
        return self.function.op_call([self.object] + args)


class DescriptorObject(GetObjectDelegate):
    def __init__(self, owner, obj):
        self.owner = owner
        self.object = obj

    def get_object(self):
        if isinstance(self.owner, ClassObject):
            return create_object(self.owner, self.object.obj.__get__(None, self.owner.cls))

        return self.object


class ClassObject(LocationObject):
    def __init__(self, node, cls):
        LocationObject.__init__(self, node)
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

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            pass

        cls = self.get_names()[name][0]
        if cls is self.cls:
            obj = self._attrs[name] = create_object(self,
                cls.__dict__[name], self.node_provider[name])
            return wrap_in_descriptor(self, obj)
        else:
            return wrap_in_descriptor(self,
                self.project.get_module(cls.__module__)[cls.__name__][name])

    def get_assigned_attributes(self):
        return {}


class FakeInstanceObject(Object):
    def __init__(self, class_obj):
        self._class = class_obj

    def get_names(self):
        return set(self._class.get_names()).union(set(self._class.get_assigned_attributes()))

    def __getitem__(self, name):
        if name in self._class.get_names():
            return wrap_in_method(self, self._class[name])

        attrs = self._class.get_assigned_attributes()
        if name in attrs:
            return wrap_in_method(self, attrs[name].get_object())


class InstanceObject(LocationObject):
    def __init__(self, node, obj):
        LocationObject.__init__(self, node)
        self.obj = obj
        self._attrs = {}
        self.node_provider = CtxNodeProvider(self, self.node[-1])

    def get_class(self):
        try:
            return self._class
        except AttributeError:
            pass

        cls = self.obj.__class__
        module = self.project.get_module(cls.__module__)

        try:
            self._class = module[cls.__name__]
        except KeyError:
            self._class = create_object(module, cls)

        return self._class

    def get_names(self):
        all_names = set(self.get_class().get_names())
        try:
            names = self._names
        except AttributeError:
            names = self._names = set()
            for k in dir_top(self.obj):
                self._names.add(k)

        all_names.update(names)
        return all_names

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            pass

        if name in self.get_names() and name in self._names:
            obj = self._attrs[name] = create_object(self, get_attr(self.obj, name),
                self.node_provider[name])
            return obj
        else:
            return wrap_in_method(self, self.get_class()[name])

    def op_getitem(self, idx):
        return create_object(self, self.obj[idx.get_value()])

    def get_value(self):
        return self.obj

    def is_descriptor(self):
        try:
            self.obj.__get__
            return True
        except AttributeError:
            return False


def wrap_in_method(obj, attr):
    if type(attr) is FunctionObject:
        return MethodObject(obj, attr)

    return attr

def wrap_in_descriptor(obj, attr):
    if isinstance(attr, DescriptorObject):
        attr.owner = obj
    elif not isinstance(attr, FunctionObject) and attr.is_descriptor():
        return DescriptorObject(obj, attr)

    return attr

def create_object(owner, obj, node=None):
    node = node or ('undefined', None)
    obj_type = type(obj)

    if node[0] == 'imported':
        newobj = ImportedObject(node)

    elif obj_type == FunctionType:
        newobj = FunctionObject(node, obj)

    elif obj_type == ModuleType:
        return owner.project.get_module(obj.__name__)

    elif issubclass(obj_type, type):
        newobj = ClassObject(node, obj)

    else:
        newobj = InstanceObject(node, obj)

    newobj.project = owner.project
    newobj.filename = owner.filename

    return newobj