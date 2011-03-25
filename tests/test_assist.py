from supplement.assistant import assist

from .helpers import pytest_funcarg__project, cleantabs

def do_assist(project, source, filename=None, pos=None):
    filename = filename or 'test.py'

    if not pos:
        source = cleantabs(source)

    pos = pos or len(source)

    return assist(project, source, pos, filename)

def test_assist_for_module_names(project):
    result = do_assist(project, '''
        test = 1
        te''')

    assert result == ['test']

def test_assist_for_module_names_without_match(project):
    result = do_assist(project, '''
        test = 1
        ''')

    assert result[0] == 'test'

def test_assist_for_builtin_names(project):
    result = do_assist(project, '''
        opened_files = []
        ope''')

    assert result == ['opened_files', 'open']

    result = do_assist(project, '''
        opened_files = []
        raise Key''')

    assert result == ['KeyError', 'KeyboardInterrupt']

def test_assist_for_imported_names(project):
    project.create_module('toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        from toimport import test
        te''')

    assert result == ['test']

def test_assist_for_star_imported_names(project):
    project.create_module('toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        from toimport import *
        te''')

    assert result == ['test']

def test_assist_for_function_names(project):
    result = do_assist(project, '''
        test1 = 1

        def func(arg1, arg2):
            test2 = 2
            ''')

    assert result[:5] == ['arg1', 'arg2', 'test2', 'func', 'test1']

def test_assist_for_object_attributes(project):
    project.create_module('toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        import toimport
        toimport.''')

    assert result == ['test']