from .helpers import pytest_funcarg__project

from supplement.evaluator import infer
from supplement.scope import StaticScope

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
