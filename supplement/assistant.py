import logging
from tokenize import DOT, COMMA, COLON, NAME, NL, NEWLINE, TokenError, generate_tokens, LPAR, untokenize, OP
from keyword import iskeyword

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
        if ( line and line[0] == ',' ) or pline[-1] in ('(', '{', '[', '\\', ','):
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

    def next(self):
        if self.onhold:
            tid, value = self.onhold
            self.onhold = None
        else:
            try:
                tid, value, _, _, _  = self.tokens.next()
            except (TokenError, StopIteration):
                tid, value = 0, ''

        return tid, value

def parse_import(tokens):
    tokens.skipmany('(', NEWLINE, NL)
    tid, match = tokens.get(NAME)
    pks = []

    while True:
        tid, value = tokens.get(',', '.', NEWLINE, NL, 0)
        if not tid:
            break
        elif value == '.':
            pks.append(match)
            match = ''
            tokens.skipmany(NEWLINE, NL)
        elif value == ',':
            pks[:] = []
            match = ''
            tokens.skipmany(NEWLINE, NL)
        else:
            continue

        tid, value = tokens.get(NAME, 0)
        if not tid:
            break
        else:
            match = value

    return '.'.join(pks), match

def parse_from(tokens):
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
            break
        elif value == '.':
            pks.append(match)
            match = ''
        else:
            match = value

    return '.'*dots + '.'.join(pks), match

def parse_expr(tokens):
    pass

def get_context(source, position):
    lines, lineno = get_block(source, position)

    tokens = TokenGenerator(lines)

    ctype, ctx, match, fctx = None, None, None, None
    while True:
        tid, value = tokens.next()
        if tid == NAME:
            if value == 'import':
                ctype, fctx = 'import', None
                ctx, match = parse_import(tokens)
            elif value == 'from':
                ctype, fctx = 'import', None
                ctx, match = parse_from(tokens)
            else:
                ctype = 'expr'
                ctx, match, fctx = parse_expr(tokens)
        elif not tid:
            break

    return ctype, lineno, ctx, match, fctx

def assist(project, source, position, filename):
    logging.getLogger(__name__).info('assist %s %s', project.root, filename)
    ctx_type, lineno, ctx, match = get_context(source, position)

    if ctx_type == 'eval':
        source = sanitize_encoding(source)
        ast_nodes, fixed_source = fix(source)

        scope = get_scope_at(project, fixed_source, lineno, filename, ast_nodes)
        if not ctx:
            names = get_scope_names(scope, lineno)
        else:
            obj = infer(ctx, scope, lineno)
            names = [obj.get_names()]
    elif ctx_type == 'import':
        names = (project.get_possible_imports(ctx, filename),)
    elif ctx_type == 'from':
        names = (project.get_possible_imports(ctx, filename),)
    elif ctx_type == 'from-import':
        names = (
            project.get_module(ctx, filename).get_names(),
            project.get_possible_imports(ctx, filename))
    elif ctx_type == 'none':
        return []

    return collect_names(match, names)

def get_location(project, source, position, filename):
    source_len = len(source)
    while position < source_len and char_is_id(source[position]):
        position += 1

    ctx_type, lineno, ctx, match = get_context(source, position)

    if ctx_type == 'eval':
        source = sanitize_encoding(source)
        ast_nodes, fixed_source = fix(source)
        scope = get_scope_at(project, fixed_source, lineno, filename, ast_nodes)
        if not ctx:
            obj = scope.find_name(match, lineno)
        else:
            obj = infer(ctx, scope, lineno)[match]
    else:
        return None, None

    return obj.get_location()