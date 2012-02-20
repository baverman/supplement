from bisect import bisect_left as bisect
from ast import NodeVisitor, Load, parse, Name as AstName, dump
from tokenize import NL, NEWLINE, ERRORTOKEN, INDENT, DEDENT, generate_tokens, TokenError, NAME
from keyword import iskeyword
from contextlib import contextmanager

from .fixer import try_to_fix, sanitize_encoding

def check_syntax(source):
    source = sanitize_encoding(source)
    try:
        parse(source)
    except Exception, e:
        _, fixed_location = try_to_fix(e, source)
        if fixed_location:
            return fixed_location, e.msg
        else:
            return ('end-of-line', e.lineno), e.msg
    else:
        return None

def lint(source):
    source = sanitize_encoding(source)
    tree = parse(source)
    result = []
    result.extend(check_names(source, tree))

    if isinstance(source, unicode):
        result = translate_offsets(source, result)

    return result

def translate_offsets(source, errors):
    lines = source.splitlines()
    result = []
    for (col, offset), name, msg in errors:
        offset = len(lines[col-1].encode('utf-8')[:offset].decode('utf-8'))
        result.append(((col, offset), name, msg))

    return result

def check_names(source, tree):
    result = []
    usages, main_scope = NameExtractor().process(tree, IdxNameExtractor(source))

    for scope, branch, name, line, offset in usages:
        names = scope.get_names_for_branch(branch, name, line, offset)
        if not names:
            result.append(((line, offset), name, 'Unknown name (E01): ' + name))
        else:
            for n in names:
                n.usages.append((line, offset))

    for name in main_scope.get_names():
        if not name.is_used() and not name.name.startswith('_'):
            result.append(((name.line, name.offset), name.name, 'Unused name (W01): ' + name.name))

    return result


class Name(object):
    def __init__(self, name, line, offset, indirect_use=False):
        self.name = name
        self.line = line
        self.offset = offset
        self.usages = []
        self.indirect_use = indirect_use
        self.declared_at_loop = None
        self.branch = None

    def is_used(self):
        if self.indirect_use or self.usages:
            return True

        if self.declared_at_loop:
            start, end = self.declared_at_loop
            for _, _, name in self.scope.names.get(self.name, []):
                if any(end > r >= start for r in name.usages):
                    return True

        return False

    def __repr__(self):
        return "Name(%s, %s, %s, %s, %s)" % (self.name, self.line, self.offset,
            self.indirect_use, self.declared_at_loop)


class Branch(object):
    def __init__(self, parent):
        self.children = []
        self.descendants = set()
        self.parent = parent
        self.names = {}
        self.orelse = None

        while parent:
            parent.descendants.add(self)
            parent = parent.parent

    def add_child(self, child):
        self.children.append(child)
        return child

    def add_name(self, name):
        self.names[name.name] = name
        name.branch = self

    def create_orelse(self):
        self.orelse = Branch(self.parent)
        return self.orelse

    def child_of(self, branch):
        return branch is self or self in branch.descendants

    def child_of_common_orelse(self, branch):
        p = branch
        while p and p.orelse:
            if self.child_of(p.orelse):
                return True
            p = p.parent

        return False


class RootBranch(Branch):
    def __init__(self):
        Branch.__init__(self, None)


MODULE_NAMES = set(('__builtins__', '__doc__', '__file__', '__name__', '__package__'))
class BuiltinScope(object):
    def __init__(self):
        self.names = {}
        self.childs = []

    def get_name(self, name):
        try:
            return self.names[name]
        except KeyError:
            pass

        if name in MODULE_NAMES or name in __builtins__:
            result = Name(name, 0, 0, True)
        else:
            result = None

        self.names[name] = result
        return result

class Scope(object):
    def __init__(self, parent=None, is_block=True, passthrough=False):
        self.names = {}
        self.parent = parent
        self.is_block = is_block
        self.childs = []
        self.passthrough = passthrough

        self.branch = RootBranch()

        if parent:
           parent.childs.append(self)

    def add_name(self, name, starts=None):
        if starts:
            value = starts[0], starts[1], name
        else:
            value = name.line, name.offset, name
        self.names.setdefault(name.name, []).append(value)
        name.scope = self

        if self.branch:
            self.branch.add_name(name)

        return name

    def get_name(self, name, line=None, offset=None):
        if name in self.names:
            nnames = self.names[name]
            if line is not None and self.is_block:
                value = line, offset, None
                idx = bisect(nnames, value) - 1
                if idx >= 0:
                    return nnames[idx][2]
            elif not self.passthrough:
                return nnames[-1][2]

        if self.parent:
            return self.parent.get_name(name)

        return None

    def get_names_for_branch(self, branch, name, line=None, offset=None):
        result = []
        idx = -1
        if name in self.names:
            nnames = self.names[name]
            if line is not None and self.is_block:
                value = line, offset, None
                idx = bisect(nnames, value) - 1
            elif not self.passthrough:
                idx = len(nnames) - 1

        while idx >= 0:
            fname = nnames[idx][2]
            nbranch = fname.branch

            if nbranch is branch or branch.child_of(nbranch):
                result.append(fname)
                break
            elif nbranch.child_of(branch) or not branch.child_of_common_orelse(nbranch):
                result.append(fname)

            idx -= 1

        if not result:
            n = self.parent.get_name(name)
            if n:
                return [n]

        return result

    def get_names(self):
        for nnames in self.names.itervalues():
            for _, _, name in nnames:
                yield name

        for c in self.childs:
            for name in c.get_names():
                yield name

class GetExprEnd(NodeVisitor):
    def __call__(self, node):
        self.visit(node)
        return self.last_loc

    def visit_Name(self, node):
        self.last_loc = node.lineno, node.col_offset + len(node.id)

class NameExtractor(NodeVisitor):
    def process(self, root, idx_name_extractor):
        #print dump(root)
        self.idx_name_extractor = idx_name_extractor
        self.scope = self.main_scope = Scope(BuiltinScope())
        self.usages = []
        self.indirect_use = False
        self.effect_starts = None
        self.get_expr_end = GetExprEnd()
        self.declared_at_loop = False

        self.generic_visit(root)

        return self.usages, self.main_scope

    @contextmanager
    def indirect(self, is_indirect):
        old_indirect = self.indirect_use
        self.indirect_use = is_indirect
        yield None
        self.indirect_use = old_indirect

    @contextmanager
    def effect(self, starts_at):
        oldstate = self.effect_starts
        self.effect_starts = starts_at
        yield None
        self.effect_starts = oldstate

    @contextmanager
    def loop(self, start=None, end=None):
        oldstate = self.declared_at_loop
        if start:
            self.declared_at_loop = start, end
        else:
            self.declared_at_loop = None
        yield None
        self.declared_at_loop = oldstate

    def visit_Import(self, node):
        idx = 0
        for n in node.names:
            if n.asname:
                name = n.asname
                idx += n.name.count('.') + 1
            else:
                name = n.name

            line, offset = self.idx_name_extractor.get(node.lineno, idx)
            self.scope.add_name(Name(name.partition('.')[0], line, offset))
            idx += name.count('.') + 1

    def visit_ImportFrom(self, node):
        idx = 0
        if node.module == '__future__':
            return

        if node.module:
            idx += node.module.count('.') + 1

        for n in node.names:
            if n.name == '*':
                continue

            if n.asname:
                name = n.asname
                idx += n.name.count('.') + 1
            else:
                name = n.name

            line, offset = self.idx_name_extractor.get(node.lineno, idx)
            self.scope.add_name(Name(name, line, offset))
            idx += name.count('.') + 1

    def visit_Assign(self, node):
        with self.effect(self.get_expr_end(node)):
            if self.is_main_scope():
                with self.indirect(True):
                    self.generic_visit(node)
            else:
                self.generic_visit(node)

    def add_usage(self, name, lineno, col_offset, scope=None):
        scope = scope or self.scope
        self.usages.append((scope, scope.branch, name, lineno, col_offset))

    def visit_AugAssign(self, node):
        if type(node.target) is AstName:
            self.add_usage(node.target.id, node.target.lineno, node.target.col_offset)

        self.visit_Assign(node)

    def visit_Name(self, node):
        if type(node.ctx) == Load:
            self.add_usage(node.id, node.lineno, node.col_offset)
        else:
            name = self.scope.add_name(Name(node.id, node.lineno, node.col_offset, self.indirect_use),
                self.effect_starts)

            if self.declared_at_loop:
                name.declared_at_loop = self.declared_at_loop

    def visit_Lambda(self, node):
        self.scope = Scope(self.scope)
        self.scope.lineno = node.lineno
        self.scope.offset = node.col_offset
        with self.effect(None):
            with self.loop():
                with self.indirect(False):
                    self.generic_visit(node)

        self.scope = self.scope.parent

    def visit_FunctionDef(self, node):
        line, offset = self.idx_name_extractor.get(node.lineno, 0)
        self.scope.add_name(Name(node.name, line, offset,
            self.indirect_use or self.is_main_scope()))
        self.scope = Scope(self.scope)
        self.scope.lineno = line
        self.scope.offset = offset
        with self.loop():
            with self.indirect(False):
                self.generic_visit(node)

        self.scope = self.scope.parent

    def visit_ClassDef(self, node):
        line, offset = self.idx_name_extractor.get(node.lineno, 0)
        self.scope.add_name(Name(node.name, line, offset,
            self.indirect_use or self.is_main_scope()))
        self.scope = Scope(self.scope, passthrough=True)
        self.scope.lineno = line
        self.scope.offset = offset
        with self.loop():
            with self.indirect(True):
                self.generic_visit(node)
        self.scope = self.scope.parent

    def visit_GeneratorExp(self, node):
        with self.effect((node.lineno, node.col_offset-1)):
            self.generic_visit(node)

    def visit_ListComp(self, node):
        self.visit_GeneratorExp(node)

    def visit_For(self, node):
        start = node.body[0]
        with self.loop((start.lineno, start.col_offset), self.get_expr_end(node)):
            self.visit(node.target)
            self.visit(node.iter)

            oldbranch = self.scope.branch
            branch = oldbranch.add_child(Branch(oldbranch))

            self.scope.branch = branch
            for r in node.body:
                self.visit(r)

            self.scope.branch = branch.create_orelse()
            for r in node.orelse:
                self.visit(r)

            self.scope.branch = oldbranch

    def visit_While(self, node):
        with self.loop((node.lineno, node.col_offset), self.get_expr_end(node)):
            self.generic_visit(node)

    def visit_arguments(self, node):
        if node.vararg:
            self.scope.add_name(Name(node.vararg, self.scope.lineno, self.scope.offset, True))

        if node.kwarg:
            self.scope.add_name(Name(node.kwarg, self.scope.lineno, self.scope.offset, True))

        self.generic_visit(node)

    def visit_If(self, node):
        self.visit(node.test)

        oldbranch = self.scope.branch
        branch = oldbranch.add_child(Branch(oldbranch))

        self.scope.branch = branch
        for r in node.body:
            self.visit(r)

        self.scope.branch = branch.create_orelse()
        for r in node.orelse:
            self.visit(r)

        self.scope.branch = oldbranch

    def is_main_scope(self):
        return self.scope is self.main_scope

class TokenGenerator(object):
    def __init__(self, lines):
        it = iter(lines)
        self.tokens = generate_tokens(it.next)
        self.onhold = None

    def get(self, *tids):
        tok = self.next()
        if tok[0] not in tids and tok[1] not in tids:
            raise Exception('(%s,%s) not in %s' % (tok[:2], tids))

        return tok

    def hold(self, tok):
        self.onhold = tok

    def skip(self, *tids):
        tok = self.next()
        if tok[0] not in tids and tok[1] not in tids:
            self.onhold = tok
            return False

        return True

    def skipmany(self, *tids):
        while self.skip(*tids):
            pass
        else:
            return False

        return True

    SPACES = set((NL, NEWLINE, ERRORTOKEN, INDENT, DEDENT))
    def next(self):
        if self.onhold:
            tid, value, start, end, _ = self.onhold
            self.onhold = None
        else:
            try:
                tid = NL
                while tid in self.SPACES:
                    tid, value, start, end, _  = self.tokens.next()
            except (TokenError, StopIteration):
                tid, value, start, end = 0, '', (0,0), (0,0)

        return tid, value, start, end

    def __iter__(self):
        while True:
            tok = self.next()
            if not tok[0]:
                break

            yield tok

class IdxNameExtractor(object):
    def __init__(self, source):
        self.lines = source.splitlines()

    def get(self, lineno, idx):
        i = -1
        for tid, value, start, _ in TokenGenerator(self.lines[lineno-1:]):
            if tid == NAME and not iskeyword(value):
                i += 1
                if i == idx:
                    return start[0] + lineno - 1, start[1]

        return lineno, 0
