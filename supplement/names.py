import ast
import logging

from .tree import ReturnExtractor
from .common import Object, UnknownObject, GetObjectDelegate, Value, MethodObject


class Valuable(object):
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value


class NodeLocation(object):
    def get_location(self):
        return self.node.lineno, self.filename


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

    def get_location(self):
        module = self.project.get_module(self.name, self.filename)
        return 1, module.filename


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
    def __init__(self, idx, value, lineno):
        self.value = value
        self.idx = idx
        self.lineno = lineno

    def get_object(self):
        obj = self.value.get_object()
        if self.idx is None:
            return obj
        else:
            return obj.op_getitem(Valuable(self.idx))

    def get_location(self):
        obj = self.get_object()
        if getattr(obj, 'filename', self.filename) != self.filename:
            return obj.get_location()
        else:
            return self.lineno, self.filename

class RecursiveCallException(Exception):
    def __init__(self, obj):
        self.object = obj

    def is_called_by(self, obj):
        return obj is self.object


class FunctionName(NodeLocation, Object):
    def __init__(self, scope, node):
        self.scope = scope
        self.node = node
        self._calling = False

    def get_scope(self):
        return self.scope

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

    def as_method_for(self, obj):
        return MethodObject(obj, self)

    def get_signature(self):
        self.scope.get_names()
        args = [self.scope.args[k] for k in sorted(self.scope.args.keys())]
        return (self.scope.name, args, self.scope.vararg, self.scope.kwarg, self.scope.defaults)

    def get_docstring(self):
        return ast.get_docstring(self.node)


class ClassName(NodeLocation, Object):
    def __init__(self, scope, node):
        self.scope = scope
        self.node = node

    def get_docstring(self):
        return ast.get_docstring(self.node)

    def get_bases(self):
        try:
            return self._bases
        except AttributeError:
            pass

        self._bases = [self.scope.parent.eval(r, False) for r in self.node.bases]
        return self._bases

    def get_names(self):
        try:
            self._names
        except AttributeError:
            self._names = self.scope.get_names()

        names = set()
        names.update(self._names)
        for b in self.get_bases():
            names.update(b.get_names())

        return names

    def __getitem__(self, name):
        if name in self.get_names():
            if name in self._names:
                return self.scope.get_name(name, self._names[name][-1][0])

            for cls in self.get_bases():
                try:
                    return cls[name]
                except KeyError:
                    pass

        raise KeyError(name)

    def op_call(self, args):
        from .objects import FakeInstanceObject
        return FakeInstanceObject(self)

    def get_assigned_attributes(self):
        try:
            self._assigned_attributes
        except AttributeError:
            self._assigned_attributes = {}
            for name, loc in self.scope.get_names().iteritems():
                for line, args in loc:
                    if args[0] == FunctionName:
                        func = self.scope.get_name(name, line)
                        func.scope.get_names()
                        if not func.scope.args:
                            continue

                        slf = func.scope.get_name(func.scope.args[0])
                        self._assigned_attributes.update(slf.find_attr_assignments())


        result = self._assigned_attributes.copy()
        for cls in self.get_bases():
            for attr, value in cls.get_assigned_attributes().iteritems():
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


class ArgumentName(GetObjectDelegate):
    def __init__(self, scope, index, name):
        self.scope = scope
        self.index = index
        self.name = name

    def get_object(self):
        try:
            return self._object
        except AttributeError:
            pass

        if self.index == 0 and self.scope.parent.type == 'class':
            from .objects import FakeInstanceObject
            self._object = FakeInstanceObject(self.scope.parent.cls)
        else:
            args = self.scope.project.calldb.get_args_for_scope(self.scope)
            index = self.index
            if self.scope.parent.type == 'class':
                index -= 1

            try:
                obj = args[self.index]
            except IndexError:
                obj = UnknownObject()

            self._object = obj

        return self._object

    def find_attr_assignments(self):
        return AttributesAssignsExtractor().process(self.name, self.scope, self.scope.node)


class VarargName(GetObjectDelegate):
    def __init__(self, scope):
        self.scope = scope

    def get_object(self):
        try:
            return self._object
        except AttributeError:
            pass

        from .objects import InstanceObject
        self._object = InstanceObject(('undefined', None), ())
        return self._object


class KwargName(GetObjectDelegate):
    def __init__(self, scope):
        self.scope = scope

    def get_object(self):
        try:
            return self._object
        except AttributeError:
            pass

        from .objects import InstanceObject
        self._object = InstanceObject(('undefined', None), {})
        return self._object


class AttributesAssignsExtractor(ast.NodeVisitor):
    def visit_Assign(self, node):
        for t in node.targets:
            if type(t) == ast.Attribute and type(t.value) == ast.Name and t.value.id == self.name:
                self.result[t.attr] = Value(self.scope, node.value)

    def process(self, name, scope, node):
        self.scope = scope
        self.name = name
        self.result = {}

        self.generic_visit(node)
        return self.result


class NameExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        function_scope = self.scope.get_child_by_lineno(node.lineno)
        self.add_name(node.name, (FunctionName, function_scope, node), node.lineno)

    def visit_ImportFrom(self, node):
        for n in node.names:
            module_name = '.' * node.level + node.module
            if n.name == '*':
                self.starred_imports.append((module_name, node.lineno))
            else:
                name = n.asname if n.asname else n.name
                self.add_name(name, (ImportedName, module_name, name), node.lineno)

    def visit_Import(self, node):
        for n in node.names:
            if n.asname:
                self.names[n.asname] = ModuleName, n.name
            else:
                name, _, tail = n.name.partition('.')
                self.add_name(name, (ModuleName, name, set()), node.lineno)
                if tail:
                    self.additional_imports.setdefault(name, []).append(tail)

    def get_names_from_target(self, target, result):
        if isinstance(target, ast.Tuple):
            for r in target.elts:
                self.get_names_from_target(r, result)

        else:
            result.append(target.id)

        return result

    def visit_For(self, node):
        for n in self.get_names_from_target(node.target, []):
            self.add_name(n, (Object, ), node.lineno)

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_scope = self.scope.get_child_by_lineno(node.lineno)
        self.add_name(node.name, (ClassName, class_scope, node), node.lineno)

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Tuple):
            targets = enumerate(node.targets[0].elts)
        else:
            targets = ((None, r) for r in node.targets)

        for i, n in targets:
            if isinstance(n,  ast.Name):
                self.add_name(n.id, (AssignedName, i, Value(self.scope, node.value), n.lineno), n.lineno)
            if isinstance(n,  ast.Subscript):
                self.subscript_assignments.append((n.value, n.slice, node.value))

    def visit_arguments(self, node):
        for i, n in enumerate(node.args):
            self.add_name(n.id, (ArgumentName, self.scope, i, n.id), n.lineno)
            self.scope.args[i] = n.id

        for d in node.defaults:
            self.scope.defaults.append(Value(self.scope.parent, d))

        if node.vararg:
            self.scope.vararg = node.vararg
            self.add_name(node.vararg, (VarargName, self.scope), self.scope.node.lineno)

        if node.kwarg:
            self.scope.kwarg = node.kwarg
            self.add_name(node.kwarg, (KwargName, self.scope), self.scope.node.lineno)

    def add_name(self, name, value, lineno):
        if name in self.names:
            self.names[name].insert(0, (lineno, value))
        else:
            self.names[name] = [(lineno, value)]

    def process(self, node, scope):
        #from .tree import dump_tree; dump_tree(node); print

        self.scope = scope
        self.starred_imports = []
        self.additional_imports = {}
        self.names = {}
        self.subscript_assignments = []

        self.generic_visit(node)

        for k, v in self.additional_imports.iteritems():
            for line, name in self.names[k]:
                if name[0] is not ModuleName:
                    continue

                name[2].update(v)

        return self.names, self.starred_imports, self.subscript_assignments


def create_name(node, owner):
    obj = node[0](*node[1:])
    obj.project = owner.project
    obj.filename = owner.filename

    try:
        ds = obj.get_docstring()
    except:
        pass
        #logging.getLogger(__name__).exception("Can't get docstring")
    else:
        if ds:
            obj = owner.project.process_docstring(ds, obj)

    return obj