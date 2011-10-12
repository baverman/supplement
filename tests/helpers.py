import sys, os.path
import types

from supplement.module import Module
from supplement.project import Project
from supplement.fixer import fix
from supplement.scope import Scope
from supplement.assistant import assist, get_docstring


class TestModule(Module):
    def get_source(self):
        return self.source


def create_module(project, name, source):
    source = cleantabs(source)
    code = compile(source, '<string>', 'exec')
    module = types.ModuleType(name)
    sys.modules[name] = module

    exec(code, module.__dict__)

    m = TestModule(project, name)
    m._module = module
    m.source = source
    module.__file__ = name + '.py'

    project.module_providers['default'].cache[name] = m

    package_name, _, module_name = name.rpartition('.')
    package_path = '/'.join(package_name.split('.'))

    if package_name:
        module.__file__ = "%s/%s.py" % (package_path, module_name)
        project.package_resolver.cache[os.path.abspath(package_name)] = package_name
        p = TestModule(project, package_name)
        p._module = sys.modules[package_name] = types.ModuleType(package_name)
        setattr(sys.modules[package_name], module_name, module)
        p._module.__file__ = "%s/__init__.py" % package_path
        p.source = None
        project.module_providers['default'].cache[package_name] = p

    return m

def create_scope(project, code, filename=None):
    source = cleantabs(code)
    lines = []
    pos = 0
    while True:
        pos = source.find('|', pos)
        if pos >= 0:
            lines.append(source.count('\n', 0, pos) + 1)
            pos += 1
        else:
            break

    ast, _ = fix(source.replace('|', ''))
    scope = Scope(ast, '', None, 'module')
    scope.project = project
    scope.filename = filename

    if lines:
        result = []
        for line in lines:
            result.extend([scope.get_scope_at(source, line), line])
        return result
    else:
        return scope

def set_project_root(project, root):
    project.root = root
    project._refresh_paths()

def pytest_funcarg__project(request):
    for crap_module in ('toimport', 'package'):
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

    return source.replace('|', ''), pos

def do_assist(project, source, filename=None):
    filename = filename or 'test.py'
    source, pos = get_source_and_pos(source)
    return assist(project, source, pos, filename)[1]

def do_docstring(project, source, filename=None):
    filename = filename or 'test.py'
    source, pos = get_source_and_pos(source)
    return get_docstring(project, source, pos, filename)
