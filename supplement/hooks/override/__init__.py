from os.path import join, exists, dirname
import logging

from supplement.module import Module

def init(project):
    project.add_override_processor(override_fs)
    project_overrides = project.config.get('overrides', [])
    project_overrides.insert(0, join(dirname(__file__), 'modules'))
    project.config['overrides'] = project_overrides

def override_fs(project, module):
    name = module.name
    for path in project.config['overrides']:
        fname = join(path, name + '.py')
        if exists(fname):
            module = OverrideModule(project, module, fname)

    return module

class OverrideModule(Module):
    def __init__(self, project, module, filename):
        Module.__init__(self, project, module.name)
        self._filename = filename
        self.overrided_module = module

    @property
    def module(self):
        try:
            return self._module
        except AttributeError:
            pass

        import imp
        logging.getLogger(__name__).info('Try to override %s from %s', self.name, self._filename)
        self._module = imp.new_module(self.name)
        self._module.__orig__ = self.overrided_module.module
        self._module.__file__ = self._filename
        exec(compile(open(self._filename).read(), self._filename, 'exec'), self._module.__dict__)

        return self._module

    @property
    def filename(self):
        return self._filename

    def get_names(self):
        return Module.get_names(self).union(self.overrided_module.get_names())

    def __getitem__(self, name):
        try:
            return Module.__getitem__(self, name)
        except (KeyError, AttributeError):
            return self.overrided_module[name]
