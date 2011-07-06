from supplement.assistant import assist

from .helpers import pytest_funcarg__project, do_assist

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

def test_logging_getLogger(project):
    result = do_assist(project, '''
        import logging
        logging.getLogger(__name__).|
    ''')

    assert 'exception' in result
