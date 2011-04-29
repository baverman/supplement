import sys, os.path
import types

from supplement.module import Module
from supplement.project import Project
from supplement.fixer import fix
from supplement.scope import Scope


class TestModule(Module):
    def get_source(self):
        return self.source


def create_module(project, name, source):
    source = cleantabs(source)
    code = compile(source, '<string>', 'exec')
    module = types.ModuleType(name)
    sys.modules[name] = module

    exec code in module.__dict__

    m = TestModule(project, name)
    m.source = source
    module.__file__ = name + '.py'

    project.module_provider.cache[name] = m

    package_name, _, module_name = name.rpartition('.')
    if package_name:
        project.package_resolver.cache[os.path.abspath(package_name)] = package_name
        sys.modules[package_name] = types.ModuleType(package_name)
        setattr(sys.modules[package_name], module_name, module)

    return m

def create_scope(project, code, filename=None):
    ast, _ = fix(cleantabs(code))
    scope = Scope(ast, '', None, 'module')
    scope.project = project
    scope.filename = filename
    return scope

def set_project_root(project, root):
    project.root = root
    project.paths = [os.path.abspath(root)] + sys.path

def pytest_funcarg__project(request):
    for crap_module in ('toimport',):
        if crap_module in sys.modules:
            del sys.modules[crap_module]

    p = Project('.')
    p.create_module = create_module.__get__(p, Project)
    p.create_scope = create_scope.__get__(p, Project)
    p.set_root = set_project_root.__get__(p, Project)
    return p

def cleantabs(text):
    lines = text.splitlines()
    if not lines[0].strip():
        lines = lines[1:]

    toremove = 999
    for l in lines:
        stripped = l.lstrip()
        if stripped:
            toremove = min(toremove, len(l) - len(stripped))

    if toremove < 999:
        return '\n'.join(l[toremove:] for l in lines)
    else:
        return '\n'.join(lines)

def get_source_and_pos(source):
    source = cleantabs(source)
    pos = source.find('|')
    if pos < 0:
        pos = len(source)

    return source, pos