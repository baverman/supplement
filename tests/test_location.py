from .helpers import pytest_funcarg__project

def test_function_node_location(project):
    m = project.create_module('test', '''
def test():
    pass

''')

    line, filename = m['test'].get_location()
    assert line == 2
    assert filename == 'test.py'

def test_assign_node_location(project):
    m = project.create_module('test', '''

(test1,
    test2) = 5, 10

''')

    line, filename = m['test1'].get_location()
    assert line == 3
    assert filename == 'test.py'

    line, filename = m['test2'].get_location()
    assert line == 4
    assert filename == 'test.py'

def test_class_location(project):
    m = project.create_module('test', '''

class test:
    pass
''')

    line, filename = m['test'].get_location()
    assert line == 3
    assert filename == 'test.py'

def test_method_location(project):
    m = project.create_module('test', '''

class test:
    def test(self):
        pass
''')

    line, filename = m['test']['test'].get_location()
    assert line == 4
    assert filename == 'test.py'

def test_imported_location(project):
    project.create_module('toimport', '''
test = 'test'
''')

    m = project.create_module('test', '''

from toimport import test
''')

    line, filename = m['test'].get_location()
    assert line == 2
    assert filename == 'toimport.py'

def test_super_method_location(project):
    project.create_module('toimport', '''
class Foo(object):
    def foo(self):
        pass
''')

    m = project.create_module('test', '''
from toimport import Foo

class Bar(Foo):
    pass
''')

    line, filename = m['Bar']['foo'].get_location()
    assert line == 3
    assert filename == 'toimport.py'