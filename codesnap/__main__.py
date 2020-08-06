# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import sys
from . import CodeSnap

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python -m codesnap your_script_to_run.py [args]")
    try:
        f = sys.argv[1]
        code_string = open(f).read()
    except FileNotFoundError:
        print("No such file as {}".format(f))
        exit(1)
    sys.argv.pop(0)
    snap = CodeSnap()
    snap.start()
    exec(code_string)
    snap.stop()
    snap.save()
