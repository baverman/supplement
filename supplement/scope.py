import ast

from .names import create_name, ModuleName, ImportedName, AssignedName, FunctionName, ArgumentName
from .evaluator import Value, Evaluator

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

def get_scope_at(project, source, lineno, filename=None, ast_node=None):
    ast_node = ast_node or ast.parse(source)
    scope = Scope(ast_node, '', None, 'module')
    scope.project = project
    scope.filename = filename

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
    def __init__(self, node, name, parent, scope_type):
        self.node = node
        self.name = name
        self.parent = parent
        self._attrs = {}
        self.type = type

        if parent:
            self.project = parent.project
            self.filename = parent.filename

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

    def get_child_by_name(self, name):
        for c in self.get_children():
            if c.name == name:
                return c

        raise KeyError(name)

    def get_names(self):
        try:
            return self._names
        except AttributeError:
            pass

        self._names, starred_imports = NameExtractor().process(self.node, self)
        for m in starred_imports:
            for name in self.project.get_module(m, self.filename).get_names():
                self._names[name] = ImportedName, m, name

        return self._names

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            pass

        node = self.get_names()[name]
        obj = self._attrs[name] = create_name(node, self)
        return obj

    def eval(self, node, skip_toplevel=True):
        return Evaluator().process(node, self, skip_toplevel)

    def get_call_scope(self, args):
        return CallScope(self, args)


class CallScope(object):
    def __init__(self, parent, args):
        self.name = ''
        self.type = 'func'
        self.fullname = parent.fullname
        self.parent = parent
        self.args = args
        self.project = parent.project
        self.filename = parent.filename

    def get_names(self):
        return self.parent.get_names()

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        obj = self.parent[name]
        if isinstance(obj, ArgumentName):
            return self.args[obj.index]

        return obj

    def get_lineno(self):
        return self.parent.get_lineno()

    def get_children(self):
        return self.parent.get_children()

    def get_child_by_name(self, name):
        return self.parent.get_child_by_name()

    def eval(self, node, skip_toplevel=True):
        return Evaluator().process(node, self, skip_toplevel)


class StaticScope(object):
    def __init__(self, fullname, project, filename=None):
        self._names = {}
        self.parent = None
        self.fullname = fullname
        self.project = project
        self.filename = filename

    def get_names(self):
        return self._names

    def __contains__(self, name):
        return name in self._names

    def __getitem__(self, name):
        return self._names[name]


class ScopeExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        scope = Scope(node, node.name, self.scope, 'func')
        scope.args = {}
        self.children.append(scope)

    def visit_ClassDef(self, node):
        self.children.append(Scope(node, node.name, self.scope, 'class'))

    def process(self, scope):
        self.children = []
        self.scope = scope
        self.generic_visit(scope.node)

        return self.children


class NameExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        self.names[node.name] = FunctionName, self.scope.get_child_by_name(node.name), node

    def visit_ImportFrom(self, node):
        for n in node.names:
            module_name = '.' * node.level + node.module
            if n.name == '*':
                self.starred_imports.append(module_name)
            else:
                name = n.asname if n.asname else n.name
                self.names[name] = ImportedName, module_name, name

    def visit_Import(self, node):
        for n in node.names:
            if n.asname:
                self.names[n.asname] = ModuleName, n.name
            else:
                name, _, tail = n.name.partition('.')
                self.names[name] = ModuleName, name, set()
                if tail:
                    self.additional_imports.setdefault(name, []).append(tail)

    def visit_ClassDef(self, node):
        self.names[node.name] = 'ClassName', node

    def visit_Assign(self, node):
        if isinstance(node.targets[0], ast.Tuple):
            targets = enumerate(node.targets[0].elts)
        else:
            targets = ((None, r) for r in node.targets)

        for i, n in targets:
            if isinstance(n,  ast.Name):
                self.names[n.id] = AssignedName, i, Value(self.scope, node.value)

    def visit_arguments(self, node):
        for i, n in enumerate(node.args):
            self.names[n.id] = ArgumentName, self.scope, i, n.id
            self.scope.args[i] = n.id

    def process(self, node, scope):
        self.scope = scope
        self.starred_imports = []
        self.additional_imports = {}
        self.names = {}
        self.generic_visit(node)

        for k, v in self.additional_imports.iteritems():
            if self.names[k][0] is not ModuleName:
                continue

            self.names[k][2].update(v)

        return self.names, self.starred_imports