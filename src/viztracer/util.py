# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import platform
import subprocess


def size_fmt(num, suffix='B'):
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


def color_print(color, s):
    print(bcolors.__getattribute__(color) + s + bcolors.ENDC)


def get_url_from_file(file_path):
    # file_path should be absolute
    uname = platform.uname()
    if uname.system.lower() == "linux" and "microsoft" in uname.release.lower():
        # We are on WSL, need to convert file_path
        p = subprocess.run(["wslpath", "-w", file_path], stdout=subprocess.PIPE)
        if p.returncode == 0:
            file_path = p.stdout.decode("utf-8")
        else:
            raise Exception("Can't convert path '{}' to Windows path".format(file_path))

    return file_path


def get_tracer():
    try:
        return __viz_tracer__
    except NameError:
        return None
