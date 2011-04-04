import ast

from .objects import create_object

def get_name(name, scope):
    project = scope.project

    while scope:
        try:
            return scope[name]
        except KeyError:
            scope = scope.parent

    return project.get_module('__builtin__')[name]

def infer(string, scope):
    tree = ast.parse(string, '<string>', 'eval')
    return Evaluator().process(tree, scope)


class Evaluator(ast.NodeVisitor):
    def push(self, value):
        self.stack.append(value)

    def pop(self):
        return self.stack.pop()

    def visit_Name(self, node):
        self.push(get_name(node.id, self.scope))

    def visit_Attribute(self, node):
        self.visit(node.value)
        obj = self.pop()
        self.push(obj[node.attr])

    def visit_Str(self, node):
        self.push(create_object(self.scope, node.s))

    def visit_Num(self, node):
        self.push(create_object(self.scope, node.n))

    def visit_List(self, node):
        self.push(create_object(self.scope, []))

    def visit_Tuple(self, node):
        self.push(create_object(self.scope, ()))

    def visit_Dict(self, node):
        self.push(create_object(self.scope, {}))

    def visit_Call(self, node):
        self.visit(node.func)
        func = self.pop()
        self.push(func.call())

    def process(self, tree, scope):
        from .tree import dump_tree; dump_tree(tree)

        self.scope = scope
        self.ops = []
        self.stack = []
        self.generic_visit(tree)

        return self.stack[-1]