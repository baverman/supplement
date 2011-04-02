class Names:
    class ModuleName(object):
        def __init__(self, name):
            self.name = name

        def get_names(self):
            return self.project.get_module(self.name, self.filename).get_names()


def create_name(node, owner):
    obj = getattr(Names, node[0])(*node[1:])
    obj.project = owner.project
    obj.filename = owner.filename

    return obj