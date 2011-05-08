from .tree import ReturnExtractor
from .common import Object, UnknownObject, GetObjectDelegate

class ModuleName(Object):
    def __init__(self, name, additional=None):
        self.name = name
        self.additional = additional

    def get_names(self):
        try:
            return self._names
        except AttributeError:
            pass

        self._names = self.project.get_module(self.name, self.filename).get_names()

        self.modules = {}
        if self.additional:
            for name in self.additional:
                if not name: continue

                name, _, tail = name.partition('.')
                if name in self.modules: continue

                self._names.add(name)
                self.modules[name] = create_name((ModuleName, self.name + '.' + name, [tail]), self)

        return self._names

    def __getitem__(self, name):
        try:
            modules = self.modules
        except AttributeError:
            self.get_names()
            modules = self.modules

        try:
            return modules[name]
        except KeyError:
            pass

        return self.project.get_module(self.name, self.filename)[name]


class ImportedName(GetObjectDelegate):
    def __init__(self, module_name, name):
        self.module_name = module_name
        self.name = name

    def get_object(self):
        module = self.project.get_module(self.module_name, self.filename)
        try:
            return module[self.name]
        except KeyError:
            pass

        return self.project.get_module(self.module_name + '.' + self.name, self.filename)


class AssignedName(GetObjectDelegate):
    def __init__(self, idx, value):
        self.value = value
        self.idx = idx

    def get_object(self):
        obj = self.value.get_object()
        if self.idx is None:
            return obj
        else:
            return obj.op_getitem(self.idx)


class RecursiveCallException(Exception):
    def __init__(self, obj):
        self.object = obj

    def is_called_by(self, obj):
        return obj is self.object


class FunctionName(Object):
    def __init__(self, scope, node):
        self.scope = scope
        self.node = node
        self._calling = False

    def op_call(self, args=[]):

        if self._calling:
            raise RecursiveCallException(self)

        self._calling = True
        try:
            for rvalue in ReturnExtractor().process(self.node):
                try:
                    result = self.scope.get_call_scope(args).eval(rvalue, False)
                    if result and type(result) is not Object:
                        return result
                except RecursiveCallException, e:
                    if not e.is_called_by(self):
                        raise
        finally:
            self._calling = False

        return UnknownObject()


class ClassName(Object):
    def __init__(self, scope, node):
        self.scope = scope
        self.node = node


class ArgumentName(Object):
    def __init__(self, scope, index, name):
        self.scope = scope
        self.index = index
        self.name = name


def create_name(node, owner):
    obj = node[0](*node[1:])
    obj.project = owner.project
    obj.filename = owner.filename

    return obj