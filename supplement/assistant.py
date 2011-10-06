import logging
from keyword import iskeyword
from inspect import formatargspec
from tokenize import (NAME, NL, NEWLINE, TokenError, generate_tokens,
    untokenize, ERRORTOKEN, INDENT, DEDENT)

from .fixer import fix, sanitize_encoding
from .scope import get_scope_at
from .evaluator import infer

def get_scope_names(scope, lineno=None):
    inject_bases = scope.type == 'class'
    project = scope.project
    while scope:
        yield scope.get_names(lineno)
        lineno = None

        if inject_bases:
            inject_bases = False
            yield scope.cls.get_names()

        scope = scope.parent

    m = project.get_module('__builtin__')
    yield m.get_names()

def collect_names(match, names):
    existing = set()
    result = []
    for name_list in names:
        names_to_add = []
        for r in name_list:
            if r in existing: continue
            if not match and r.startswith('__'): continue
            if not match or (r.startswith(match) and match != r):
                names_to_add.append(r)
                existing.add(r)

        result.extend(sorted(names_to_add))

    return result

def get_block(source, position):
    lines = source[:position].splitlines(True)
    lineno = len(lines) - 1

    start = lineno
    while start > 0:
        line = lines[start].lstrip()
        pline = lines[start-1].rstrip()
        if ( line and line[0] == ',' ) or not pline or pline[-1] in ('(', '{', '[', '\\', ','):
            start -= 1
        else:
            break

    return lines[start:lineno+1], lineno + 1

class TokenGenerator(object):
    def __init__(self, lines):
        it = iter(lines)
        self.tokens = generate_tokens(it.next)
        self.onhold = None

    def get(self, *tids):
        tid, value = self.next()
        if tid not in tids and value not in tids:
            raise Exception('(%s,%s) not in %s' % (tid, value, tids))

        return tid, value

    def hold(self, tid, value):
        self.onhold = (tid, value)

    def skip(self, *tids):
        tid, value = self.next()
        if tid not in tids and value not in tids:
            self.onhold = (tid, value)
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
            tid, value = self.onhold
            self.onhold = None
        else:
            try:
                tid = NL
                while tid in self.SPACES:
                    tid, value, _, _, _  = self.tokens.next()
            except (TokenError, StopIteration):
                tid, value = 0, ''

        return tid, value

def parse_import(tokens):
    tokens.skip('(')
    tid, match = tokens.get(NAME, 0)
    pks = []

    if not tid:
        return '', ''

    while True:
        tid, value = tokens.get(',', '.', 0)
        if not tid:
            break
        elif value == '.':
            pks.append(match)
            match = ''
        elif value == ',':
            pks[:] = []
            match = ''
        else:
            continue

        tid, value = tokens.get(NAME, 0)
        if not tid:
            break
        else:
            match = value

    return '.'.join(pks), match

def parse_from(tokens):
    ctype = 'import'
    pks = []
    match = ''
    dots = 0
    while True:
        tid, value = tokens.next()
        if value == '.':
            dots += 1
        else:
            break

    tokens.hold(tid, value)
    while True:
        tid, value = tokens.get(NAME, '.', 0)
        if not tid: break

        if value == 'import':
            if match:
                pks.append(match)

            _, match = parse_import(tokens)
            ctype = 'from-import'
            break
        elif value == '.':
            pks.append(match)
            match = ''
        else:
            match = value

    return ctype, '.'*dots + '.'.join(pks), match

BRACKETS = {
 '(':')',
 '{':'}',
 '[':']'
}

def parse_expr(tokens, end=None):
    expr = []
    match = ''
    full = []
    is_arg = True

    while True:
        tid, value = tokens.next()
        if not tid: break
        full.append((tid, value))

        if end and value == end:
            return 'full', (full,)

        if value in ('(', '{', '['):
            if match:
                expr.append((NAME, match))
                match = ''

            expr.append((tid, value))
            state, args = parse_expr(tokens, BRACKETS[value])
            if state == 'full':
                expr.extend(args[0])
                full.extend(args[0])
                continue
            elif state == 'stop':
                if args[2]:
                    fctx = expr[:-1]
                else:
                    fctx = None

                if end:
                    return 'done', (args[0], args[1], fctx)
                else:
                    return args[0], args[1], fctx
            elif state == 'done':
                if end:
                    return state, args
                else:
                    return args
        elif tid == NAME and not iskeyword(value):
            match = value
            continue
        elif value == '.':
            is_arg = False
            if match:
                expr.append((NAME, match))
                match = ''

            expr.append((tid, value))
        else:
            expr[:] = []
            match = ''
            is_arg = value == ','

    if end:
        return 'stop', (expr, match, is_arg)

    return expr, match, []

def prep_tokens(tokens):
    if not tokens:
        return ''

    result = []
    pos = 0
    for tid, value in tokens:
        newpos = pos + len(value)
        result.append((tid, value, (1, pos), (1, newpos), ''))

    return result

def get_context(source, position):
    lines, lineno = get_block(source, position)

    tokens = TokenGenerator(lines)
    ctype, ctx, match, fctx = 'expr', '', '', ''
    while True:
        tid, value = tokens.next()
        if not tid: break

        if tid == NAME and value == 'import':
            ctype, fctx = 'import', None
            ctx, match = parse_import(tokens)

        elif tid == NAME and value == 'from':
            fctx = None
            ctype, ctx, match = parse_from(tokens)

        elif tid == NAME or value in BRACKETS.keys():
            ctype = 'expr'
            tokens.hold(tid, value)
            ctx, match, fctx = parse_expr(tokens)
            ctx = untokenize(prep_tokens(ctx)).strip().rstrip('.')
            fctx = untokenize(prep_tokens(fctx)).strip().rstrip('.')

        else:
            ctype, ctx, match, fctx = 'expr', '', '', ''

    return ctype, lineno, ctx, match, fctx

def assist(project, source, position, filename):
    logging.getLogger(__name__).info('assist %s %s', project.root, filename)
    ctx_type, lineno, ctx, match, fctx = get_context(source, position)
    if ctx_type == 'expr':
        source = sanitize_encoding(source)
        ast_nodes, fixed_source = fix(source)

        scope = get_scope_at(project, fixed_source, lineno, filename, ast_nodes)
        project.calldb.collect_calls(scope.get_toplevel(), True)
        if not ctx:
            names = get_scope_names(scope, lineno)
            if fctx:
                funcobj = infer(fctx, scope, lineno)
                args = funcobj.get_signature()
                if args:
                    names = [(r + '=' for r in args[1])] + list(names)
        else:
            obj = infer(ctx, scope, lineno)
            names = [obj.get_names()]
    elif ctx_type == 'import':
        names = (project.get_possible_imports(ctx, filename),)
    elif ctx_type == 'from-import':
        names = (
            project.get_module(ctx, filename).get_names(),
            project.get_possible_imports(ctx, filename))
    elif ctx_type is None:
        return match, []

    return match, collect_names(match, names)

def char_is_id(c):
    return c == '_' or c.isalnum()

def get_id_ending(source, position):
    source_len = len(source)
    while position < source_len and char_is_id(source[position]):
        position += 1

    return position

def get_location(project, source, position, filename):
    position = get_id_ending(source, position)
    ctx_type, lineno, ctx, match, fctx = get_context(source, position)

    if ctx_type == 'expr':
        source = sanitize_encoding(source)
        ast_nodes, fixed_source = fix(source)
        scope = get_scope_at(project, fixed_source, lineno, filename, ast_nodes)
        if not ctx:
            obj = scope.find_name(match, lineno)
        else:
            obj = infer(ctx, scope, lineno)[match]

        return obj.get_location()

    elif ctx_type in ('import', 'from-import'):
        if ctx:
            if ctx[-1] == '.':
                ctx = ctx[:-1]

            module_name = ctx + '.' + match
        else:
            module_name = match

        try:
            module = project.get_module(module_name, filename)
        except ImportError:
            module_name, _, _ = module_name.rpartition('.')
            if module_name:
                module = project.get_module(module_name, filename)
                return module[match].get_location()
        else:
            return 1, module.filename

    return None, None

def get_docstring(project, source, position, filename):
    position = get_id_ending(source, position)
    ctx_type, lineno, ctx, match, fctx = get_context(source, position)
    if ctx_type == 'expr' and fctx:
        source = sanitize_encoding(source)
        ast_nodes, fixed_source = fix(source)
        scope = get_scope_at(project, fixed_source, lineno, filename, ast_nodes)
        obj = infer(fctx, scope, lineno)

        sig = obj.get_signature()
        if sig:
            sig = '%s%s' % (sig[0], formatargspec(*sig[1:]))

        return sig, obj.get_docstring()

    return None