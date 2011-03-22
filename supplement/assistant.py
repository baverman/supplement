from .fixer import fix
from .scope import get_scope_at
from .tree import StarImportsExtractor

def get_scope_names(project, scope, ast_nodes):
    while scope:
        ids = scope.get_identifiers()

        if scope.table.has_import_star():
            modules = StarImportsExtractor().process(ast_nodes)
            scope_name = scope.get_fullname()
            if scope_name in modules:
                for m in modules[scope_name]:
                    ids.extend(project.get_module(m).get_attributes().keys())

        yield ids
        scope = scope.parent

    m = project.get_module('__builtin__')
    yield m.get_attributes().keys()

def collect_names(match, names):
    result = []
    for name_list in names:
        result.extend(sorted(r for r in name_list
            if not match or ( r.startswith(match) and match != r )))

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

    if matches:
        ast_nodes, fixed_source = fix(source)
        lineno = source.count('\n', 0, position) + 1
        scope = get_scope_at(fixed_source, lineno)
        names = get_scope_names(project, scope, ast_nodes)

        return collect_names(match, names)

    return []