from .fixer import fix, sanitize_encoding
from .scope import get_scope_at

def get_scope_names(project, scope):
    while scope:
        yield scope.get_names(project)
        scope = scope.parent

    m = project.get_module('__builtin__')
    yield m.get_attributes().keys()

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
    if source[i] == '.' and i > 1 and char_is_id(source[i-1]):
        return find_id, i

    return None, i

def get_line(source, lineno):
    return source.splitlines()[lineno - 1]

def get_context(source, position):
    lineno = source.count('\n', 0, position) + 1

    func = find_id
    collected = []
    while func:
        func, position = func(collected, source, position)

    line = get_line(source, lineno).strip()
    if line.startswith('import'):
        ctx_type = 'import'
    else:
        ctx_type = 'name'

    return ctx_type, lineno, collected[:-1], collected[-1]

def assist(project, source, position, filename):
    ctx_type, lineno, ctx, match = get_context(source, position)

    if ctx_type == 'name':
        source = sanitize_encoding(source)
        ast_nodes, fixed_source = fix(source)

        scope = get_scope_at(fixed_source, lineno, ast_nodes)
        names = get_scope_names(project, scope)
    elif ctx_type == 'import':
        names = (project.get_possible_imports(ctx),)

    return collect_names(match, names)