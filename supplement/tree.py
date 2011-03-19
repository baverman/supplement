import ast

from .fixer import fix

class AstProvider(object):
    def __init__(self):
        self.cache = {}

    def get(self, module):
        try:
            return self.cache[module.name]
        except KeyError:
            pass

        source = module.get_source()
        if source:
            tree, _ = fix(source)
        else:
            tree = None

        self.cache[module.name] = tree

        return tree

UNSUPPORTED_ASSIGNMENTS = ast.Subscript, ast.Attribute

class NameExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        self.attrs[node.name] = 'func', node

    def visit_ClassDef(self, node):
        self.attrs[node.name] = 'class', node

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Tuple):
            targets = node.targets[0].elts
        else:
            targets = node.targets

        for i, n in enumerate(targets):
            if isinstance(n,  UNSUPPORTED_ASSIGNMENTS):
                continue
            self.attrs[n.id] = 'assign', i, node.value, n

    #def default(self, node):
    #    print '  ' * self.level, type(node), vars(node)
    #    self.level += 1
    #    self.generic_visit(node)
    #    self.level -= 1
    #
    #def __getattr__(self, name):
    #    if name in ('_attrs'):
    #        return object.__getattr__(self, name)
    #
    #    return self.default

    def process(self, node):
        if not node:
            return {}

        self.level = 0
        self.attrs = {}
        self.generic_visit(node)
        return self.attrs