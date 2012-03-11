from supplement.scope import get_scope_at

from .helpers import cleantabs, pytest_funcarg__project

def check_scope(project, source, names, cont=True):
    def check(line, name):
        result = get_scope_at(project, source, line, continous=cont).fullname
        assert result == name, "[%s] must be [%s] at line %d" % (result, name, line)

    for line, name in names.iteritems():
        check(line, name)

def test_module_scope(project):
    result = get_scope_at(project, cleantabs("""
        test1 = 1

        test2 = 2
    """), 2).fullname

    assert result == ''

def test_function_scope(project):
    source = cleantabs("""
        test1 = 1

        def func():
            pass

        test2 = 2
    """)

    check_scope(project, source, {
        2: '',
        3: 'func',
        4: 'func',
        5: 'func',
        6: ''
    })

def test_nested_scopes(project):
    source = cleantabs("""

        def func1():

            def inner():
                pass

            ddd = 1


        def func2():
            pass

    """)

    check_scope(project, source, {
        1: '',
        2: 'func1',
        3: 'func1',
        4: 'func1.inner',
        5: 'func1.inner',
        6: 'func1.inner',
        7: 'func1',
        8: 'func1',
        9: 'func1',
        10: 'func2',
    })

def test_class_scope(project):
    source = cleantabs("""
        class Cls(object):

            def m1(self):
                pass

            @staticmethod
            def m2():
                pass

    """)

    check_scope(project, source, {
        1: 'Cls',
        2: 'Cls',
        3: 'Cls.m1',
        5: 'Cls.m1',
        6: 'Cls.m2',
        7: 'Cls.m2',
        9: 'Cls.m2',
    })

def test_eof_scope(project):
    source = cleantabs("""
        def func(self):
            pass

    """)

    check_scope(project, source, {
        1: 'func',
        2: 'func',
        3: 'func',
    })

def test_non_continous_scope(project):
    source = cleantabs("""
        class Cls(object):

            def m1(self):
                pass

            @staticmethod
            def m2():
                pass


        class Klass(object):
            pass

    """)

    check_scope(project, source, {
        1: 'Cls',
        2: 'Cls',
        3: 'Cls.m1',
        5: 'Cls',
        6: 'Cls.m2',
        7: 'Cls.m2',
        9: '',
        10: '',
        11: 'Klass',
    }, False)

def test_scope_with_decorators(project):
    source = cleantabs("""
        @decorator
        class Cls(object):
            def m1(self):
                pass

            @staticmethod
            def m2():
                pass
    """)

    check_scope(project, source, {
        1: 'Cls',
        2: 'Cls',
        3: 'Cls.m1',
        5: 'Cls.m1',
        6: 'Cls.m2',
        7: 'Cls.m2',
    }, True)
