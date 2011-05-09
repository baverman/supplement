from supplement.scope import get_scope_at
from supplement.names import ArgumentName

from .helpers import pytest_funcarg__project, cleantabs

def test_name_reassigning_in_topmost_scope(project):
    source = cleantabs('''
        test = []

        test = {}
    ''')

    scope = get_scope_at(project, source, 2)

    obj = scope.get_name('test', 2)
    assert 'append' in obj

    obj = scope['test']
    assert 'iterkeys' in obj

def test_name_reassigning_in_inner_scope(project):
    source = cleantabs('''
        test = []

        def func():

            test = {}
    ''')

    scope = get_scope_at(project, source, 4)

    obj = scope.find_name('test', 4)
    assert 'append' in obj

    obj = scope['test']
    assert 'iterkeys' in obj

def test_argument_reassigning(project):
    source = cleantabs('''
        def func(test):

            test = {}
    ''')

    scope = get_scope_at(project, source, 2)

    obj = scope.get_name('test', 2)
    assert isinstance(obj, ArgumentName)

    obj = scope['test']
    assert 'iterkeys' in obj
