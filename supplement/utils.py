from weakref import ref

class WeakedList(object):
    def __init__(self):
        self.list = []

    def __iter__(self):
        for r in self.list:
            yield r()

    def __len__(self):
        return len(self.list)

    def append(self, value):
        self.list.append(ref(value, self.on_delete))

    def on_delete(self, ref):
        self.list.remove(ref)
