from multiprocessing import Pool


def pool_worker(item):
    return {"a": 1}


def pool_indexer(path):
    item_count = 0
    with Pool(processes=4) as pool:
        for res in pool.imap(pool_worker, range(1, 200), chunksize=10):
            item_count = item_count + 1


pool_indexer(10)
