import re
import ast

match_ws = re.compile('^[ \t]+')
def get_ws_len(line):
    match = match_ws.search(line)
    if match:
        return len(match.group(0))
    else:
        return 0

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
    return fix(code, tries - 1), code