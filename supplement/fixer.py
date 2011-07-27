import re
import ast

match_ws = re.compile('^[ \t]+')
def get_ws_len(line):
    match = match_ws.search(line)
    if match:
        return len(match.group(0))
    else:
        return 0

def sanitize_encoding(source):
    if isinstance(source, str):
        parts = source.split('\n', 3)
        for i, l in enumerate(parts):
            parts[i] = l.replace('coding=', 'codang=').replace('coding:', 'codang:')

        return '\n'.join(parts)
    else:
        return source

def force_byte_string(source):
    if isinstance(source, str):
        return source.encode('utf8')
    else:
        return source

def fix(code, tries=10):
    try:
        return ast.parse(code), code
    except IndentationError as e:
        if not tries:
            raise

        result = code.splitlines()
        i = e.lineno
        while i > 0:
            i -= 1
            ls = result[i].rstrip()
            if ls.endswith(':'):
                result[i] = ls + ' pass'
                break

    except SyntaxError as e:
        if not tries:
            raise

        code = code.splitlines()

        if e.text.strip().startswith('except '):
            code[e.lineno - 1] = code[e.lineno - 1][:e.offset] + ': pass'
            result = code
        else:
            level = get_ws_len(code[e.lineno - 1])
            result = code[:e.lineno - 1]
            result.append('')
            for i, l in enumerate(code[e.lineno:], e.lineno):
                if l.strip() and get_ws_len(l) <= level:
                    result.extend(code[i:])
                    break
                else:
                    result.append('')

    code = '\n'.join(result)
    return fix(code, tries - 1)
