from supplement.project import Project

from .helpers import create_module

def test_function_node_location():
    p = Project('./')
    m = create_module(p, 'test', '''
def test():
    pass

''')

    line, filename = m['test'].get_location()
    assert line == 2
    assert filename == 'test.py'

def test_assign_node_location():
    p = Project('./')
    m = create_module(p, 'test', '''

(test1,
    test2) = 5, 10

''')

    line, filename = m['test1'].get_location()
    assert line == 3
    assert filename == 'test.py'

    line, filename = m['test2'].get_location()
    assert line == 4
    assert filename == 'test.py'

def test_class_location():
    p = Project('./')
    m = create_module(p, 'test', '''

class test:
    pass
''')

    line, filename = m['test'].get_location()
    assert line == 3
    assert filename == 'test.py'

def test_method_location():
    p = Project('./')
    m = create_module(p, 'test', '''

class test:
    def test(self):
        pass
''')

    line, filename = m['test']['test'].get_location()
    assert line == 4
    assert filename == 'test.py'

def test_imported_location():
    p = Project('./')

    create_module(p, 'toimport', '''
test = 'test'
''')

    m = create_module(p, 'test', '''

from toimport import test
''')

    line, filename = m['test'].get_location()
    assert line == 2
    assert filename == 'toimport.py'
