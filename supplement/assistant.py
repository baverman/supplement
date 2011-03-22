from .fixer import fix
from .scope import get_scope_at
from .tree import StarImportsExtractor

def get_module_names(project, scope, ast_tree):
    ids = scope.get_identifiers()

    if scope.table.has_import_star():
        modules = StarImportsExtractor().process(ast_tree)
        scope_name = scope.get_fullname()
        if scope_name in modules:
            for m in modules[scope_name]:
                ids.extend(project.get_module(m).get_attributes().keys())

    yield ids
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
    lineno = source.find('\n', 0, position) + 1

    ast_tree, fixed_source = fix(source)

    scope = get_scope_at(fixed_source, lineno)

    matches, match = match_name_ctx(source, position)
    if scope.get_type() == 'module':
        names = get_module_names(project, scope, ast_tree)

    return collect_names(match, names)