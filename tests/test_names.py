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


def test_attributes_of_inherited_class(project):
    source = cleantabs('''
        class Boo(object):
            def boo(self):
                pass

        class Foo(Boo):
            def foo(self):
                pass
    ''')

    scope = get_scope_at(project, source, 7)

    obj = scope.get_name('self', 7)
    assert 'boo' in obj

def test_class_object_must_provide_attributes_assigned_in_its_methods(project):
    source = cleantabs('''
        class Boo(object):
            def boo(self):
                self.boo_attr = []

        boo = Boo()
    ''')

    scope = get_scope_at(project, source, 5)

    obj = scope.get_name('boo', 5)
    assert 'boo_attr' in obj
    assert 'append' in obj['boo_attr']

def test_class_object_must_provide_attributes_assigned_in_parent_methods(project):
    source = cleantabs('''
        class Boo(object):
            def boo(self):
                self.boo_attr = []

        class Foo(Boo):
            pass

        foo = Foo()
    ''')

    scope = get_scope_at(project, source, 8)

    obj = scope.get_name('foo', 8)
    assert 'boo_attr' in obj
    assert 'append' in obj['boo_attr']

def test_for_names(project):
    source = cleantabs('''
        for n, (m, l) in []:
            pass
    ''')

    scope = get_scope_at(project, source, 2)

    obj = scope.get_name('n')
    assert obj

    obj = scope.get_name('m')
    assert obj

    obj = scope.get_name('l')
    assert obj

def test_method_name_call_should_resolve_self_properly(project):
    source = cleantabs('''
        class Foo(object):
            def foo(self):
                return self.aaa

            def bar(self):
                self.aaa = 'name'
                result = self.foo()
    ''')

    scope = get_scope_at(project, source, 8)
    obj = scope.get_name('result')
    assert 'lower' in obj
