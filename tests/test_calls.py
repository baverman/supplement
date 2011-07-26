from .helpers import pytest_funcarg__project, do_assist

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
