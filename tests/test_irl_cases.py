from .helpers import pytest_funcarg__project, do_assist, get_source_and_pos

def test_eval_of_os_path_abspath(project):
    result = do_assist(project, '''
        from os.path import abspath
        abspath('').''')

    assert 'lower' in result

def est_assist_for_gtk_object_attributes(project):
    result = do_assist(project, '''
        import gtk
        gtk.Window().''')

    assert 'activate' in result

def est_assist_for_gtk_class_properties(project):
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

def test_unclosed_bracket_indented_assist(project):
    result = do_assist(project, '''
        import sys

        if True:
            len(sy|
    ''')

    assert 'sys' in result

def est_pyqt_signals(project):
    result = do_assist(project, '''
        from PyQt4 import QtGui
        app = QtGui.QApplication([])
        window = QtGui.QWidget()
        button  = QtGui.QPushButton(window)
        button.clicked.|
    ''')

    assert result == ['connect', 'disconnect', 'emit']

def test_recursive_name_defenition(project):
    project.register_hook('supplement.hooks.override')
    result = do_assist(project, '''
        import os, re
        def fnc(file):
            code = open(file).read()
            pyrex = re.search("(from)(.+)", code)
            code = code.replace(pyrex.group(1), "b")
            code.|
    ''')

#def test_snaked(project):
#    project.set_root('/home/bobrov/work/bonent')
#    fname = project.root + '/bparser/smscenter.py'
#    source, pos = open(fname).read(), 524
#    result = do_assist(project, source, fname)
#
#    print result
#    assert False