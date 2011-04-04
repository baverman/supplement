from .helpers import pytest_funcarg__project

from supplement.evaluator import infer
from supplement.scope import StaticScope

def test_string(project):
    scope = StaticScope('test', project)

    obj = infer("'str'", scope)
    assert 'lower' in obj

def test_dict(project):
    scope = StaticScope('test', project)

    obj = infer("{}", scope)
    assert 'keys' in obj

def test_list(project):
    scope = StaticScope('test', project)

    obj = infer("[]", scope)
    assert 'append' in obj

def test_tuple(project):
    scope = StaticScope('test', project)

    obj = infer("()", scope)
    assert 'append' not in obj
    assert 'index' in obj

def test_number(project):
    scope = StaticScope('test', project)

    obj = infer("100.5", scope)
    assert 'real' in obj
