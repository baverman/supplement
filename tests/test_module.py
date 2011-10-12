import sys

from supplement.project import Project

from .helpers import pytest_funcarg__project

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

def test_module_loader_must_load_project_modules(project, tmpdir):
    project.set_root(str(tmpdir))
    import subprocess

    tmpdir.join('subprocess.py').write('name = []')
    m = project.get_module('subprocess')

    assert m.module is not subprocess
    assert 'append' in m['name']

def test_module_loader_must_do_relative_load_without_sys_path(project, tmpdir):
    pkgdir = tmpdir.join('package')
    pkgdir.mkdir()
    pkgdir.join('__init__.py').write('')
    pkgdir.join('toimport.py').write('test = 1')

    project.set_root(str(pkgdir))

    m = project.get_module('.toimport', str(pkgdir) + '/test.py')
    assert 'test' in m