from supplement.evaluator import infer
from supplement.names import ArgumentName

from .helpers import pytest_funcarg__project

def test_name_reassigning_in_topmost_scope(project):
    scope, line = project.create_scope('''
        test = []
        |
        test = {}
    ''')

    obj = scope.get_name('test', line)
    assert 'append' in obj

    obj = scope['test']
    assert 'keys' in obj

def test_name_reassigning_in_inner_scope(project):
    scope, line = project.create_scope('''
        test = []

        def func():
            |
            test = {}
    ''')

    obj = scope.find_name('test', line)
    assert 'append' in obj

    obj = scope['test']
    assert 'keys' in obj

def test_argument_reassigning(project):
    scope, line = project.create_scope('''
        def func(test):
            |
            test = {}
    ''')

    obj = scope.get_name('test', line)
    assert isinstance(obj, ArgumentName)

    obj = scope['test']
    assert 'keys' in obj


def test_attributes_of_inherited_class(project):
    scope, line = project.create_scope('''
        class Boo(object):
            def boo(self):
                pass

        class Foo(Boo):
            def foo(self):
                pass|
    ''')

    obj = scope.get_name('self', line)
    assert 'boo' in obj

def test_class_object_must_provide_attributes_assigned_in_its_methods(project):
    scope, line = project.create_scope('''
        class Boo(object):
            def boo(self):
                self.boo_attr = []

        boo = Boo()
        |
    ''')

    obj = scope.get_name('boo', line)
    assert 'boo_attr' in obj
    assert 'append' in obj['boo_attr']

def test_class_object_must_provide_attributes_assigned_in_parent_methods(project):
    scope, line = project.create_scope('''
        class Boo(object):
            def boo(self):
                self.boo_attr = []

        class Foo(Boo):
            pass

        foo = Foo()
        |
    ''')

    obj = scope.get_name('foo', line)
    assert 'boo_attr' in obj
    assert 'append' in obj['boo_attr']

def test_assign_to_complex_slice(project):
    scope, line = project.create_scope('''
        class Foo(object):
            def boo(self):
                self.boo_attr = []

            def foo(self):
                self.boo_attr[:] = []

        foo = Foo()
        |
    ''')

    obj = scope.get_name('foo', line)
    assert 'append' in obj['boo_attr']

def test_assign_to_attribute_of_attribute(project):
    scope, line = project.create_scope('''
        class Foo(object):
            def boo(self):
                self.boo_attr = []
                self.boo_attr.foo_attr = {}

        foo = Foo()
        |
    ''')

    obj = scope.get_name('foo', line)
    assert 'append' in obj['boo_attr']

def test_for_names(project):
    scope, line = project.create_scope('''
        for n, (m, l) in [('', ({}, []))]:
            pass|
    ''')

    obj = scope.get_name('n')
    assert 'lower' in obj

    obj = scope.get_name('m')
    assert 'keys' in obj

    obj = scope.get_name('l')
    assert 'append' in obj

def test_method_name_call_should_resolve_self_properly(project):
    scope, line = project.create_scope('''
        class Foo(object):
            def foo(self):
                return self.aaa

            def bar(self):
                self.aaa = 'name'
                result = self.foo()
                |
    ''')

    obj = scope.get_name('result')
    assert 'lower' in obj

def test_pattern_matching(project):
    scope = project.create_scope('''
        a, [b, c] = [{}, ["", []]]
    ''')

    obj = scope['a']
    assert 'keys' in obj

    obj = scope['b']
    assert 'lower' in obj

    obj = scope['c']
    assert 'append' in obj

def test_name_introduced_by_except_clause(project):
    scope1, line1, scope2, line2 = project.create_scope('''
        class Exc(Exception):
            def __init__(self):
                self.msg = []

        try:
            pass
        except Exc as e:
            1 == 2
            pass|

        code
        |
    ''')

    obj = infer('e.msg', scope1, line1)
    assert 'append' in obj

    result = scope2.get_names(line2)
    assert 'e' not in result

def test_name_introduced_by_with_statement(project):
    scope1, line1, scope2, line2 = project.create_scope('''
        with open("fname") as f:
            pass|

        code
        |
    ''')

    obj = scope1.get_name('f', line1)
    assert obj

    result = scope2.get_names(line2)
    assert 'f' not in result

def test_name_in_list_comprehension(project):
    scope, line = project.create_scope('''
        data = [(x, y) for x in (1, 2, 3) for y in ("1", "2", "3")]
        for a, b in data:
            |
            pass
    ''')

    obj = scope.get_name('data', line)
    assert 'append' in  obj

    obj = scope.get_name('a', line)
    assert 'numerator' in  obj

    obj = scope.get_name('b', line)
    assert 'split' in  obj

def test_name_in_generator_expression(project):
    scope, line = project.create_scope('''
        def foo(arg):
            return arg

        for a, b in foo((x, y) for x in (1, 2, 3) for y in ("1", "2", "3")):
            |
            pass
    ''')

    obj = scope.get_name('a', line)
    assert 'numerator' in  obj

    obj = scope.get_name('b', line)
    assert 'split' in  obj
