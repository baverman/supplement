from .helpers import pytest_funcarg__project

def test_instance_attributes(project):
    m = project.create_module('test', '''
        test = 'string'
    ''')

    obj = m['test']

    assert 'lower' in obj

def test_attributes_of_class_with_deep_inheritance_level(project):
    m = project.create_module('test', '''
        class Foo(object):
            def foo(self): pass

        class Bar(Foo):
            def bar(self): pass

        class Boo(Bar): pass
    ''')

    obj = m['Boo']

    assert 'bar' in obj
    assert 'foo' in obj