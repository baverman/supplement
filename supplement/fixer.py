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
    if isinstance(source, unicode):
        parts = source.split(u'\n', 3)
        for i in range(2):
            parts[i] = parts[i].replace(u'coding=', u'codang=').replace(u'coding:', u'codang:')

        return u'\n'.join(parts)
    else:
        return source

def force_byte_string(source):
    if isinstance(source, unicode):
        return source.encode('utf8')
    else:
        return source

def fix(code, tries=4):
    try:
        return ast.parse(code), code
    except IndentationError, e:
        if not tries:
            raise

        code = code.splitlines()
        result = []
        for i, l in reversed(list(enumerate(code[:e.lineno - 1]))):
            if l.strip():
                result.extend(code[:i])
                result.append(l + ' pass')
                result.extend(code[i+1:])
                break

    except SyntaxError, e:
        if not tries:
            raise

        code = code.splitlines()

        if e.text.strip().startswith('except '):
            code[e.lineno - 1] = code[e.lineno - 1][:e.offset] + ':'
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