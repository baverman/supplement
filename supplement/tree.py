import ast

from .fixer import fix

UNSUPPORTED_ASSIGNMENTS = ast.Subscript, ast.Attribute


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


class NodeProvider(object):
    def get_node(self):
        raise NotImplementedError()

    def __getitem__(self, name):
        try:
            return self.nodes.get(name, None)
        except AttributeError:
            pass

        node = self.get_node()
        if not node:
            return ('undefined', None)
        else:
            self.nodes = NameExtractor().process(self.get_node())
            return self.nodes.get(name, None)


class CtxNodeProvider(NodeProvider):
    def __init__(self, ctx, node):
        self.node = node
        self.ctx = ctx

    def get_node(self):
        return self.node


class NameExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        self.attrs[node.name] = 'func', node

    def visit_ImportFrom(self, node):
        for n in node.names:
            name = n.asname if n.asname else n.name
            self.attrs[name] = 'imported', n.name, node

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

    def process(self, node):
        if not node:
            return {}

        self.attrs = {}
        self.generic_visit(node)
        return self.attrs


class ReturnExtractor(ast.NodeVisitor):
    def process(self, node):
        dump_tree(node)
        self.result = []
        self.generic_visit(node)

        return self.result

    def visit_Return(self, node):
        self.result.append(node)


class TreeDumper(ast.NodeVisitor):
    def default(self, node):
        print '  ' * self.level, type(node), vars(node)
        self.level += 1
        self.generic_visit(node)
        self.level -= 1

    def __getattr__(self, name):
        if name in ('_attrs'):
            return object.__getattr__(self, name)

        return self.default

    def process(self, node):
        self.level = 0
        self.visit(node)

def dump_tree(tree):
    TreeDumper().process(tree)
