import symtable

def traverse_tree(root, parents):
    yield root, parents

    for n in root.get_children():
        for r in traverse_tree(n, parents + (root,)):
            yield r

def get_block_end(table, lines):
    start = table.get_lineno() - 1
    start_line = lines[start]

    while not any(map(start_line.lstrip().startswith, ('def ', 'class '))):
        start += 1
        try:
            start_line = lines[start]
        except IndexError:
            return start

    indent = len(start_line) - len(start_line.lstrip())

    last_line = start + 1
    for i, l in enumerate(lines[start+1:], start+2):
        stripped = l.lstrip()

        if stripped:
            if len(l) - len(stripped) <= indent:
                break

            last_line = i

    return last_line

def get_scope_at(source, lineno):
    table = symtable.symtable(source, '<string>', 'exec')

    prev = None
    for node, parents in traverse_tree(table, ()):
        if node.get_lineno() == lineno:
            break

        if node.get_lineno() > lineno:
            node, parents = prev
            break

        prev = node, parents

    lines = source.splitlines()
    while parents:
        end = get_block_end(node, lines)
        if lineno <= end:
            break

        node, parents = parents[-1], parents[:-1]

    n = None
    for p in parents + (node,):
        n = Scope(p, n)

    return n


class Scope(object):
    def __init__(self, table, parent):
        self.table = table
        self.parent = parent

    def get_name(self):
        return self.table.get_name()

    def get_fullname(self):
        names = [self.get_name()]
        node = self
        while node.parent:
            node = node.parent
            names.append(node.get_name())

        return '.'.join(reversed(names[:-1]))