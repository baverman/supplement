import pytest

from supplement.remote import Environment

from .helpers import cleantabs

@pytest.mark.slow
def test_project_config():
    env = Environment()
    env.configure_project('.', {'libs':['/usr/lib/python2.7/site-packages/exo-0.6']})

    source = cleantabs('''
        from exo import IconView
        IconView().props.''')

    result = env.assist('.', source, len(source), 'test.py')
    assert 'layout_mode' in result

@pytest.mark.slow
def test_simple_assist():
    env = Environment()

    source = cleantabs('''
        from os import popen
        p''')

    result = env.assist('.', source, len(source), 'test.py')
    assert result == ['popen', 'pow', 'print', 'property']