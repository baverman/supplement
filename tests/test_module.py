import sys

from supplement.project import Project

def pytest_generate_tests(metafunc):
    if 'module_name' in metafunc.funcargnames:
        for name in ('os', 'sys', 'subprocess', 'collections', 'datetime', 'os.path', 'glob',
                'multiprocessing'):
            metafunc.addcall(funcargs=dict(module_name=name))

def test_stock_module(module_name):
    p = Project('./')
    m = p.get_module(module_name)

    absent_items = []
    module = sys.modules[module_name]

    for name in dir(module):
        if name not in m:
            absent_items.append((name, getattr(module, name)))

    assert absent_items == []
