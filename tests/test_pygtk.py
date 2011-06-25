from supplement.assistant import assist
from supplement.scope import get_scope_at
from supplement.evaluator import infer

from .helpers import pytest_funcarg__project, get_source_and_pos

def do_assist(project, source, filename=None):
    filename = filename or 'test.py'
    source, pos = get_source_and_pos(source)
    return assist(project, source, pos, filename)

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

def est_provider_must_allow_to_implement_glade_handlers(project):
    result = get_proposals(project, 'pass\n\n'
        '   def on')
    assert 'on_window1_delete_event' in result
