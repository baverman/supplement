import pytest
import os

import logging
logger = logging.getLogger('supplement')
logger.setLevel(int(os.environ['SUPP_LOG_LEVEL']))
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(name)s %(levelname)s: %(message)s"))
logger.addHandler(handler)


def pytest_runtest_setup(item):
    if 'slow' in item.keywords and 'SKIP_SLOW_TESTS' in os.environ \
            and len(item.session._collected) > 1:
        pytest.skip("ommit SKIP_SLOW_TESTS envvar to run")