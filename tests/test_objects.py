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

def test_class_object_must_provide_attributes_assigned_in_its_methods(project):
    project.create_module('toimport', '''
        class Boo(object):
            def boo(self):
                self.boo_attr = []
    ''')

    scope = project.create_scope('''
        import toimport

        boo = toimport.Boo()
    ''')

    obj = scope.get_name('boo')
    assert 'boo_attr' in obj
    assert 'append' in obj['boo_attr']
