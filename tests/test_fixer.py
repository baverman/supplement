# -*- coding: utf-8 -*-
import pytest
from supplement.fixer import fix, sanitize_encoding

from .helpers import pytest_funcarg__project, do_assist, cleantabs

def test_encoding_sanitization():
    tree, source = fix(sanitize_encoding(u'# coding: utf-8\n\n\n"вау"'))
    assert source == u'# codang: utf-8\n\n\n"вау"'

def test_sanitize_encoding_must_be_able_to_handle_one_line():
    source = sanitize_encoding(u'# coding: utf-8')
    assert source == u'# codang: utf-8'

def test_sanitize_encoding_must_not_change_source_after_third_line():
    source = sanitize_encoding(u'# coding: utf-8\n\n\ncoding="utf-8"')
    assert source == u'# codang: utf-8\n\n\ncoding="utf-8"'

def test_not_closed_except(project):
    result = do_assist(project, '''
        try:
            code
        except Att|

        code
    ''')

    assert result == ['AttributeError']

def test_glued_indent():
    source = cleantabs('''
        import toimport

        if True:
            toimport(
    ''')

    tree, source = fix(source)
    expected_source = cleantabs('''
        import toimport

        if True: pass''')
    assert source == expected_source

def test_except_with_colon(project):
    result = do_assist(project, '''
        def foo():

            try:
                code
            except Att|:

            other
    ''')

    assert 'AttributeError' in result

def test_if(project):
    result = do_assist(project, '''
        name = 1

        if na|

        other
    ''')

    assert 'name' in result

@pytest.mark.xfail
def test_unclosed_bracket():
    source = cleantabs('''
        func(

        def foo():
            pass

        def boo():
            pass

    ''')

    tree, source = fix(source, 5)
