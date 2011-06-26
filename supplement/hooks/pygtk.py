import re
import xml.sax.handler
import gobject

from supplement.names import ClassName
from supplement.objects import FakeInstanceObject
from supplement.common import ClassProxy, Object
from supplement.watcher import monitor

pydoc_glade_file_matcher = re.compile('(?m)^.*glade-file\s*:(.*)$')

def init(project):
    project.add_docstring_processor(docstring_processor)
    project.add_module_provider('glade', GladeModuleProvider())

def docstring_processor(docstring, obj):
    if not isinstance(obj, ClassName):
        return

    match = pydoc_glade_file_matcher.match(docstring)
    if not match:
        return

    filename = 'glade:'+obj.project.get_filename(match.group(1).strip(), obj.filename)
    proxy = ClassProxy(obj.project, filename, 'GladeClass')

    def glade_base_injector(func):
        def inner():
            bases = func()
            if proxy not in bases:
                bases.insert(0, proxy)

            return bases
        return inner

    obj.get_bases = glade_base_injector(obj.get_bases)
    return obj


class GladeModuleProvider(object):
    def __init__(self):
        self.cache = {}

    def on_file_change(self, filename, name):
        self.cache[name].invalidate()

    def get(self, project, name):
        try:
            return self.cache[name]
        except KeyError:
            pass

        m = self.cache[name] = GladeModule(project, name)
        monitor(name, self.on_file_change, name)
        return m


class GladeModule(Object):
    def __init__(self, project, filename):
        self._names = {'GladeClass': GladeClass(project, filename)}

    def get_names(self):
        return self._names

    def __getitem__(self, name):
        return self._names[name]


class GladeClass(Object):
    def __init__(self, project, filename):
        self.filename = filename
        self.project = project
        self._attrs = {}

    def get_gtk_object(self, name):
        name = name.replace('Gtk', '')
        return self.project.get_module('gtk')[name]

    def get_names(self):
        try:
            return self._names
        except AttributeError:
            pass

        handler = GladeHandler()
        xml.sax.parseString(open(self.filename).read(), handler)

        self._names = {}
        for name, cls, line in handler.objects:
            self._names[name] = cls, line

        for name, (cls, signal, line) in handler.signals.iteritems():
            self._names[name] = cls, signal, line

        return self._names

    def __getitem__(self, name):
        try:
            return self._attrs[name]
        except KeyError:
            pass

        name = self.get_names()[name]
        obj = self._attrs[name] = FakeInstanceObject(self.get_gtk_object(name[0]))
        return obj


class GladeName(object):
    def __init__(self, pyobject, module, line):
        self.pyobject = pyobject
        self.line = line
        self.module = module

    def get_object(self):
        return self.pyobject

    def get_definition_location(self):
        return self.module, self.line


class PyGtkHintProvider(object):
    def __init__(self, project):
        super(PyGtkHintProvider, self).__init__(project)
        self.gtk_aware_classes = {}
        self.cache = {}
        self.func_cache = {}
        self.handlers = {}
        self.processed_files = {}

    def get_pygtk_class_name(self, gtk_class_name):
        return gtk_class_name.replace('Gtk', 'gtk.', 1) + '()'

    def process_glade(self, scope_path, glade_resource, force=False):
        glade_file = glade_resource.real_path
        processed = self.processed_files.getw(glade_file, False)
        if processed and not force:
            return

        self.cache[scope_path] = attrs
        self.processed_files[glade_file] = True

    def get_glade_file_for_class(self, scope_path, pyclass):
        project = pyclass.get_module().resource.project
        try:
            path = self.gtk_aware_classes[scope_path]
            return project.get_resource(path)
        except KeyError:
            pass

        doc = pyclass.get_doc()
        if doc:
            match = pydoc_glade_file_matcher.search(doc)
            if match:
                filename = match.group(1).strip()
                if filename.startswith('/'):
                    return project.get_resource(filename[1:])
                else:
                    return pyclass.get_module().resource.parent.get_child(filename)

        return None

    def get_attributes(self, scope_path, pyclass, orig_attrs):
        attrs = {}
        glade_file = self.get_glade_file_for_class(scope_path, pyclass)
        if glade_file:
            self.process_glade(scope_path, glade_file)
            for k, v in self.cache[scope_path].iteritems():
                if k not in orig_attrs:
                    attrs[k] = v

        return attrs

    def add_class(self, scope, glade_file):
        self.gtk_aware_classes[scope] = glade_file

    def get_function_params(self, scope_path, pyfunc):
        """:type pyfunc: rope.base.pyobjectsdef.PyFunction"""

        pyclass = pyfunc.parent
        scope_path = get_attribute_scope_path(pyclass)
        glade_file = self.get_glade_file_for_class(scope_path, pyclass)

        if glade_file:
            self.process_glade(scope_path, glade_file)
            return self.get_params_for_handler(scope_path, pyfunc)
        else:
            return {}

    def get_params_for_handler(self, class_scope, pyfunc):
        """:type pyfunc: rope.base.pyobjectsdef.PyFunction"""
        try:
            cls, signal = self.handlers[class_scope][pyfunc.get_name()]
        except KeyError:
            return {}

        attrs = {}

        idx = 0
        names = pyfunc.get_param_names(False)
        if pyfunc.get_kind() in ('method', 'classmethod'):
            names = names[1:]
            idx += 1

        if names:
            attrs[idx] = self.get_type(self.get_pygtk_class_name(cls)).get_object()
            names = names[1:]
            idx += 1

        if names:
            for t in gobject.signal_query(signal, str(cls))[-1]:
                try:
                    tname = self.get_type(self.get_pygtk_class_name(t.name))
                    if tname:
                        attrs[idx] = tname.get_object()
                except ModuleNotFoundError:
                    pass

                idx += 1

        return attrs


class GladeHandler(xml.sax.handler.ContentHandler):
    def __init__(self):
        self.objects = []
        self.signals = {}
        self.current_object_class = None

    def startElement(self, name, attrs):
        if name == 'object':
            self.objects.append((attrs['id'], attrs['class'], self._locator.getLineNumber()))
            self.current_object_class = attrs['class']
        elif name == 'signal':
            if self.current_object_class:
                self.signals[attrs['handler']] = (self.current_object_class, attrs['name'],
                    self._locator.getLineNumber())

    def endElement(self, name):
        if name == 'object':
            self.current_object_class = None