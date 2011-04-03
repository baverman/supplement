from .helpers import pytest_funcarg__project

def test_instance_attributes(project):
    m = project.create_module('test', '''
        test = 'string'
    ''')

    obj = m['test']

    assert 'lower' in obj
