from .helpers import pytest_funcarg__project

from supplement.evaluator import infer
from supplement.scope import StaticScope

def test_string(project):
    scope = StaticScope('test', project)

    obj = infer("'str'", scope)
    assert 'lower' in obj
