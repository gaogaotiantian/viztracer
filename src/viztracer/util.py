# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import errno
import os
import re
import sys
from typing import Union


def size_fmt(num: Union[int, float], suffix: str = 'B') -> str:
    for unit in ['', 'Ki', 'Mi', 'Gi']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}{'Ti'}{suffix}"


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


color_support = True


if sys.platform == "win32":
    try:
        # https://stackoverflow.com/questions/36760127/...
        # how-to-use-the-new-support-for-ansi-escape-sequences-in-the-windows-10-console
        from ctypes import windll
        kernel32 = windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:  # pragma: no cover
        color_support = False


def color_print(color, s: str, **kwargs) -> None:
    if color_support:
        print(bcolors.__getattribute__(color) + s + bcolors.ENDC, **kwargs)
    else:  # pragma: no cover
        print(s)


def same_line_print(s: str, width=80, **kwargs) -> None:
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


# https://github.com/giampaolo/psutil
def pid_exists(pid):
    """Check whether pid exists in the current process table.
    UNIX only.
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:  # pragma: no cover
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH)
            raise
    else:
        return True
