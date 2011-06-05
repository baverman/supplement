# -*- coding: utf-8 -*-

from supplement.fixer import fix, sanitize_encoding
from supplement.assistant import assist

from .helpers import pytest_funcarg__project, get_source_and_pos

def do_assist(project, source, filename=None):
    filename = filename or 'test.py'
    source, pos = get_source_and_pos(source)
    return assist(project, source, pos, filename)

def test_encoding_sanitization():
    tree, source = fix(sanitize_encoding('# coding: utf-8\n\n\n"вау"'))

def test_not_closed_except(project):
    result = do_assist(project, '''
        try:
            code
        except Att|

        code
    ''')

    assert result == ['AttributeError']
