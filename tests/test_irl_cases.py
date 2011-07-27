from .helpers import pytest_funcarg__project, do_assist, get_source_and_pos

def test_eval_of_os_path_abspath(project):
    result = do_assist(project, '''
        from os.path import abspath
        abspath('').''')

    assert 'lower' in result

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
