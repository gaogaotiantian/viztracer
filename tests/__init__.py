# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import sys


if os.getenv("GITHUB_ACTIONS") or os.getenv("ENABLE_COREDUMPY"):
    if sys.version_info < (3, 14):
        # coredumpy does not support Python 3.14 and above yet
        try:
            import coredumpy
            coredumpy.patch_unittest(directory=os.getenv("COREDUMPY_DUMP_DIR", "./"))
        except ImportError:
            pass
