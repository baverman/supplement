import logging
from types import FunctionType, ModuleType, BuiltinFunctionType
from inspect import getargspec, getdoc

from .tree import CtxNodeProvider
from .common import Object, GetObjectDelegate, MethodObject, UnknownObject

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
        name, mname = self.node[1:3]
        module = self.project.get_module(mname, self.filename)
        return module[name]


class FunctionObject(LocationObject):
    def __init__(self, node, func):
        LocationObject.__init__(self, node)
        self.func = func

    def __repr__(self):
        return '<FunctionObject %s %s>' % (self.func.__name__, getattr(self, 'filename', 'No file'))

    def get_scope(self):
        module = getattr(self, 'declared_in', None)
        if not module:
            module_name = getattr(self.func, '__module__', None)
            if module_name:
                module = self.project.get_module(module_name)

        if module:
            code = getattr(self.func, '__code__', None)
            if code:
                return module.get_scope_at(code.co_firstlineno)

        return None

    def op_call(self, args):
        scope = self.get_scope()
        if scope:
            return scope.function.op_call(args)
        else:
            return UnknownObject()

    def as_method_for(self, obj):
        return MethodObject(obj, self)

    def get_signature(self):
        try:
            return (self.func.__name__,) + getargspec(self.func)
        except TypeError:
            return None

    def get_docstring(self):
        return getdoc(self.func)


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

    def get_bases(self):
        try:
            return self._bases
        except AttributeError:
            pass

        self._bases = []
        for cls in self.cls.__bases__:
            module = self.project.get_module(cls.__module__)
            try:
                clsobj = module[cls.__name__]
            except KeyError:
                clsobj = create_object(self, cls)

            self._bases.append(clsobj)

        return self._bases

    def get_names(self):
        try:
            self._names
        except AttributeError:
            self._names = set()
            for k in self.cls.__dict__:
                self._names.add(k)

        names = set()
        names.update(self._names)
        for cls in self.get_bases():
            names.update(cls.get_names())

        return names

    def op_call(self, args):
        return FakeInstanceObject(self)

    def __getitem__(self, name):
        obj = None
        try:
            obj = self._attrs[name]
        except KeyError:
            try:
                attr = self.cls.__dict__[name]
            except KeyError:
                for cls in self.get_bases():
                    try:
                        obj = cls[name]
                    except KeyError:
                        pass
                    else:
                        break
                else:
                    raise KeyError(name)
            else:
                obj = self._attrs[name] = create_object(self, attr, self.node_provider[name])

        if obj:
            return wrap_in_descriptor(self, obj)

        raise KeyError(name)

    def get_assigned_attributes(self):
        try:
            self._assigned_attributes
        except AttributeError:
            self._assigned_attributes = {}
            self.get_names()
            for name in self._names:
                obj = self[name]
                if type(obj) == FunctionObject:
                    scope = obj.get_scope()
                    if not scope: continue

                    scope.get_names()
                    if not scope.args: continue

                    slf = scope.get_name(scope.args[0])
                    self._assigned_attributes.update(slf.find_attr_assignments())

        result = self._assigned_attributes.copy()
        for cls in self.get_bases():
            for attr, value in cls.get_assigned_attributes().items():
                if attr not in result:
                    result[attr] = value

        return result

    def get_signature(self):
        sig = self['__init__'].get_signature()
        if sig:
            name, args, vararg, kwarg, defaults = sig
            return name, args[1:], vararg, kwarg, defaults
        else:
            return None

    def get_docstring(self):
        return getdoc(self.cls)


class FakeInstanceObject(Object):
    def __init__(self, class_obj):
        self._class = class_obj

    def get_names(self):
        return set(self._class.get_names()).union(set(self._class.get_assigned_attributes()))

    def __getitem__(self, name):
        attrs = self._class.get_assigned_attributes()
        if name in attrs:
            return wrap_in_method(self, attrs[name].get_object())

        if name in self._class.get_names():
            return wrap_in_method(self, self._class[name])

        raise KeyError(name)

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
        try:
            idx = idx.get_value()
        except AttributeError:
            pass
        else:
            try:
                value = self.obj[idx]
            except Exception as e:
                logging.getLogger(__name__).error(e)
            else:
                return create_object(self, value)

        return UnknownObject()

    def get_value(self):
        return self.obj

    def is_descriptor(self):
        try:
            self.obj.__get__
            return True
        except AttributeError:
            return False


def wrap_in_method(obj, attr):
    try:
        return attr.as_method_for(obj)
    except AttributeError:
        return attr

def wrap_in_descriptor(obj, attr):
    if isinstance(attr, DescriptorObject):
        attr.owner = obj
    elif not getattr(attr, 'as_method_for', None) and attr.is_descriptor():
        return DescriptorObject(obj, attr)

    return attr

MethodDescriptor = type(list.__dict__['append'])

def create_object(owner, obj, node=None):
    node = node or ('undefined', None)
    obj_type = type(obj)

    if node[0] == 'imported':
        newobj = ImportedObject(node)

    elif obj_type == ModuleType:
        return owner.project.get_module(obj.__name__)

    elif issubclass(obj_type, type):
        newobj = ClassObject(node, obj)

    elif obj_type == FunctionType or obj_type == BuiltinFunctionType or obj_type == MethodDescriptor:
        newobj = FunctionObject(node, obj)

    else:
        newobj = InstanceObject(node, obj)

    newobj.project = owner.project
    newobj.filename = owner.filename

    return newobj