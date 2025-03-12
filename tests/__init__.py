# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

try:
    import coredumpy
    import os
    coredumpy.patch_unittest(directory=os.getenv("COREDUMPY_DUMP_DIR", "./"))
except ImportError:
    pass
