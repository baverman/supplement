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

def match_name_ctx(source, position):
    match = ''
    i = position
    while i > 0:
        i -= 1
        c = source[i]

        if c != '_' and not c.isalnum():
            break

    match = source[i+1:position]
    return True, match

def assist(project, source, position, filename):
    matches, match = match_name_ctx(source, position)

    source = sanitize_encoding(source)
    if matches:
        ast_nodes, fixed_source = fix(source)
        lineno = source.count('\n', 0, position) + 1
        scope = get_scope_at(fixed_source, lineno, ast_nodes)
        names = get_scope_names(project, scope)

        return collect_names(match, names)

    return []