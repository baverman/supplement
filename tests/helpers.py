import sys, os.path
import types

from supplement.module import Module
from supplement.project import Project

def create_module(project, name, source):
    source = cleantabs(source)
    code = compile(source, '<string>', 'exec')
    module = types.ModuleType(name)
    sys.modules[name] = module

    exec code in module.__dict__

    m = TestModule(project, module)
    m.source = source
    module.__file__ = name + '.py'

    project.module_provider.cache[name] = m

    package_name, _, module_name = name.rpartition('.')
    if package_name:
        project.package_resolver.cache[os.path.abspath(package_name)] = package_name
        sys.modules[package_name] = types.ModuleType(package_name)

    return m

class TestModule(Module):
    def get_source(self):
        return self.source


def pytest_funcarg__project(request):
    p = Project('.')
    p.create_module = types.MethodType(create_module, p, Project)
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
