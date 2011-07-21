import sys
import os.path
import glob
from lxml import etree
from cPickle import dump
import textwrap

def get_docs(root):
    if os.path.isfile(root):
        yield root
        return

    for fname in glob.glob(os.path.join(root, '*.xml')):
        if not fname.endswith('pygtk2-ref.xml'):
            yield fname

def get_obj(modules, *names, **kwargs):
    result = modules
    for n in names[:-1]:
        result = modules.setdefault(n, {})

    try:
        result = result[names[-1]]
    except KeyError:
        result = result.setdefault(names[-1], {})
        result.update(kwargs)

    return result

def parse_method(refsect, cname, methods):
    synopsis = refsect.xpath(
        './programlisting/methodsynopsis | ./programlisting/constructorsynopsis')

    if not len(synopsis):
        return

    synopsis = synopsis[0]
    _, _, mname = ''.join(synopsis.find('methodname').itertext()).rpartition('.')
    if mname == cname:
        mname = '__init__'

    method = methods[mname] = {'name':mname}
    params = method['params'] = []

    for p in synopsis.xpath('./methodparam'):
        pname = p.find('parameter')
        if pname is None:
            continue

        pname = pname.text
        if not pname:
            continue

        if pname == '...':
            pname = '**kwargs'
        elif pname == 'def':
            pname = 'default'

        init = p.find('initializer')
        if init is not None:
            init = ''.join(init.itertext()).strip()

        params.append((pname, init))

    returns = refsect.xpath('.//varlistentry[term/emphasis/text()="Returns"]//classname')
    if len(returns) and mname != '__init__':
        method['returns'] = returns[0].text
    else:
        method['returns'] = None

    doc = method['doc'] = []
    for d in refsect.xpath('./para | ./programlisting'):
        if d.find('methodsynopsis') is None and d.find('constructorsynopsis') is None:
            text = textwrap.dedent(''.join(d.itertext()))
            if d.tag == 'programlisting':
                text = '\n'.join('    ' + r for r in text.splitlines())
            else:
                text = textwrap.fill(' '.join(r.strip() for r in text.splitlines()).strip(),
                    80, expand_tabs=False)

            doc.append(text)

def parse(modules, root, fname):
    for refentry in root.xpath('/refentry'):
        if not refentry.attrib['id'].startswith('class-'):
            continue

        mname, _, cname = refentry.xpath('./refnamediv/refname')[0].text.rpartition('.')
        cls = get_obj(modules, mname, cname, type='class', name=cname)

        text = ''.join(refentry.xpath('./refnamediv/refpurpose')[0].itertext())
        cls['doc'] = textwrap.fill(' '.join(r.strip() for r in text.splitlines()).strip(),
                            80, expand_tabs=False)

        methods = cls['methods'] = {}
        for refsect in refentry.xpath(
                './refsect1[title/text()="Methods"]/refsect2 | ./refsect1[title/text()="Constructor"]'):
            parse_method(refsect, cname, methods)


        attrs = cls['attrs'] = []
        for row in refentry.xpath('./refsect1[title/text()="Attributes"]//row'):
            entries = row.xpath('./entry')
            name = entries[0].text.strip().strip('"')

            atype = entries[2].xpath('.//classname')
            if len(atype):
                atype = atype[0].text.strip()
            else:
                atype = None

            attrs.append((name, atype))


if __name__ == '__main__':
    modules = {}

    parser = etree.XMLParser(load_dtd=True)

    for fname in get_docs(sys.argv[1]):
        print fname
        with open(fname) as f:
            root = etree.parse(f, parser)
            parse(modules, root, fname)

    with open(sys.argv[2], 'wb') as f:
        dump(modules, f, 2)