from supplement.scope import get_scope_at

from .helpers import cleantabs

def check_scope(source, names):
    def check(line, name):
        result = get_scope_at(source, line).fullname
        assert result == name

    for line, name in names.iteritems():
        check(line, name)

def test_module_scope():
    result = get_scope_at(cleantabs("""
        test1 = 1

        test2 = 2
    """), 2).fullname

    assert result == ''

def test_function_scope():
    source = cleantabs("""
        test1 = 1

        def func():
            pass

        test2 = 2
    """)

    check_scope(source, {
        2: '',
        3: 'func',
        4: 'func',
        5: ''
    })

def test_nested_scopes():
    source = cleantabs("""

        def func1():

            def inner():
                pass

            ddd = 1


        def func2():
            pass

    """)

    check_scope(source, {
        1: '',
        2: 'func1',
        3: 'func1',
        4: 'func1.inner',
        5: 'func1.inner',
        6: 'func1',
        7: 'func1',
        8: '',
        9: '',
        10: 'func2',
    })

def test_class_scope():
    source = cleantabs("""
        class Cls(object):

            def m1(self):
                pass

            @staticmethod
            def m2():
                pass

    """)

    check_scope(source, {
        1: 'Cls',
        2: 'Cls',
        3: 'Cls.m1',
        5: 'Cls',
        6: 'Cls.m2',
        7: 'Cls.m2',
        9: 'Cls.m2',
    })

def test_eof_scope():
    source = cleantabs("""
        def func(self):
            pass

    """)

    check_scope(source, {
        1: 'func',
        2: 'func',
        3: 'func',
    })
