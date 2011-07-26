from .helpers import pytest_funcarg__project

from supplement.calls import CallDB

def test_calls_update(project):
    scope = project.create_scope('''
        def bar():
            pass

        def foo(arg):
            map(arg, bar())

        foo(int)
    ''')

    cdb = CallDB()
    cdb.collect_calls(scope)
    assert len(cdb.calls['foo']) == 1

    scope = project.create_scope('''
        def bar():
            pass

        def foo(arg):
            map(arg, bar())
    ''')

    cdb.collect_calls(scope)
    assert len(cdb.calls['foo']) == 0


