import time
import pytest

from supplement.assistant import assist

from .helpers import pytest_funcarg__project, get_source_and_pos

def do_assist(project, source, filename=None):
    filename = filename or 'test.py'
    source, pos = get_source_and_pos(source)
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

    assert result == ['test']

    result = do_assist(project, '''
        import toimport
        toimport.__''')

    assert result == ['__builtins__', '__doc__', '__file__', '__name__']

def test_assist_for_dotted_module_attributes(project):
    project.create_module('package.toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        import package.toimport
        package.''')

    assert result == ['toimport']


    result = do_assist(project, '''
        import package.toimport
        package.toimport.''')

    assert result == ['test']

def test_assist_for_imported_names_attributes(project):
    project.create_module('toimport', '''
        test = "string"
    ''')

    result = do_assist(project, '''
        from toimport import test
        test.''')

    assert 'lower' in result
    assert 'isdigit' in result

def test_assist_after_curve_brackets(project):
    result = do_assist(project, '''{1:()}.''')
    assert 'iterkeys' in result

def test_assist_after_square_brackets(project):
    result = do_assist(project, '''[1].''')
    assert 'append' in result

def test_assist_for_list_item(project):
    result = do_assist(project, '''["string"][0].''')
    assert 'lower' in result

def test_assist_for_dict_item(project):
    result = do_assist(project, '''{"key":[]}["key"].''')
    assert 'append' in result

def test_assist_for_call(project):
    result = do_assist(project, '''dict().''')
    assert 'iterkeys' in result

def test_assist_for_module_imported_from_package(project):
    project.create_module('package.toimport', '''
        test = 1
    ''')

    result = do_assist(project, '''
        from package import toimport
        toimport.''')

    assert result == ['test']

@pytest.mark.slow
def test_assist_for_names_in_changed_module(project, tmpdir):
    project.set_root(str(tmpdir))

    m = tmpdir.join('toimport.py')
    m.write('name1 = 1')

    def get_result(): return do_assist(project, '''
        import toimport
        toimport.''')

    result = get_result()
    assert result == ['name1']

    time.sleep(1)
    m.write('name1 = 1\nname2 = 2')
    time.sleep(2)

    result = get_result()
    assert result == ['name1', 'name2']

def test_assist_must_not_show_names_below_current_cursor(project):
    result = do_assist(project, '''
        name1 = 1
        name|
        name2 = 2
    ''')

    assert result == ['name1']