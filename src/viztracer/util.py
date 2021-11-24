# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import re
from typing import Union


def size_fmt(num: Union[int, float], suffix: str = 'B'):
    for unit in ['', 'Ki', 'Mi', 'Gi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Ti', suffix)


class _bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


bcolors = _bcolors()


def color_print(color, s: str, **kwargs):
    print(bcolors.__getattribute__(color) + s + bcolors.ENDC, **kwargs)


def same_line_print(s: str, width=80, **kwargs):
    print(f"\r{'':<{width}}", end="")  # clear the line
    print(f"\r{s}", end="", **kwargs)


def compare_version(ver1: str, ver2: str) -> int:
    # assuming ver1, ver2 are both str and in a pattern of
    # major.minor.micro with only numbers
    # return 1 if ver1 > ver2
    # return 0 if ver1 == ver2
    # return -1 if ver1 < ver2
    tuple1 = tuple((int(v) for v in ver1.split(".")))
    tuple2 = tuple((int(v) for v in ver2.split(".")))

    if tuple1 > tuple2:
        return 1
    elif tuple1 == tuple2:
        return 0
    else:
        return -1


def time_str_to_us(t_s: str) -> float:
    # t_s is a string representing a time
    # Should be [0-9\.]+([mun]?s)?
    #   ex. 300ns 23.5 .2ms
    # (This is not a perfect match, but enough for us to duck parse)
    # We need to convert it to us
    m = re.match(r"([0-9\.]+)([mun]?s)?", t_s)
    if m:
        try:
            val = float(m.group(1))
        except ValueError:
            raise ValueError(f"Can't convert {t_s} to time")
        unit = m.group(2)
        if unit == "s":
            val *= 1e6
        elif unit == "ms":
            val *= 1e3
        elif unit == "ns":
            val *= 1e-3
        return val
    else:
        raise ValueError(f"Can't convert {t_s} to time")


def get_tracer():
    try:
        return __viz_tracer__
    except NameError:
        return None
