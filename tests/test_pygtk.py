from supplement.scope import get_scope_at
from supplement.evaluator import infer

from .helpers import pytest_funcarg__project, get_source_and_pos, do_assist

def test_class_must_contain_objects_defined_in_glade_file(project):
    project.register_hook('supplement.hooks.pygtk')
    source, _ = get_source_and_pos('''
        class Window(object):
            """glade-file: tests/pygtktest/sample.glade"""

            def foo(self):
                pass
    ''')

    scope = get_scope_at(project, source, 5, 'test.py')

    result = infer('self', scope, 5)
    assert 'window1' in result
    assert 'vbox1' in result

    result = infer('self.window1', scope, 5)
    assert 'set_title' in result

    result = infer('self.vbox1', scope, 5)
    assert 'pack_start' in result

def est_provider_must_resolve_params_of_handlers_defined_in_glade_file(project):
    result = get_proposals(project, 'pass\n\n'
        '   def on_window1_delete_event(self, wnd):\n'
        '       wnd.')
    assert 'set_title' in result

def test_provider_must_allow_to_implement_glade_handlers(project):
    project.register_hook('supplement.hooks.pygtk')
    result = do_assist(project, '''
        class Window(object):
            """glade-file: tests/pygtktest/sample.glade"""

            def on|
    ''')

    assert 'on_window1_delete_event' in result

def test_docbook_hints(project):
    project.register_hook('supplement.hooks.pygtk')

    result = do_assist(project, '''
        import gtk
        gtk.HBox().get_window().set_t|
    ''')
    assert 'set_title' in result

    result = do_assist(project, '''
        import gtk
        gtk.HBox().get_window().set_title(tit|
    ''')
    assert 'title=' in result


    scope = project.create_scope('import gtk')
    print infer('gtk.HBox().window', scope, 5)

    result = do_assist(project, '''
        import gtk
        gtk.HBox().window.set_title(tit|
    ''')
    assert 'title=' in result

def test_docbook_modules_must_behave_as_usual(project):
    project.register_hook('supplement.hooks.pygtk')

    result = do_assist(project, '''
        from gtk.key|
    ''')
    assert 'keysyms' in result

    result = do_assist(project, '''
        from gtk.keysyms import Dow|
    ''')
    assert 'Down' in result
