import sys
import os.path
import textwrap
from cPickle import load
import ast

def generate_method(method, modules):
    result = '    def %(name)s(' % method
    params = ['self']
    for pname, default in method['params']:
        if default:
            params.append('%s=%s' % (pname, default))
        else:
            params.append(pname)

    result += ', '.join(params) + '):\n'

    if method['doc']:
        initial_indent = ''
        result += "        '''"
        for d in method['doc']:
            for l in d.splitlines(True):
                result += initial_indent + l
                initial_indent = '        '

            result += '\n\n'

        result += "        '''\n"

    if method['returns']:
        module, _, name = method['returns'].rpartition('.')
        result += '        import %s\n' % module
        result += '        return %s()\n' % method['returns']
    else:
        result += '        pass\n'

    return result

def generate_class(cls, modules):
    result = 'class %(name)s(__orig__.%(name)s):\n' % cls
    result += "    '''" + textwrap.fill(cls['doc'], 80, subsequent_indent='    ') + "\n    '''\n"

    for mname, m in sorted(cls['methods'].iteritems()):
        result += generate_method(m, modules)
        result += '\n'

    return result

def generate_module(module, modules):
    result = ''
    for _, obj in sorted(module.iteritems()):
        if obj['type'] == 'class':
            result += generate_class(obj, modules)
            result += '\n'

    return result

def generate(root, modules):
    for mname, module in modules.iteritems():
        print mname
        fname = os.path.join(root, mname + '.py')
        result = generate_module(module, modules).encode('utf-8')
        with open(fname, 'w') as f:
            f.write(result)
            ast.parse(result)

if __name__ == '__main__':
    modules = load(open(sys.argv[1]))
    root = sys.argv[2]

    generate(root, modules)