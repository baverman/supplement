import pytest
import os

def pytest_runtest_setup(item):
    if 'slow' in item.keywords and 'SKIP_SLOW_TESTS' in os.environ:
        pytest.skip("ommit SKIP_SLOW_TESTS envvar to run")