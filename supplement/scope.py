import ast
import logging
from bisect import bisect

from .evaluator import Evaluator
from .names import NameExtractor, create_name, ArgumentName, VarargName
from .names import ClassName, FunctionName, ImportedName, PostponedName
from .common import ListHolder, create_object_from_class_name, create_object_from_expr

def traverse_tree(root):
    yield root
    for n in root.get_children():
        for r in traverse_tree(n):
            yield r

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
        self.node2scope = {}

        if scope_type == 'module':
            node.lineno = 0

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
            from supplement.names import AssignedName
            self._names, starred_imports, sassigns = NameExtractor().process(self.node, self)
            for m, line in starred_imports:
                for name in self.project.get_module(m, self.filename).get_names():
                    self._names.setdefault(name, []).append((line, (ImportedName, m, name)))
                    self._names[name].sort(reverse=True)

            for target, idx, vidx, value, line in sassigns:
                t = self.eval(target, False)
                if t:
                    t.op_setitem(self.eval(idx, False), AssignedName(vidx, value, line))
                else:
                    logging.getLogger(__name__).error(
                        "Can't eval target on subscript assign %s %s", self.filename, vars(target))

        if lineno is None:
            return self._names

        result = []
        for name, names in self._names.iteritems():
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

        return self.project.get_module('__builtin__')[name]

    def get_scope_at(self, source, lineno, continous=True):
        try:
            ranges = self._scope_ranges
        except AttributeError:
            ranges = self._scope_ranges = ([], [])
            collect_scope_ranges(self.node, ranges, [])

        lines, scopes = ranges
        idx = bisect(lines, lineno) - 1
        node, end, parent = scopes[idx]
        cadd = 0

        if end and not continous:
            lines = source.splitlines()
            i = end - 2
            while i >= 0:
                if lines[i].strip():
                    break
                i -= 1
            cadd = end - i - 2

        while parent and end and lineno >= end - cadd:
            node, end, parent = parent

        try:
            return self.node2scope[node]
        except KeyError:
            pass

        for s in traverse_tree(self):
            if s.node is node:
                self.node2scope[node] = s
                return s

        raise Exception('Scope for line %d not found' % lineno)


SCOPE_CLASSES = (ast.ClassDef, ast.FunctionDef, ast.ExceptHandler, ast.With, ast.Module)
BLOCK_CLASSES = SCOPE_CLASSES + (ast.TryExcept, ast.TryFinally, ast.If, ast.While, ast.For)

def collect_scope_ranges(root, ranges, toclose, parent=None):
    if not isinstance(root, BLOCK_CLASSES):
        return

    isscope = isinstance(root, SCOPE_CLASSES)
    if isscope:
        lrange = [root, None, parent]
        ranges[0].append(root.lineno)
        ranges[1].append(lrange)
        parent = lrange

    for n in root.body if isscope else ast.iter_child_nodes(root):
        if toclose:
            for r in toclose:
                r[1] = n.lineno

            toclose[:] = []

        collect_scope_ranges(n, ranges, toclose, parent)

    if isscope:
        toclose.append(lrange)


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


class InnerScope(Scope):
    def __init__(self, node, parent):
        Scope.__init__(self, node, parent.name, parent, 'inner')
        self.fullname = parent.fullname
        self._names = {}

    def add_name(self, name, value):
        self._names[name] = value

    def get_names(self, lineno=None):
        return self._names

    def get_name(self, name, lineno=None):
        return self._names[name]

    def __getitem__(self, name):
        return self.get_name(name)

    def find_name(self, name, lineno=None):
        try:
            return self._names[name]
        except KeyError:
            pass

        return self.parent.find_name(name, lineno)


class ScopeExtractor(ast.NodeVisitor):
    def visit_FunctionDef(self, node):
        scope = Scope(node, node.name, self.scope, 'func')
        scope.args = {}
        scope.defaults = []
        scope.vararg = None
        scope.kwarg = None
        scope.function = create_name((FunctionName, scope, node), scope)
        self.children.append(scope)

    def visit_ExceptHandler(self, node):
        scope = InnerScope(node, self.scope)
        if node.name:
            scope.add_name(node.name.id, PostponedName(self.scope,
                create_object_from_class_name, self.scope, node.type))
        self.children.append(scope)

    def visit_With(self, node):
        scope = InnerScope(node, self.scope)
        if node.optional_vars:
            scope.add_name(node.optional_vars.id, PostponedName(self.scope,
                create_object_from_expr, self.scope, node.context_expr))
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
