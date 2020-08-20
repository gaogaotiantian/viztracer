# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import functools
import viztracer.snaptrace as snaptrace


def ignore_function(func):
    @functools.wraps(func)
    def ignore_wrapper(*args, **kwargs):
        snaptrace.pause()
        ret = func(*args, **kwargs)
        snaptrace.resume()
        return ret

    return ignore_wrapper
