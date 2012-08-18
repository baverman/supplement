import pytest

from supplement.remote import Environment

from .helpers import cleantabs

def get_env():
    return Environment(env={'PYTHONPATH':'.'})

@pytest.mark.xfail
def test_project_config():
    env = get_env()
    env.configure_project('.', {'libs':['/usr/lib/python2.7/site-packages/exo-0.6']})

    source = cleantabs('''
        from exo import IconView
        IconView().props.''')

    match, result = env.assist('.', source, len(source), 'test.py')
    assert 'layout_mode' in result

@pytest.mark.slow
def test_simple_assist():
    env = get_env()

    source = cleantabs('''
        from os import popen
        p''')

    match, result = env.assist('.', source, len(source), 'test.py')
    assert result == ['popen', 'pow', 'print', 'property']

@pytest.mark.slow
def test_prepare():
    env = get_env()
    env.prepare()

    source = cleantabs('''
        from os import popen
        p''')

    match, result = env.assist('.', source, len(source), 'test.py')
    assert result == ['popen', 'pow', 'print', 'property']