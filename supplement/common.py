import logging

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


class UnknownObject(Object): pass


class Value(object):
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