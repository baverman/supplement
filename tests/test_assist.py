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

def test_assist_for_relative_star_imported_names(project):
    project.create_module('package.toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        from .toimport import *
        te''', filename='package/test.py')

    assert result == ['test']

def test_assist_for_function_names(project):
    result = do_assist(project, '''
        test1 = 1

        def func(arg1, arg2):
            test2 = 2
            ''')

    assert result[:5] == ['arg1', 'arg2', 'test2', 'func', 'test1']

def test_assist_should_return_only_uniq_names(project):
    result = do_assist(project, '''
        test = 1
        test = 2
        te''')

    assert result == ['test']

def test_assist_must_provide_package_names_in_import_statement(project):
    result = do_assist(project, '''
        import o''')

    assert 'os' in result
    assert 'operator' in result

    all_start_with_o = all(r.startswith('o') for r in result)
    assert all_start_with_o

def test_assist_must_provide_package_module_names_in_import_statement(project):
    result = do_assist(project, '''
        import multiprocessing.''')

    assert 'connection' in result

def test_assist_must_provide_module_names_in_import_statement_for_dynamic_packages(project):
    result = do_assist(project, '''
        import os.''')

    assert 'path' in result

def test_assist_for_from(project):
    result = do_assist(project, '''
        from os.pa''')

    assert result == ['path']

def test_assist_for_module_and_names_in_from_import(project):
    result = do_assist(project, '''
        from os import ''')

    assert 'path' in result
    assert 'walk' in result

def test_assist_for_relative_modules(project):
    project.create_module('package.toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        from .''', filename='package/test.py')

    assert result == ['toimport']

def test_assist_for_import_from_relative_modules(project):
    project.create_module('package.toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        from .toimport import ''', filename='package/test.py')

    assert 'test' in result

def test_assist_for_import_from_relative_modules_on_real_fs(project):
    import os.path
    root = os.path.dirname(os.path.dirname(__file__))

    result = do_assist(project, '''
        from .tree import ''', filename=os.path.join(root, 'supplement', 'test.py'))

    assert 'NodeProvider' in result

    result = do_assist(project, '''
        from .helpers import cleantabs, ''', filename=os.path.join(root, 'tests', 'test.py'))

    assert 'TestModule' in result

def test_assist_for_module_attributes(project):
    project.create_module('toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        import toimport
        toimport.''')

    assert result == ['__builtins__', '__doc__', '__file__', '__name__', 'test']

def test_assist_for_dotted_module_attributes(project):
    project.create_module('package.toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        import package.toimport
        package.''')

    assert result == ['__doc__', '__name__', 'toimport']


    result = do_assist(project, '''
        import package.toimport
        package.toimport.''')

    assert result == ['__builtins__', '__doc__', '__file__', '__name__', 'test']
