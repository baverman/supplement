import re

from .fixer import fix, sanitize_encoding
from .scope import get_scope_at

def get_scope_names(project, scope, filename):
    while scope:
        yield scope.get_names(project, filename)
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
            if not match or ( r.startswith(match) and match != r ):
                names_to_add.append(r)
                existing.add(r)

        result.extend(sorted(names_to_add))

    return result

def char_is_id(c):
    return c == '_' or c.isalnum()

def find_id(collected, source, position):
    i = position
    while i > 0:
        i -= 1
        if not char_is_id(source[i]):
            break

    collected.insert(0, source[i+1:position])
    if source[i] == '.' and i > 1:
        return find_id, i

    return None, i

def get_line(source, lineno):
    lines = source.splitlines(True)
    if lineno > len(lines):
        lineno = len(lines)

    return lines[lineno - 1], sum(map(len, lines[:lineno-1]))


package_in_from_import_matcher = re.compile('from\s+(.+?)\s+import')

def get_context(source, position):
    lineno = source.count('\n', 0, position) + 1

    func = find_id
    collected = []
    while func:
        func, position = func(collected, source, position)

    line, line_pos = get_line(source, lineno)
    stripped_line = line.lstrip()

    ctx_type = 'none'
    if stripped_line.startswith('import'):
        ctx_type = 'import'
    elif stripped_line.startswith('from'):
        import_pos = line.find(' import ')
        if import_pos >= 0 and line_pos + import_pos + 7 <= position:
            match = package_in_from_import_matcher.search(line)
            if match:
                ctx_type = "from-import"
                collected = [match.group(1), collected[-1]]
        else:
            ctx_type = 'from'
            collected[:-1] = ['.' if r == '' else r for r in collected[:-1]]
    else:
        ctx_type = 'name'

    return ctx_type, lineno, collected[:-1], collected[-1]

def assist(project, source, position, filename):
    ctx_type, lineno, ctx, match = get_context(source, position)

    if ctx_type == 'name':
        source = sanitize_encoding(source)
        ast_nodes, fixed_source = fix(source)

        scope = get_scope_at(fixed_source, lineno, ast_nodes)
        names = get_scope_names(project, scope, filename)
    elif ctx_type == 'import':
        names = (project.get_possible_imports('.'.join(ctx), filename),)
    elif ctx_type == 'from':
        names = (project.get_possible_imports('.'.join(ctx), filename),)
    elif ctx_type == 'from-import':
        names = (
            project.get_module(ctx[0], filename).get_names(),
            project.get_possible_imports(ctx[0], filename))
    elif ctx_type == 'none':
        return []

    return collect_names(match, names)