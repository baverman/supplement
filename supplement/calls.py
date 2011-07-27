import ast
from .utils import WeakedList
from .common import UnknownObject
from .names import ClassName
from .objects import ClassObject

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
        try:
            return self._evaluated_args
        except AttributeError:
            pass

        result = []
        for arg in self.args:
            try:
                v = self.scope.eval(arg, False)
            except:
                v = None
            else:
                if isinstance(v, UnknownObject):
                    v = None

            result.append(v)

        self._evaluated_args = result
        return result


class CallDB(object):
    def __init__(self, project):
        self.calls = {}
        self.files = {}
        self.project = project

    def update_calls(self, fname, calls):
        try:
            fcalls = self.files[fname]
        except KeyError:
            fcalls = self.files[fname] = []

        for fname, fullname, ci in calls:
            fcalls.append(ci)
            self.calls.setdefault((fname, fullname), WeakedList()).append(ci)

    def get_args_for_scope(self, scope):
        key = scope.filename, scope.fullname
        try:
            clist = self.calls[key]
        except KeyError:
            return None

        args = [None] * len(scope.args)
        for ci in list(clist):
            for i, v in enumerate(ci.get_args()):
                if v and args[i] is None:
                    args[i] = v

            if not any(r is None for r in args):
                return args

        for i, v in enumerate(args):
            if v is None:
                args[i] = UnknownObject()

        return args

    def collect_calls(self, scope, skip_if_exists=False):
        if skip_if_exists and scope.filename in self.files:
            return

        from .scope import traverse_tree

        try:
            del self.files[scope.filename]
        except KeyError:
            pass

        call_extractor = CallExtractor()
        for s in traverse_tree(scope):
            calls = []
            for line, func, args in call_extractor.process(s.node):
                if not args: continue

                try:
                    func = s.eval(func, False)
                except:
                    continue

                if isinstance(func, (ClassName, ClassObject)):
                    func = func['__init__']

                if func:
                    fscope = func.get_scope()
                    if fscope:
                        ci = CallInfo(scope, line, args)
                        calls.append((fscope.filename, fscope.fullname, ci))

            self.update_calls(scope.filename, calls)

    def index_project(self):
        for fname, source in self.get_project_sources():
            pass