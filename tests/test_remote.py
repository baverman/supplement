import pytest

from supplement.remote import Environment

from .helpers import cleantabs

@pytest.mark.slow
def test_project_token():
    env = Environment()
    env.run()

    p1 = env.get_project_token('.')
    p2 = env.get_project_token('.')

    assert p1 != p2

@pytest.mark.xfail
def test_project_config():
    env = Environment()
    env.run()
    p = env.get_project_token('.', config={'libs':['/usr/lib/python2.7/site-packages/exo-0.6']})

    source = cleantabs('''
        from exo import IconView
        IconView().props.''')

    result = env.assist(p, source, len(source), 'test.py')
    assert 'layout_mode' in result

@pytest.mark.slow
def test_simple_assist():
    env = Environment()
    env.run()
    p = env.get_project_token('.')

    source = cleantabs('''
        from os import popen
        p''')

    result = env.assist(p, source, len(source), 'test.py')
    assert result == ['popen', 'pow', 'print', 'property']