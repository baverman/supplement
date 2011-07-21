from .helpers import pytest_funcarg__project, do_assist

def test_re_compile_must_return_good_object(project):
    result = do_assist(project, '''
        import re

        re.compile('match').|
    ''')

    assert 'groups' in result
    assert 'findall' in result