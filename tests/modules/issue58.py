# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import gc
from multiprocessing import Pool


def pool_worker(item):
    return {"a": 1}


def pool_indexer(path):
    item_count = 0
    with Pool(processes=4) as pool:
        for _ in pool.imap(pool_worker, range(1, 200), chunksize=10):
            item_count = item_count + 1


# gc seems to cause SegFault with multithreading
# Pool creates a couple of thread and it's failing the test
# https://github.com/python/cpython/issues/101975

gc.disable()
pool_indexer(10)
gc.enable()
