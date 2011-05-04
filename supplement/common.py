class Object(object):
    def get_location(self):
        return None, None

    def get_names(self):
        return set()

    def __contains__(self, name):
        return name in self.get_names()

    def __getitem__(self, name):
        raise KeyError(name)

    def op_call(self, *args):
        return UnknownObject()

    def op_getitem(self, idx):
        return UnknownObject()


class GetObjectDelegate(object):
    def get_names(self):
        return self.get_object().get_names()

    def __getitem__(self, name):
        return self.get_object()[name]

    def __contains__(self, name):
        return name in self.get_object()

    def op_call(self, args):
        return self.get_object().op_call(args)

    def op_getitem(self, idx):
        return self.get_object().op_getitem(idx)

    def get_location(self):
        return self.get_object().get_location()


class UnknownObject(Object): pass
