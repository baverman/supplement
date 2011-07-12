import ast
import logging

from .objects import create_object, FakeInstanceObject
from .common import Value, UnknownObject, Object
from .names import RecursiveCallException

def infer(string, scope, lineno=None):
    tree = ast.parse(string, '<string>', 'eval')

    if lineno:
        ast.increment_lineno(tree, lineno-1)

    return Evaluator().process(tree, scope)


class Slice(Object):
    def __init__(self, upper, lower, step):
        self.upper = upper
        self.lower = lower
        self.step = step


class Indexable(Object):
    def __init__(self, scope, obj, nodes):
        self.values = [Value(scope, r) for r in nodes]
        self.object = obj

    def op_getitem(self, idx):
        idx = idx.get_value()
        try:
            value = self.values[idx]
        except IndexError:
            return UnknownObject()

        return value.get_object()

    def get_names(self):
        return self.object.get_names()

    def __getitem__(self, name):
        return self.object[name]


class Dict(Object):
    def __init__(self, scope, node):
        self.scope = scope
        self.node = node
        self.object = create_object(scope, {})

    def get_data(self):
        try:
            return self.data
        except AttributeError:
            data = self.data = {}
            scope = self.scope
            for k, v in zip(self.node.keys, self.node.values):
                data[Value(scope, k).get_object().get_value()] = Value(scope, v).get_object()

            return data

    def op_getitem(self, idx):
        data = self.get_data()
        try:
            idx = idx.get_value()
        except AttributeError:
            if data:
                idx = data.keys()[0]
            else:
                return UnknownObject()

        return data[idx]

    def op_setitem(self, idx, value):
        data = self.get_data()
        try:
            data[idx.get_value()] = value
        except AttributeError:
            pass

    def get_names(self):
        return self.object.get_names()

    def __getitem__(self, name):
        return self.object[name]


class Evaluator(ast.NodeVisitor):
    def push(self, value):
        if value is None:
            raise Exception('Try to push None value')

        self.stack.append(value)

    def pop(self):
        return self.stack.pop()

    def visit_Name(self, node):
        self.push(self.scope.find_name(node.id, node.lineno))

    def visit_IfExp(self, node):
        self.visit(node.body)

    def visit_Attribute(self, node):
        self.visit(node.value)
        obj = self.pop()

        try:
            value = obj[node.attr]
        except KeyError:
            value = UnknownObject()

        self.push(value)

    def visit_Str(self, node):
        self.push(create_object(self.scope, node.s))

    def visit_Num(self, node):
        self.push(create_object(self.scope, node.n))

    def visit_List(self, node):
        self.push(Indexable(self.scope, create_object(self.scope, []), node.elts))

    def visit_Tuple(self, node):
        self.push(Indexable(self.scope, create_object(self.scope, ()), node.elts))

    def visit_Dict(self, node):
        self.push(Dict(self.scope, node))

    def visit_Call(self, node):
        self.visit(node.func)
        func = self.pop()

        args = []
        for arg in node.args:
            self.visit(arg)
            args.append(self.pop())

        self.push(func.op_call(args))

    def visit_Subscript(self, node):
        self.visit(node.slice)
        idx = self.pop()

        self.visit(node.value)
        obj = self.pop()

        self.push(obj.op_getitem(idx))

    def visit_Slice(self, node):
        if node.upper:
            self.visit(node.upper)
            upper = self.pop()
        else:
            upper = None

        if node.lower:
            self.visit(node.lower)
            lower = self.pop()
        else:
            lower = None

        if node.step:
            self.visit(node.step)
            step = self.pop()
        else:
            step = None

        self.push(Slice(upper, lower, step))

    def visit_BoolOp(self, node):
        self.visit(node.values[-1])

    def visit_BinOp(self, node):
        self.visit(node.left)

    def visit_Compare(self, node):
        self.push(FakeInstanceObject(create_object(self.scope, bool)))

    def process(self, tree, scope, skip_toplevel=True):
        #from .tree import dump_tree; print '!!!', scope.filename; print dump_tree(tree); print

        self.scope = scope
        self.ops = []
        self.stack = []

        try:
            if skip_toplevel:
                self.generic_visit(tree)
            else:
                self.visit(tree)

            if len(self.stack) != 1:
                raise Exception('invalid eval stack:', repr(self.stack))
        except RecursiveCallException:
            raise
        except:
            from .tree import dump_tree
            logger = logging.getLogger(__name__)
            logger.exception('\n<<<<<<<<<<<<<<<<<')
            logger.error('\n|||||||||||| %s - %s - %s\n%s>>>>>>>>>>\n', scope.__class__.__name__,
                scope.fullname, scope.filename, dump_tree(tree))
            raise

        return self.stack[0]