# -*- coding: utf-8 -*-
import pytest
from supplement.fixer import fix, sanitize_encoding

from .helpers import pytest_funcarg__project, do_assist, cleantabs

def test_encoding_sanitization():
    tree, source = fix(sanitize_encoding('# coding: utf-8\n\n\n"вау"'))
    assert source == '# codang: utf-8\n\n\n"вау"'

def test_sanitize_encoding_must_be_able_to_handle_one_line():
    source = sanitize_encoding('# coding: utf-8')
    assert source == '# codang: utf-8'

def test_sanitize_encoding_must_not_change_source_after_third_line():
    source = sanitize_encoding('# coding: utf-8\n\n\ncoding="utf-8"')
    assert source == '# codang: utf-8\n\n\ncoding="utf-8"'

def test_incomlete_if(project):
    result = do_assist(project, '''
        var = 1
        if |
    ''')
    assert 'var' in result

    result = do_assist(project, '''
        var = 1
        if v|
    ''')
    assert 'var' in result

    result = do_assist(project, '''
        def foo():
            var = 1
            if |
    ''')
    assert 'var' in result

    result = do_assist(project, '''
        def foo():
            var = 1
            if v|
    ''')
    assert 'var' in result

    result = do_assist(project, '''
        def foo():
            var = 1
            if |

            do_something()

        def boo():
            pass
    ''')
    assert 'var' in result

    result = do_assist(project, '''
        def foo():
            var = 1
            if v|

            do_something()

        def boo():
            pass
    ''')
    assert 'var' in result

def test_not_closed_except(project):
    result = do_assist(project, '''
        try:
            code
        except Att|

        code
    ''')

    assert result == ['AttributeError']

def test_not_closed_try(project):
    result = do_assist(project, '''
        var = 1

        try:
            |

        code
    ''')
    assert 'var' in result

    result = do_assist(project, '''
        var = 1

        try:
            v|

        code
    ''')
    assert 'var' in result

def test_except_with_colon(project):
    result = do_assist(project, '''
        def foo():

            try:
                code
            except Att|:

            other
    ''')

    assert 'AttributeError' in result

def test_incomplete_for(project):
    result = do_assist(project, '''
        var = 1
        for a in |
    ''')
    assert 'var' in result

    result = do_assist(project, '''
        var = 1
        for a in v|
    ''')
    assert 'var' in result

def test_unclosed_bracket(project):
    result = do_assist(project, '''
        var = 1

        map(|

        def foo():
            pass
    ''')
    assert 'var' in result

    result = do_assist(project, '''
        var = 1

        map(|

    ''')
    assert 'var' in result

    result = do_assist(project, '''
        var = 1

        map(|''')
    assert 'var' in result

    result = do_assist(project, '''
        var = 1

        if True:
            len(v|
    ''')
    assert 'var' in result

def test_dotted(project):
    result = do_assist(project, '''
        def foo():
            var = []
            var.| ;True
    ''')
    assert 'append' in result

def test_dot_in_for(project):
    result = do_assist(project, '''
        var = []
        for r in var.|  :
            pass
    ''')
    assert 'append' in result
