import logging
import ast

class Object(object):
    def get_location(self):
        raise NotImplementedError()
        return None, None

    def get_names(self):
        return set()

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        return UnknownObject()

    def op_call(self, *args):
        return UnknownObject()

    def op_getitem(self, idx):
        return UnknownObject()

    def op_setitem(self, idx, value):
        logging.getLogger(__name__).info('Try to set item on unknown object %s', self)

    def is_descriptor(self):
        return False

    def get_assigned_attributes(self):
        return {}

    def get_docstring(self):
        return None

    def get_signature(self):
        return None

    def get_scope(self):
        return None

    def op_common_item(self):
        return UnknownObject()


class GetObjectDelegate(object):
    def get_names(self):
        return self.get_object().get_names()

    def __getitem__(self, name):
        return self.get_object()[name]

    def __contains__(self, name):
        return name in self.get_object()

    def op_call(self, args):
        return self.get_object().op_call(args)

    def op_getitem(self, idx):
        return self.get_object().op_getitem(idx)

    def op_setitem(self, idx, value):
        return self.get_object().op_setitem(idx, value)

    def get_location(self):
        return self.get_object().get_location()

    def is_descriptor(self):
        return self.get_object().is_descriptor()

    def get_assigned_attributes(self):
        return self.get_object().get_assigned_attributes()

    def get_docstring(self):
        return self.get_object().get_docstring()

    def get_signature(self):
        return self.get_object().get_signature()

    def get_scope(self):
        return self.get_object().get_scope()

    def op_common_item(self):
        return self.get_object().op_common_item()


class UnknownObject(Object): pass
class NoneObject(Object): pass


class Value(GetObjectDelegate):
    def __init__(self, scope, value):
        self.scope = scope
        self.value = value

    def get_object(self):
        try:
            return self._object
        except AttributeError:
            pass

        self._object = self.scope.eval(self.value, False)
        return self._object


class ClassProxy(GetObjectDelegate):
    def __init__(self, project, module_name, class_name):
        self.class_name = class_name
        self.module_name = module_name
        self.project = project

    def get_object(self):
        return self.project.get_module(self.module_name)[self.class_name]


class GetObjectable(object):
    def __init__(self, obj):
        self.object = obj

    def get_object(self):
        return self.object


class MethodObject(GetObjectDelegate):
    def __init__(self, obj, func_obj):
        self.object = obj
        self.function = func_obj

    def get_scope(self):
        return self.function.get_scope()

    def get_object(self):
        return self.function

    def op_call(self, args):
        return self.function.op_call([self.object] + args)

    def get_signature(self):
        sig = self.function.get_signature()
        if sig:
            name, args, vararg, kwarg, defaults = sig
            return name, args[1:], vararg, kwarg, defaults
        else:
            return None


class ListHolder(GetObjectDelegate):
    def __init__(self, obj, values):
        self.values = values
        self.object = obj

    def get_object(self):
        return self.object

    def op_getitem(self, idx):
        return self.values[idx.get_value()]


def create_object_from_class_name(scope, name):
    from .objects import FakeInstanceObject
    return FakeInstanceObject(scope.eval(name, False))

def create_object_from_expr(scope, expr):
    return scope.eval(expr, False)

def create_object_from_seq_item(scope, expr):
    seq = scope.eval(expr, False)
    return seq.op_common_item()

def get_indexes_for_target(target, result, idx):
    if isinstance(target, (ast.Tuple, ast.List)):
        idx.append(0)
        for r in target.elts:
            get_indexes_for_target(r, result, idx)
        idx.pop()

    else:
        result.append((target, idx[:]))
        if idx:
            idx[-1] += 1

    return result

