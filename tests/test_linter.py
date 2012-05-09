# -*- coding: utf-8 -*-

import re
from supplement.linter import lint
from .helpers import cleantabs

def get_source_and_expected_result(source):
    source = cleantabs(source)
    result = []
    while True:
        m = re.search(r'([$!])(.+?)\1', source)
        if not m: break

        lineno = source.count('\n', 0, m.start()) + 1
        offset = m.start() - len(''.join(source.splitlines(True)[:lineno-1]))

        c = m.group(1)
        if c == '$':
            message = 'Unused name (W01): ' + m.group(2)
        else:
            message = 'Unknown name (E01): ' + m.group(2)
        result.append(((lineno, offset), m.group(2), message))
        source= source.replace(c, '', 2)

    return source, result

def assert_names(source):
    source, expected = get_source_and_expected_result(source)
    result = lint(source)
    assert set(result) == set(expected)

def test_module_level_variables_must_be_skipped_as_unused():
    assert_names('''
        var = 1
    ''')

def test_unused_imports():
    assert_names('''
        import $package1$.module, package1.module as $modulo$

        from ..package import *
        from .package.module import $boo$, $foo$
        from . import $bar$
    ''')

def test_module_level_unused_names():
    assert_names('''
        for $a$, b in []:
            b
    ''')

def test_underscore_names():
    assert_names('''
        for _, _test in []:
            pass
    ''')

def test_unknown_names():
    assert_names('''
        !name!
    ''')

def test_builtin_names():
    assert_names('''
        True
        None
        __builtins__
        Exception
    ''')

def test_func_and_arg_names():
    assert_names('''
        def boo($bar$):
            def $bar$():
                pass

        def foo($arg$, *args, **kwargs):
            !bar!
            boo()
            args
            kwargs

        foo()
    ''')

def test_class_defenitions():
    assert_names('''
        class Boo(object):
            def boo($self$):
                pass

            class Foo(object): pass

            def foo($self$):
                class $Bar$(object):
                    pass
        Boo()
    ''')

def test_declaration_action_scope():
    assert_names('''
        def bar():
            boo = 1
            $boo$ = boo + 1

            $foo$ = !foo! + 1
    ''')

def test_self_changed_names():
    assert_names('''
        def bar():
            boo = 1
            $boo$ += 1
    ''')

def test_looped_name_usage_in_for_statements():
    assert_names('''
        def bar():
            for i in []:
                i += 1

            found = False
            while not found:
                found, $boo$ = True, False

            boo = 1
            return boo
    ''')

def test_generator_and_list_expressions():
    assert_names('''
        def bar():
            (r for r in (1,2,3))
            [rr for rr in (1,2,3)]
    ''')

def test_class_scope_must_not_hide_global_names():
    assert_names('''
        from . import bar

        class Bar(object):
            def bar($self$):
                return bar()
    ''')

def test_unicode():
    assert_names(u'''
        s = "юникод %s" % !test!
    ''')

def test_unused_function_arguments():
    assert_names('''
        def bar(boo, $foo$):
            return boo
    ''')

def test_simple_if():
    assert_names('''
        def foo():
            boo = 1
            if True:
                boo = 2

            return boo
    ''')

def test_complex_if():
    assert_names('''
        def foo():
            boo = 1
            if True:
                boo = 2
                $bar$ = 1
            elif False:
                boo = 1
                map(!bar!)
            else:
                if True:
                    boo = 0

            return boo
    ''')

def test_near_branches():
    assert_names('''
        def foo():
            if True:
                boo = 2

            if True:
                boo = 0

            return boo
    ''')

def test_parent_subbranches1():
    assert_names('''
        def foo():
            if True:
                boo = 2

            if True:
                return boo
    ''')

def test_parent_subbranches2():
    assert_names('''
        def foo():
            if True:
                boo = 1

                if True:
                    boo = 2

                if True:
                    return boo
    ''')

def test_parent_subbranches3():
    assert_names('''
        def foo():
            if True:
                $boo$ = 1
            else:
                return !boo!
    ''')

def test_lambda():
    assert_names('''
        def foo():
            return lambda boo, bar: boo + bar
    ''')

def test_lambda_assigned_to_var():
    assert_names('''
        def foo():
            $result$ = lambda boo, bar: boo + bar
    ''')

def test_lambda_assigned_to_var():
    assert_names('''
        from __future__ import absolute_import
    ''')

def test_for_loop_alt_logic_branches():
    assert_names('''
        def foo():
            for _ in []:
                bar = 1
                break
            else:
                bar = 2

            map(bar)
    ''')

def test_alternative_names_in_try_blocks():
    assert_names('''
        def foo():
            try:
                bar = 1
            except:
                bar = 2
                $boo$ = 4
            except:
                bar = 3
                map(!boo!)

            map(bar)
    ''')

def test_alternative_names_in_try_blocks_with_exception_vars():
    assert_names('''
        def foo():
            try:
                bar = 1
            except Exception as e:
                bar = 2
                map(e)
            except:
                bar = 3
                map(!e!)

            map(bar)
    ''')

def test_function_name_with_decorator():
    assert_names('''
        def foo():
            @!bar!(arg=map)
            def $boo$():
                pass
    ''')

def test_with_statement_local_scope():
    assert_names('''
        def foo():
            with open('file') as f:
                map(f)
                bar = 1

            map(!f!)
            map(bar)
    ''')

def test_multiple_with_statement_local_scope():
    assert_names('''
        def foo():
            with open('file') as f, open('boo') as boo:
                map(f)
                map(boo)
                bar = 1

            map(!f!)
            map(!boo!)
            map(bar)
    ''')

def test_with_statement_tuple_target_local_scope():
    assert_names('''
        def foo():
            with open('file') as (f, boo):
                map(f)
                map(boo)
                bar = 1

            map(!f!)
            map(!boo!)
            map(bar)
    ''')

def test_except_statement_local_scope():
    assert_names('''
        def foo():
            try:
                pass
            except Exception as e:
                bar = 1
                map(e)

            map(!e!)
            map(bar)
    ''')
