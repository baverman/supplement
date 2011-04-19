from supplement.assistant import assist

from .helpers import cleantabs, pytest_funcarg__project

def do_assist(project, source, filename=None, pos=None):
    filename = filename or 'test.py'

    if not pos:
        source = cleantabs(source)

    pos = pos or len(source)

    return assist(project, source, pos, filename)


def test_assist_for_watcher_raises_KeyError(project):
    result = do_assist(project, '''
        from supplement import watcher
        watcher.''')

    assert 'run_loop' in result
    assert 'monitor' in result
