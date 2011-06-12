from supplement.evaluator import infer
from supplement.scope import StaticScope, get_scope_at

from .helpers import pytest_funcarg__project, cleantabs

def pytest_funcarg__scope(request):
    project = pytest_funcarg__project(request)
    return StaticScope('test', project)

def test_string(scope):
    obj = infer("'str'", scope)
    assert 'lower' in obj

def test_dict(scope):
    obj = infer("{}", scope)
    assert 'keys' in obj

def test_list(scope):
    obj = infer("[]", scope)
    assert 'append' in obj

def test_tuple(scope):
    obj = infer("5, 'sss'", scope)
    assert 'append' not in obj
    assert 'index' in obj

def test_number(scope):
    obj = infer("100.5", scope)
    assert 'real' in obj

def test_instance_of_builtin_class(scope):
    obj = infer("set()", scope)
    assert 'add' in obj

    obj = infer("dict()", scope)
    assert 'keys' in obj

def test_eval_of_assigned_name(project):
    scope = project.create_scope("""
        d = dict()
    """)

    obj = infer('d', scope)
    assert 'iterkeys' in obj
    assert 'Class' not in obj.get_object().__class__.__name__

def test_eval_of_multi_assigned_name_from_tuple(project):
    scope = project.create_scope("""
        d, l = {}, []
    """)

    obj = infer('d', scope)
    assert 'iterkeys' in obj

    obj = infer('l', scope)
    assert 'append' in obj

def test_eval_of_multi_assigned_name_from_list(project):
    scope = project.create_scope("""
        d, l = [{}, []]
    """)

    obj = infer('d', scope)
    assert 'iterkeys' in obj

    obj = infer('l', scope)
    assert 'append' in obj

def test_eval_of_multi_assigned_name_from_imported_seq(project):
    project.create_module('toimport', '''
        value = [{}, []]
    ''')

    scope = project.create_scope('''
        import toimport
        d, l = toimport.value
    ''')

    obj = infer('d', scope, 3)
    assert 'iterkeys' in obj

    obj = infer('l', scope, 3)
    assert 'append' in obj

def test_eval_of_seq_item_get(project):
    scope = project.create_scope('''
        seq_value = [{}, []]
        d = seq_value[0]
        l = seq_value[1]
    ''')

    obj = infer('d', scope, 4)
    assert 'iterkeys' in obj

    obj = infer('l', scope, 4)
    assert 'append' in obj

def test_eval_of_dict_item_get(project):
    scope = project.create_scope('''
        dict_value = {'aaa':{}, 2:[]}
        d = dict_value['aaa']
        l = dict_value[2]
    ''')

    obj = infer('d', scope, 4)
    assert 'iterkeys' in obj

    obj = infer('l', scope, 4)
    assert 'append' in obj

def test_eval_of_function_call_without_arguments(project):
    scope = project.create_scope('''
        def func():
            return []
    ''')

    obj = infer('func()', scope)
    assert 'append' in obj

def test_eval_of_function_call_with_arguments(project):
    scope = project.create_scope('''
        def func(arg):
            return arg
    ''')

    obj = infer('func([])', scope, 3)
    assert 'append' in obj

def test_eval_of_recursive_function_call(project):
    scope = project.create_scope('''
        def func():
            return func()
            return []
    ''')

    obj = infer('func()', scope, 4)
    assert 'append' in obj

def test_eval_of_ping_pong_call(project):
    scope = project.create_scope('''
        def ping():
            return pong()
            return []

        def pong():
            return ping()
    ''')

    obj = infer('ping()', scope, 7)
    assert 'append' in obj

def test_fallback_to_safe_result_on_rec_func_eval(project):
    scope = project.create_scope('''
        def func():
            return func()
    ''')

    obj = infer('func()', scope, 3)
    assert not obj.get_names()

def test_evaluation_of_func_must_find_any_meaning_result(project):
    scope = project.create_scope('''
        import os.path
        def func():
            return str('filename')
            return ""
    ''')

    obj = infer('func()', scope, 5)
    assert 'lower' in obj

def test_evaluation_of_function_object(project):
    project.create_module('toimport', '''
        def func(arg):
            return arg
    ''')

    scope = project.create_scope('''
        import toimport
    ''')

    obj = infer('toimport.func([])', scope)
    assert 'append' in obj

def test_function_object_must_correctly_locate_its_source(project):
    project.create_module('toimport', '''
        def func():
            return []

        oldfunc = func

        def func(arg):
            return {}
    ''')

    scope = project.create_scope('''
        import toimport
    ''')

    obj = infer('toimport.oldfunc()', scope)
    assert 'append' in obj

def test_dyn_method_call_must_know_exact_self_type(project):
    project.create_module('toimport', '''
        class Foo(object):
            def foo(self):
                return self.bar()

        class Bar(Foo):
            def bar(self):
                return self

        bar = Bar()
    ''')

    scope = project.create_scope('''
        from toimport import Bar, bar
    ''')

    obj = infer('bar.foo()', scope, 2)
    assert 'bar' in obj

    obj = infer('Bar().foo()', scope, 2)
    assert 'bar' in obj

def test_method_scope_must_know_self_type(project):
    scope = get_scope_at(project, cleantabs('''
        class Foo(object):
            def foo(self):
                return self

            def bar(self):
                pass
    '''), 3)

    obj = infer('self', scope, 7)
    assert 'bar' in obj

def test_assign_chain(project):
    scope = project.create_scope('''
        def boo(name):
            return []

        def foo(name, data):
            p = data[name] = boo(name)
    ''')

    obj = infer('p', scope.get_child_by_lineno(4), 6)
    assert 'append' in obj

def test_dict_must_remeber_its_subscript_assignments(project):
    scope = project.create_scope('''
        d = {}
        d['index'] = []
    ''')

    obj = infer('d["index"]', scope, 3)
    assert 'append' in obj

def test_op_getitem_with_non_value_object(project):
    scope = project.create_scope('''
        def foo(name):
            data = {}
            data['sss'] = []
            p = data[name]
    ''')

    obj = infer('p', scope.get_child_by_lineno(1), 4)
    assert 'append' in obj
