import ast

from .objects import create_object

def infer(string, scope, lineno=None):
    tree = ast.parse(string, '<string>', 'eval')

    if lineno:
        ast.increment_lineno(tree, lineno-1)

    return Evaluator().process(tree, scope)


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


class Indexable(object):
    def __init__(self, scope, obj, nodes):
        self.values = [Value(scope, r) for r in nodes]
        self.object = obj

    def op_getitem(self, idx):
        return self.values[idx].get_object()

    def get_names(self):
        return self.object.get_names()

    def __contains__(self, name):
        return name in self.object

    def __getitem__(self, name):
        return self.object[name]


class Dict(object):
    def __init__(self, scope, node):
        self.scope = scope
        self.node = node
        self.object = create_object(scope, {})

    def op_getitem(self, idx):
        try:
            data = self.data
        except AttributeError:
            data = self.data = {}
            scope = self.scope
            for k, v in zip(self.node.keys, self.node.values):
                data[Value(scope, k).get_object().get_value()] = Value(scope, v).get_object()

        return self.data[idx]

    def get_names(self):
        return self.object.get_names()

    def __contains__(self, name):
        return name in self.object

    def __getitem__(self, name):
        return self.object[name]


class Evaluator(ast.NodeVisitor):
    def push(self, value):
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
        self.push(obj[node.attr])

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

        self.push(obj.op_getitem(idx.get_value()))

    def process(self, tree, scope, skip_toplevel=True):
        from .tree import dump_tree;
        dump_tree(tree)
        print

        self.scope = scope
        self.ops = []
        self.stack = []

        if skip_toplevel:
            self.generic_visit(tree)
        else:
            self.visit(tree)

        if len(self.stack) != 1:
            raise Exception('invalid eval stack:', repr(self.stack))

        return self.stack[0]