import os.path
import ast
import pytest

from supplement.assistant import infer
from supplement.scope import Scope, traverse_tree
from supplement.calls import CallExtractor

from .helpers import pytest_funcarg__project, do_assist

def pytest_generate_tests(metafunc):
    if 'fname' in metafunc.funcargnames:
        for top, dirs, files in os.walk('supplement'):
            if top.endswith('override'):
                continue

            for fname in files:
                if fname.endswith('.py') and fname != '__init__.py':
                    metafunc.addcall(funcargs={'fname':os.path.join(top, fname)})

@pytest.mark.slow
def test_evalutor_must_resolve_all_call_info_without_errors(project, fname):
    scope = Scope(ast.parse(open(fname).read()), '', None, 'module')
    scope.project = project
    scope.filename = fname

    call_extractor = CallExtractor()
    for s in traverse_tree(scope):
        for line, func, args in call_extractor.process(s.node):
            if not args: continue
            func = s.eval(func, False)

def test_calls_update(project):
    scope = project.create_scope('''
        def bar():
            pass

        def foo(arg):
            map(arg, bar())

        foo(int)
    ''')

    project.calldb.collect_calls(scope)
    assert len(project.calldb.calls[(None, 'foo')]) == 1

    scope = project.create_scope('''
        def bar():
            pass

        def foo(arg):
            map(arg, bar())
    ''')

    project.calldb.collect_calls(scope)
    assert len(project.calldb.calls[(None, 'foo')]) == 0

def test_calldb_must_provide_arguments_for_function(project):
    result = do_assist(project, '''
        def foo(arg):
            arg.a|

        foo([])
    ''')

    assert 'append' in result

def test_calldb_must_provide_arguments_for_constructor(project):
    result = do_assist(project, '''
        class Foo(object):
            def __init__(self, arg):
                self.arg = arg

        Foo([]).arg.a|
    ''')

    assert 'append' in result

def test_calldb_must_provide_arguments_for_methods(project):
    result = do_assist(project, '''
        class Foo(object):
            def foo(self, arg):
                arg.a|

        Foo().foo([])
    ''')

    assert 'append' in result

def test_calldb_for_imported_function(project):
    m = project.create_module('toimport', '''
        def foo(arg):
            pass
    ''')

    scope = project.create_scope('''
        from toimport import foo
        foo([])
    ''')

    project.calldb.collect_calls(scope)
    result = infer('arg', m.get_scope_at(2))
    assert 'append' in result

def test_calldb_for_imported_class(project):
    project.create_module('toimport', '''
        class Foo(object):
            def __init__(self, bar):
                self.bar = bar
    ''')

    result = do_assist(project, '''
        from toimport import Foo
        Foo([]).bar.a|
    ''')

    assert 'append' in result
