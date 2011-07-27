import ast
import logging

from .evaluator import Evaluator
from .names import NameExtractor, create_name, ArgumentName, VarargName
from .names import ClassName, FunctionName, ImportedName
from .common import ListHolder

def traverse_tree(root):
    yield root
    for n in root.get_children():
        for r in traverse_tree(n):
            yield r

def get_block_end(table, lines, continous):
    start = table.get_lineno() - 1
    start_line = lines[start]

    stripped_start_line = start_line.lstrip()
    while not any(map(stripped_start_line.startswith, ('def ', 'class '))):
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

        if stripped or continous:
            last_line = i
    else:
        last_line = len(lines) + 1

    return last_line

def get_scope_at(project, source, lineno, filename=None, ast_node=None, continous=True):
    ast_node = ast_node or ast.parse(source)

    scope = Scope(ast_node, '', None, 'module')
    scope.project = project
    scope.filename = filename

    return scope.get_scope_at(source, lineno, continous)


class Scope(object):
    def __init__(self, node, name, parent, scope_type):
        self.node = node
        self.name = name
        self.parent = parent
        self._attrs = {}
        self.type = scope_type

        if parent:
            self.project = parent.project
            self.filename = parent.filename

        if parent and parent.fullname:
                self.fullname = parent.fullname + '.' + name
        else:
            self.fullname = name

    def get_toplevel(self):
        scope = self
        while scope.parent:
            scope = scope.parent

        return scope

    def __repr__(self):
        return '<Scope %s %s %s>' % (self.type, self.fullname, self.filename)

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

    def get_child_by_lineno(self, lineno):
        for c in self.get_children():
            if c.get_lineno() == lineno:
                return c

        raise KeyError('lineno: %d' % lineno)

    def get_names(self, lineno=None):
        try:
            self._names
        except AttributeError:
            self._names, starred_imports, sassigns = NameExtractor().process(self.node, self)
            for m, line in starred_imports:
                for name in self.project.get_module(m, self.filename).get_names():
                    self._names.setdefault(name, []).append((line, (ImportedName, m, name)))
                    self._names[name].sort(reverse=True)

            for target, idx, value in sassigns:
                t = self.eval(target, False)
                if t:
                    t.op_setitem(self.eval(idx, False), self.eval(value, False))
                else:
                    logging.getLogger(__name__).error(
                        "Can't eval target on subscript assign %s %s", self.filename, vars(target))

        if lineno is None:
            return self._names

        result = []
        for name, names in self._names.items():
            if any(line <= lineno for line, _ in names):
                result.append(name)

        return result

    def __contains__(self, name):
        return name in self.get_names()

    def get_name(self, name, lineno=None):
        try:
            names = self._attrs[name]
        except KeyError:
            try:
                node_names = self._names[name]
            except AttributeError:
                self.get_names()
                node_names = self._names[name]

            names = self._attrs[name] = []
            for line, node in reversed(node_names):
                names.insert(0, (line, create_name(node, self)))

        if lineno is None:
            return names[0][1]

        for line, name in names:
            if line <= lineno:
                return name

        raise KeyError(name)

    def __getitem__(self, name):
        return self.get_name(name)

    def eval(self, node, skip_toplevel=True):
        return Evaluator().process(node, self, skip_toplevel)

    def get_call_scope(self, args):
        return CallScope(self, args)

    def find_name(self, name, lineno=None):
        try:
            return self.get_name(name, lineno)
        except KeyError:
            pass

        scope = self.parent
        while scope:
            try:
                return scope[name]
            except KeyError:
                scope = scope.parent

        return self.project.get_module('builtins')[name]

    def get_scope_at(self, source, lineno, continous=True):
        prev = None
        for node in traverse_tree(self):
            if node.get_lineno() == lineno:
                break

            if node.get_lineno() > lineno:
                node = prev
                break

            prev = node

        lines = source.splitlines()
        while node.parent:
            end = get_block_end(node, lines, continous)
            if lineno <= end:
                break

            node = node.parent

        return node


class CallScope(object):
    def __init__(self, parent, args):
        self.name = ''
        self.type = 'func'
        self.fullname = parent.fullname
        self.parent = parent
        self.args = args
        self.project = parent.project
        self.filename = parent.filename

    def __repr__(self):
        return '<CallScope %s %s>' % (self.fullname, self.filename)

    def get_names(self):
        return self.parent.get_names()

    def __contains__(self, name):
        return name in self.get_names()

    def find_name(self, name, lineno=None):
        try:
            return self.get_name(name, lineno)
        except KeyError:
            pass

        return self.parent.parent.find_name(name)

    def get_name(self, name, lineno=None):
        obj = self.parent.get_name(name, lineno)
        if isinstance(obj, ArgumentName):
            try:
                return self.args[obj.index]
            except IndexError:
                return self.parent.defaults[obj.index - len(self.args)].get_object()

        if isinstance(obj, VarargName):
            return ListHolder(obj, self.args[len(self.parent.args):])

        return obj

    def __getitem__(self, name):
        return self.get_name(name)

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

    def find_name(self, name, lineno=None):
        return Scope.__dict__['find_name'](self, name, lineno)

    def __contains__(self, name):
        return name in self._names

    def __getitem__(self, name):
        return self._names[name]

    def get_name(self, name, lineno=None):
        return self._names[name]


class ScopeExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        scope = Scope(node, node.name, self.scope, 'func')
        scope.args = {}
        scope.defaults = []
        scope.vararg = None
        scope.kwarg = None
        scope.function = create_name((FunctionName, scope, node), scope)
        self.children.append(scope)

    def visit_ClassDef(self, node):
        scope = Scope(node, node.name, self.scope, 'class')
        scope.cls = create_name((ClassName, scope, node), scope)
        self.children.append(scope)

    def process(self, scope):
        self.children = []
        self.scope = scope
        self.generic_visit(scope.node)

        return self.children
