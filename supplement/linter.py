import ast
from .fixer import try_to_fix

def lint(code, syntax_only=False):
    try:
        tree = ast.parse(code)
    except Exception as e:
        code, fixed_location = try_to_fix(e, code)
        if fixed_location:
            return [('syntax-error', e.msg, fixed_location)]
        else:
            return [('syntax-error', e.msg, ('end-of-line', e.lineno))]
    else:
        if syntax_only:
            return []
        else:
            raise NotImplementedError()