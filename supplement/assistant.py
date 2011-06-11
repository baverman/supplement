import re
import logging

from .fixer import fix, sanitize_encoding
from .scope import get_scope_at
from .evaluator import infer

def get_scope_names(scope, lineno=None):
    project = scope.project
    while scope:
        yield scope.get_names(lineno)
        lineno = None
        scope = scope.parent

    m = project.get_module('builtins')
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

def char_is_id(c):
    return c == '_' or c.isalnum()

def find_bracket(br):
    brks = {')':'(', ']':'[', '}':'{'}
    def inner(result, source, pos):
        level = 0
        consumed = []
        while pos >= 0:
            c = source[pos]
            consumed.append(c)
            if c == br:
                level += 1
            if c == brks[br]:
                level -= 1

            pos -= 1

            if level == 0:
                break
        else:
            return None, pos

        [result.insert(0, r) for r in consumed]
        return find_start, pos

    return inner

def find_id(result, source, pos):
    while pos >= 0:
        c = source[pos]
        if not char_is_id(c):
            break

        result.insert(0, c)
        pos -= 1
    else:
        return None, pos

    return find_start, pos

def find_start(result, source, pos):
    if pos < 0:
        return None, pos

    c = source[pos]
    if c == '.':
        result.insert(0, c)
        return find_start, pos - 1
    if c in (')', '}', ']'):
        return find_bracket(c), pos
    if char_is_id(c):
        return find_id, pos

    return None, pos

def get_line(source, lineno):
    lines = source.splitlines(True)
    if lineno > len(lines):
        lineno = len(lines)

    return lines[lineno - 1], sum(map(len, lines[:lineno-1]))


package_in_from_import_matcher = re.compile('from\s+(.+?)\s+import')

def get_context(source, position):
    lineno = source.count('\n', 0, position) + 1

    collected = []
    position -= 1
    func, position = find_start(collected, source, position)

    match = ''
    if func == find_id:
        func, position = func(collected, source, position)
        match = ''.join(collected)
        collected = []

    while func:
        func, position = func(collected, source, position)

    ctx = ''.join(collected)
    stripped_context = ctx.rstrip('.')
    if stripped_context:
        ctx = stripped_context

    line, line_pos = get_line(source, lineno)
    stripped_line = line.lstrip()

    ctx_type = 'none'
    if stripped_line.startswith('import'):
        ctx_type = 'import'
    elif stripped_line.startswith('from'):
        import_pos = line.find(' import ')
        if import_pos >= 0 and line_pos + import_pos + 7 <= position:
            m = package_in_from_import_matcher.search(line)
            if m:
                ctx_type = "from-import"
                ctx = m.group(1)
        else:
            ctx_type = 'from'
    else:
        ctx_type = 'eval'

    return ctx_type, lineno, ctx, match

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
            obj = scope.get_name(match, lineno)
        else:
            obj = infer(ctx, scope, lineno)[match]
    else:
        return None, None

    return obj.get_location()
