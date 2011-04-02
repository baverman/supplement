import ast

UNSUPPORTED_ASSIGNMENTS = ast.Subscript, ast.Attribute

def traverse_tree(root):
    yield root
    for n in root.get_children():
        for r in traverse_tree(n):
            yield r

def get_block_end(table, lines):
    start = table.get_lineno() - 1
    start_line = lines[start]

    while not any(map(start_line.lstrip().startswith, ('def ', 'class '))):
        start += 1
        try:
            start_line = lines[start]
        except IndexError:
            return start

    indent = len(start_line) - len(start_line.lstrip())

    last_line = start + 1
    for i, l in enumerate(lines[start+1:], start+2):
        stripped = l.lstrip()

        if stripped:
            if len(l) - len(stripped) <= indent:
                break

            last_line = i
    else:
        last_line = len(lines) + 1

    return last_line

def get_scope_at(source, lineno, ast_node=None):
    ast_node = ast_node or ast.parse(source)
    scope = Scope(ast_node, '', None)

    prev = None
    for node in traverse_tree(scope):
        if node.get_lineno() == lineno:
            break

        if node.get_lineno() > lineno:
            node = prev
            break

        prev = node

    lines = source.splitlines()
    while node.parent:
        end = get_block_end(node, lines)
        if lineno <= end:
            break

        node = node.parent

    return node


class Scope(object):
    def __init__(self, node, name, parent):
        self.node = node
        self.name = name
        self.parent = parent

        if parent and parent.fullname:
            self.fullname = parent.fullname + '.' + name
        else:
            self.fullname = name

    def get_lineno(self):
        try:
            return self.node.lineno
        except AttributeError:
            return 0

    def get_children(self):
        try:
            return self.children
        except AttributeError:
            pass

        self.children = ScopeExtractor().process(self)
        return self.children

    def get_names(self, project, filename=None):
        try:
            return self.names
        except AttributeError:
            pass

        self.names, starred_imports = NameExtractor().process(self.node)
        for m in starred_imports:
            self.names.extend(project.get_module(m, filename).get_names())

        return self.names


class ScopeExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        self.children.append(Scope(node, node.name, self.scope))

    def visit_ClassDef(self, node):
        self.children.append(Scope(node, node.name, self.scope))

    def process(self, scope):
        self.children = []
        self.scope = scope
        self.generic_visit(scope.node)

        return self.children


class NameExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        self.names.append(node.name)

    def visit_ImportFrom(self, node):
        for n in node.names:
            if n.name == '*':
                self.starred_imports.append('.' * node.level + node.module)
            else:
                self.names.append(n.asname if n.asname else n.name)

    def visit_Import(self, node):
        for n in node.names:
            self.names.append(n.asname if n.asname else n.name)

    def visit_ClassDef(self, node):
        self.names.append(node.name)

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Tuple):
            targets = node.targets[0].elts
        else:
            targets = node.targets

        for i, n in enumerate(targets):
            if isinstance(n,  UNSUPPORTED_ASSIGNMENTS):
                continue
            self.names.append(n.id)

    def visit_arguments(self, node):
        for n in node.args:
            self.names.append(n.id)

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
        #self.level = 0
        self.starred_imports = []
        self.names = []
        self.generic_visit(node)

        return self.names, self.starred_imports