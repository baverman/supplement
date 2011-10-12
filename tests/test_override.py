from .helpers import pytest_funcarg__project, do_docstring, do_assist

def test_re_compile_must_return_good_object(project):
    project.register_hook('supplement.hooks.override')
    result = do_assist(project, '''
        import re

        re.compile('match').|
    ''')

    assert 'groups' in result
    assert 'findall' in result

def test_builtin_override(project):
    project.register_hook('supplement.hooks.override')
    result = do_assist(project, '''
        f = open('file')
        f.|
    ''')

    assert 'read' in result

def test_docstring_of_overrided_func(project):
    project.register_hook('supplement.hooks.override')
    sig, docstring = do_docstring(project, '''
        open(|)
    ''')

    assert sig.startswith('open')
    assert docstring is None