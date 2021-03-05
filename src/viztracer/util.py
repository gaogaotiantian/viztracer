# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


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


def compare_version(ver1, ver2):
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


def get_tracer():
    try:
        return __viz_tracer__
    except NameError:
        return None
