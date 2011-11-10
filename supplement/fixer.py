import re
import ast

match_ws = re.compile('^[ \t]+')
def get_ws_len(line):
    match = match_ws.search(line)
    if match:
        return len(match.group(0))
    else:
        return 0

def renumerate(seq):
    i = len(seq) - 1
    for r in reversed(seq):
        yield i, r
        i -= 1

def sanitize_encoding(source):
    if isinstance(source, str):
        parts = source.split('\n', 4)
        for i in range(min(3, len(parts))):
            parts[i] = parts[i].replace('coding=', 'codang=').replace('coding:', 'codang:')

        return '\n'.join(parts)
    else:
        return source

def force_byte_string(source):
    if isinstance(source, str):
        return source.encode('utf8')
    else:
        return source

def get_lines(code, lineno):
    lines = code.splitlines()
    return lines[:lineno-1], lines[lineno-1], lines[lineno:]

def append_before(text, lineno, before, line, after):
    before[lineno] += text
    return '\n'.join(before + [line] + after)

def replace_line(before, line, after):
    return '\n'.join(before + [line] + after)

def replace_lineno(lines, lineno, text):
    lines[lineno] = text
    return '\n'.join(lines)

def unwrap_block(block_start, block_end, lines):
    lines[block_start] = ''
    for i, line in enumerate(lines[block_start+1:block_end+1], block_start+1):
        if line.startswith('    '):
            lines[i] = line[4:]
        elif line and line[0] == '\t':
            lines[i] = line[1:]

    return '\n'.join(lines)

def remove_block(block_start, block_end, lines):
    for i, line in enumerate(lines[block_start:block_end+1], block_start):
        lines[i] = '    '

    return '\n'.join(lines)

def find_except_on_the_same_level(lines, lineno):
    tryws = get_ws_len(lines[lineno])
    for i, line in enumerate(lines[lineno+1:], lineno+1):
        if line.lstrip().startswith('except') and get_ws_len(line) == tryws:
            return True, i

        if line.strip() and get_ws_len(line) <= tryws:
            return False, i - 1

    return False, len(lines) - 1

def find_unclosed_try(lines, lineno):
    for i, line in renumerate(lines[:lineno]):
        if line.strip() == 'try:':
            is_found, j = find_except_on_the_same_level(lines, i)
            if is_found:
                if j > lineno:
                    return None
            else:
                return i, j

    return None

def find_prev_block_start(lines, lineno):
    for i, line in renumerate(lines[:lineno-1]):
        if line.strip():
            return i

    return None

def try_to_fix(error, code):
    if type(error) == SyntaxError:
        before, line, after = get_lines(code, error.lineno)

        if error.text[:error.offset-1].rstrip().endswith('.'):
            return (replace_line(before, error.text[:error.offset-1].rstrip() +
                '_someattr' + error.text[error.offset-1:], after),
                ('line-offset', error.lineno, len(error.text[:error.offset-1].rstrip())))

        if error.text.rstrip().endswith('if'):
            return (replace_line(before, line.rstrip() + ' _somevar: pass', after),
                ('end-of-line', error.lineno))

        lines = code.splitlines()
        result = find_unclosed_try(lines, error.lineno)
        if result:
            return unwrap_block(result[0], result[1], lines), ('end-of-line', result[1] + 1)

        if any(map(error.text.lstrip().startswith, ('with', 'for', 'if', 'while', 'except'))) \
                and error.text[-1] != ':':

            loc = 'end-of-line', error.lineno

            if any(map(error.text.rstrip().endswith, ('with', ' in', 'while'))):
                return replace_line(before, line.rstrip() + ' _somevar: pass', after), loc

            return replace_line(before, line.rstrip() + ': pass', after), loc

        if lines[-1].strip() and error.lineno == len(lines):
            return remove_block(error.lineno-1, error.lineno, lines), ('end-of-file',)

        result = find_prev_block_start(lines, error.lineno)
        if result is not None:
            return remove_block(result, error.lineno-2, lines), ('end-of-line', result+1)

    elif type(error) == IndentationError:
        before, line, after = get_lines(code, error.lineno)
        for i, l in renumerate(before):
            sline = l.strip()
            if sline:
                if sline == 'try:':
                    return replace_lineno(code.splitlines(), i, ''), ('end-of-line', error.lineno - 1)
                if sline[-1] == ':':
                    return append_before('pass', i, before, line, after), ('end-of-line', error.lineno - 1)

    return code, None

def fix(code, tries=10):
    try:
        return ast.parse(code), code
    except Exception as e:
        tries -= 1
        if tries <= 0:
            raise

        code, fixed_location = try_to_fix(e, code)
        if fixed_location:
            return fix(code, tries)
        else:
            raise
