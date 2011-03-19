import sys
import types

from supplement.module import Module

def create_module(project, name, source):
    code = compile(source, '<string>', 'exec')
    module = types.ModuleType(name)
    sys.modules[name] = module

    exec code in module.__dict__

    m = TestModule(project, module)
    m.source = source
    module.__file__ = name + '.py'

    project.module_provider.cache[name] = m

    return m

class TestModule(Module):
    def get_source(self):
        return self.source