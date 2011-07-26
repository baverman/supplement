import ast
from .utils import WeakedList

class CallExtractor(ast.NodeVisitor):
    def process(self, node):
        self.calls = []
        self.generic_visit(node)
        return self.calls

    def visit_FunctionDef(self, node):
        pass

    def visit_ClassDef(self, node):
        pass

    def visit_Call(self, node):
        self.calls.append((node.lineno, node.func, node.args))
        self.generic_visit(node)


class CallInfo(object):
    def __init__(self, scope, line, args):
        self.scope = scope
        self.line = line
        self.args = args

    def get_args(self):
        pass

class CallDB(object):
    def __init__(self):
        self.calls = {}
        self.files = {}

    def update_calls(self, fname, calls):
        try:
            fcalls = self.files[fname]
        except KeyError:
            fcalls = self.files[fname] = []

        for fullname, ci in calls:
            fcalls.append(ci)
            self.calls.setdefault(fullname, WeakedList()).append(ci)

    def collect_calls(self, scope):
        from .scope import traverse_tree

        try:
            del self.files[scope.filename]
        except KeyError:
            pass

        call_extractor = CallExtractor()
        for s in traverse_tree(scope):
            calls = []
            for line, func, args in call_extractor.process(s.node):
                func = scope.eval(func, False)
                if func:
                    fscope = func.get_scope()
                    if fscope:
                        ci = CallInfo(scope, line, args)
                        calls.append((fscope.fullname, ci))

            self.update_calls(scope.filename, calls)