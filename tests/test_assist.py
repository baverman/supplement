import pytest
import time

from supplement.assistant import assist, get_location, get_context

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
    assert 'keys' in result

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
    assert 'keys' in result

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
    project.monitor.boo()

    result = get_result()
    assert result == ['name1', 'name2']

def test_assist_must_not_show_names_below_current_cursor(project):
    result = do_assist(project, '''
        name1 = 1
        name|
        name2 = 2
    ''')

    assert result == ['name1']

def test_get_location_must_return_name_location(project):
    source, pos = get_source_and_pos('''
        def aaa():
            pass

        aa|a()
    ''')

    line, fname = get_location(project, source, pos, 'test.py')
    assert fname == 'test.py'
    assert line == 1

def test_get_location_must_return_name_location_for_imported_names(project):
    project.create_module('toimport', '''
        def aaa():
            pass
    ''')

    source, pos = get_source_and_pos(u'''
        import toimport
        toimport.aa|a()
    ''')

    line, fname = get_location(project, source, pos, 'test.py')
    assert fname == 'toimport.py'
    assert line == 1

def test_get_location_must_return_name_location_for_imported_modules(project):
    source, pos = get_source_and_pos(u'''
        import sys

        def foo():
            sy|s
    ''')

    line, fname = get_location(project, source, pos, 'test.py')
    assert fname == None
    assert line == 1

def test_import_package_modules_from_init(project, tmpdir):
    project.set_root(str(tmpdir))
    pkgdir = tmpdir.join('package')
    pkgdir.mkdir()

    source, pos = get_source_and_pos('''
        import module

        def foo():
            module.n|
    ''')

    pkg = pkgdir.join('__init__.py')
    pkg.write(source)

    m = pkgdir.join('module.py')
    m.write('name = []')

    result = assist(project, source, pos, str(pkg))
    assert result == ['name']

def test_import_context():
    source, pos = get_source_and_pos('''
        import |
    ''')
    result = get_context(source, pos)
    assert result == ('import', 1, '', '', None)

    source, pos = get_source_and_pos('''
        import package|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 1, '', 'package', None)

    source, pos = get_source_and_pos('''
        import package.module|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 1, 'package', 'module', None)

    source, pos = get_source_and_pos('''
        import package.module.submodule|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 1, 'package.module', 'submodule', None)

    source, pos = get_source_and_pos('''
        import package1.module1, package2.module2|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 1, 'package2', 'module2', None)

    source, pos = get_source_and_pos('''
        import (package1.module1,
            package2.module2|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 2, 'package2', 'module2', None)

    source, pos = get_source_and_pos('''
        import package1.module1, \\
            package2.module2|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 2, 'package2', 'module2', None)

def test_from_context():
    source, pos = get_source_and_pos('''
        from package|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 1, '', 'package', None)

    source, pos = get_source_and_pos('''
        from package.module|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 1, 'package', 'module', None)

    source, pos = get_source_and_pos('''
        from ..package.module|
    ''')
    result = get_context(source, pos)
    assert result == ('import', 1, '..package', 'module', None)

def test_from_import_context():
    source, pos = get_source_and_pos('''
        from package import module|
    ''')
    result = get_context(source, pos)
    assert result == ('from-import', 1, 'package', 'module', None)

    source, pos = get_source_and_pos('''
        from . import module|
    ''')
    result = get_context(source, pos)
    assert result == ('from-import', 1, '.', 'module', None)

    source, pos = get_source_and_pos('''
        from ..package import module1, module2|
    ''')
    result = get_context(source, pos)
    assert result == ('from-import', 1, '..package', 'module2', None)

def test_simple_expression_context():
    source, pos = get_source_and_pos('''
        module.attr|
    ''')
    result = get_context(source, pos)
    assert result == ('expr', 1, 'module', 'attr', '')

    source, pos = get_source_and_pos('''
        package.module.attr|
    ''')
    result = get_context(source, pos)
    assert result == ('expr', 1, 'package.module', 'attr', '')

    source, pos = get_source_and_pos('''
        module.func(param1, param2|
    ''')
    result = get_context(source, pos)
    assert result == ('expr', 1, '', 'param2', 'module.func')

def test_expression_context_with_func_ctx_break():
    source, pos = get_source_and_pos('''
        module.func(param1, (package.param2|
    ''')
    result = get_context(source, pos)
    assert result == ('expr', 1, 'package', 'param2', '')

def test_expression_without_func_name():
    source, pos = get_source_and_pos('''
        (param1, (param2,)).attr|
    ''')
    result = get_context(source, pos)
    assert result == ('expr', 1, '(param1,(param2,))', 'attr', '')

def test_complex_expression():
    source, pos = get_source_and_pos('''
        module.func(param1, (param2,))(p1=10, m.p2|
    ''')
    result = get_context(source, pos)
    assert result == ('expr', 1, 'm', 'p2', '')

    source, pos = get_source_and_pos('''
        module.func(param1, (param2,))(p1=10, p2=m.attr|
    ''')
    result = get_context(source, pos)
    assert result == ('expr', 1, 'm', 'attr', '')

def test_dotted_func_call_context():
    source, pos = get_source_and_pos('''
        Foo().foo(param1|
    ''')
    result = get_context(source, pos)
    assert result == ('expr', 1, '', 'param1', 'Foo().foo')

def test_indented_import():
    source, pos = get_source_and_pos('''
        def foo():
            import |
    ''')
    result = get_context(source, pos)
    assert result == ('import', 2, '', '', None)

def test_assistant_must_suggest_function_argument_names(project):
    result = do_assist(project, '''
        def foo(arg1, arg2):
            pass

        # scope guard

        foo(a|
    ''')
    assert 'arg1=' in result
    assert 'arg2=' in result


    project.create_module('toimport', '''
        def foo(arg1, arg2):
            pass
    ''')

    result = do_assist(project, '''
        import toimport
        toimport.foo(a|
    ''')
    assert 'arg1=' in result
    assert 'arg2=' in result

def test_assistant_must_suggest_constructor_argument_names(project):
    result = do_assist(project, '''
        class Foo(object):
            def __init__(self, arg1, arg2):
                pass

        # scope guard

        Foo(|
    ''')
    assert 'arg1=' in result
    assert 'arg2=' in result
    assert 'self=' not in result

    project.create_module('toimport', '''
        class Foo(object):
            def __init__(self, arg1, arg2):
                pass
    ''')

    result = do_assist(project, '''
        import toimport
        toimport.Foo(|
    ''')
    assert 'arg1=' in result
    assert 'arg2=' in result
    assert 'self=' not in result

def test_assistant_must_suggest_argument_names_for_class_functions(project):
    result = do_assist(project, '''
        class Foo(object):
            def __init__(self, arg1, arg2):
                pass

        # scope guard

        Foo.__init__(|
    ''')
    assert 'arg1=' in result
    assert 'arg2=' in result
    assert 'self=' in result

    project.create_module('toimport', '''
        class Foo(object):
            def __init__(self, arg1, arg2):
                pass
    ''')

    result = do_assist(project, '''
        import toimport
        toimport.Foo.__init__(|
    ''')
    assert 'arg1=' in result
    assert 'arg2=' in result
    assert 'self=' in result

def test_assistant_must_suggest_argument_names_for_methods(project):
    result = do_assist(project, '''
        class Foo(object):
            def foo(self, arg1, arg2):
                pass

        # scope guard

        Foo().foo(|
    ''')
    assert 'arg1=' in result
    assert 'arg2=' in result
    assert 'self=' not in result

    project.create_module('toimport', '''
        class Foo(object):
            def foo(self, arg1, arg2):
                pass
    ''')

    result = do_assist(project, '''
        import toimport
        toimport.Foo().foo(|
    ''')
    assert 'arg1=' in result
    assert 'arg2=' in result
    assert 'self=' not in result
