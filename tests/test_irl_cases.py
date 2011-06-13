from supplement.assistant import assist

from .helpers import pytest_funcarg__project, get_source_and_pos

def do_assist(project, source, filename=None):
    filename = filename or 'test.py'
    source, pos = get_source_and_pos(source)
    return assist(project, source, pos, filename)

def test_assist_for_watcher_raises_KeyError(project):
    result = do_assist(project, '''
        from supplement import watcher
        watcher.''')

    assert 'monitor' in result

def test_eval_of_os_path_abspath(project):
    result = do_assist(project, '''
        from os.path import abspath
        abspath('').''')

    assert 'lower' in result

def test_assist_for_gtk_object_attributes(project):
    result = do_assist(project, '''
        import gtk
        gtk.Window().''')

    assert 'activate' in result

def test_assist_for_gtk_class_properties(project):
    result = do_assist(project, '''
        import gtk
        gtk.Window.props.''')

    assert 'has_focus' in result