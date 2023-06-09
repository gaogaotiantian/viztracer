import os
from multiprocessing import Pool


def f(x):
    return x ** x


if __name__ == "__main__":
    process_num = 5
    with Pool(processes=process_num) as pool:
        print(pool.map(f, range(10)))

        for i in pool.imap_unordered(f, range(10)):
            print(i)

        res = pool.apply_async(f, (20,))       # runs in *only* one process
        print(res.get(timeout=1))              # prints "400"

        res = pool.apply_async(os.getpid, ())  # runs in *only* one process
        print(res.get(timeout=1))              # prints the PID of that process

        multiple_results = [pool.apply_async(os.getpid, ()) for i in range(process_num)]
        print([res.get(timeout=1) for res in multiple_results])
