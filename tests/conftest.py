import pytest
import os

def pytest_runtest_setup(item):
    if 'slow' in item.keywords and 'SKIP_SLOW_TESTS' in os.environ \
            and len(item.session._collected) > 1:
        pytest.skip("ommit SKIP_SLOW_TESTS envvar to run")