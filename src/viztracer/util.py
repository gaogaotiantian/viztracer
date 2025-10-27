# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import datetime
import errno
import os
import re
import sys

# Windows macros
STILL_ACTIVE = 0x103
ERROR_ACCESS_DENIED = 0x5
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def size_fmt(num: int | float, suffix: str = 'B') -> str:
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


def same_line_print(s: str, width: int = 80, **kwargs) -> None:
    print(f"\r{'':<{width}}", end="")  # clear the line
    print(f"\r{s}", end="", **kwargs)


def unique_file_name(exec_name: str) -> str:
    # Get the base name of the executable
    filename = os.path.basename(exec_name)

    # Remove the extension
    filename = filename.split(".")[0]

    d = datetime.datetime.now()
    return "_".join([
        f"{filename}",
        f"{d.year}{d.month:02d}{d.day:02d}",
        f"{d.hour:02d}{d.minute:02d}{d.second:02d}",
        f"{os.getpid()}.json"
    ])


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
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        # On Windows, 0 is an idle process buw we don't need to
        # check it here
        raise ValueError('invalid PID 0')
    if sys.platform == "win32":
        # Windows
        import ctypes
        kernel32 = ctypes.windll.kernel32

        process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, 0, pid)
        if not process:
            if kernel32.GetLastError() == ERROR_ACCESS_DENIED:
                # Access is denied, which means there's a process.
                # Usually it's impossible to run here in viztracer.
                return True     # pragma: no cover
            else:
                return False

        exit_code = ctypes.c_ulong()
        out = kernel32.GetExitCodeProcess(process, ctypes.byref(exit_code))
        kernel32.CloseHandle(process)
        # nonzero return value means the funtion succeeds
        if out:
            if exit_code.value == STILL_ACTIVE:
                # According to documents of GetExitCodeProcess.
                # If a thread returns STILL_ACTIVE (259) as an error code,
                # then applications that test for that value could interpret
                # it to mean that the thread is still running, and continue
                # to test for the completion of the thread after the thread
                # has terminated, which could put the application into an
                # infinite loop.
                return True
            else:
                return False
        else:   # pragma: no cover
            if kernel32.GetLastError() == ERROR_ACCESS_DENIED:
                # Access is denied, which means there's a process.
                # Usually it's impossible to run here in viztracer.
                return True
        return False    # pragma: no cover
    else:
        # UNIX
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


def frame_stack_has_func(frame, funcs):
    while frame:
        if any(frame.f_code == func.__code__ for func in funcs):
            return True
        frame = frame.f_back
    return False
