from os.path import join, exists

def get_module_resource(project, name):
    parts = join(*name.split('.'))
    names = join(parts, '__init__.py'), parts + '.so', parts + '.py'

    for p in project.paths:
        for n in names:
            filename = join(p, n)
            if exists(filename):
                return FileResource(filename)

    return None


class FileResource(object):
    def __init__(self, path):
        self.path = path

    @property
    def source(self):
        return open(self.path).read()


class StringResource(object):
    def __init__(self, path, source):
        self.path = path
        self.source = source


class AttributeGetter(object):
    def __getitem__(self, key):
        return self.get_attributes()[key]

    def __contains__(self, key):
        return key in self.get_attributes()