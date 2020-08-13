# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

import sys
import argparse
from . import VizTracer

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--tracer", nargs="?", choices=["c", "python"], default="c")
    parser.add_argument("--output_file", "-o", nargs="?", default="result.html")
    parser.add_argument("--quiet", action="store_true", default=False)
    parser.add_argument("--max_stack_depth", nargs="?", type=int, default=-1)
    parser.add_argument("--exclude_files", nargs="*", default=None)
    parser.add_argument("--include_files", nargs="*", default=None)
    parser.add_argument("--run", nargs="*", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    options = parser.parse_args(sys.argv[1:])

    if options.command:
        command = options.command
    elif options.run:
        command = options.run
    else:
        parser.print_help()
        exit(0)

    try:
        f = command[0]
        code_string = open(f).read()
    except FileNotFoundError:
        print("No such file as {}".format(f))
        exit(1)
    sys.argv = command[1:]
    if options.quiet:
        verbose = 0
    else:
        verbose = 1
    tracer = VizTracer(
        tracer=options.tracer,
        verbose=verbose,
        max_stack_depth=options.max_stack_depth,
        exclude_files=options.exclude_files,
        include_files=options.include_files
    )
    tracer.start()
    exec(code_string)
    tracer.stop()
    tracer.save(output_file=options.output_file)
