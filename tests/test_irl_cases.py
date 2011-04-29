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

    assert 'run_loop' in result
    assert 'monitor' in result

def test_eval_of_os_path_absname(project):
    result = do_assist(project, '''
        from os.path import abspath
        abspath('').''')

    assert 'lower' in result