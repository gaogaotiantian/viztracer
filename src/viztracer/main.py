# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import sys
import argparse
import os
import subprocess
from . import VizTracer
from . import FlameGraph
from .report_builder import ReportBuilder


def main():
    import runpy

    parser = argparse.ArgumentParser(prog="python -m viztracer")
    parser.add_argument("--tracer", nargs="?", choices=["c", "python"], default="c",
            help="specify the tracer you use. Can only be c or python")
    parser.add_argument("--tracer_entries", nargs="?", type=int, default=5000000,
            help="size of circular buffer. How many entries can it store")
    parser.add_argument("--output_file", "-o", nargs="?", default=None,
            help="output file path. End with .json or .html or .gz")
    parser.add_argument("--output_dir", nargs="?", default=None,
            help="output directory. Should only be used when --pid_suffix is used")
    parser.add_argument("--quiet", action="store_true", default=False,
            help="stop VizTracer from printing anything")
    parser.add_argument("--max_stack_depth", nargs="?", type=int, default=-1,
            help="maximum stack depth you want to trace.")
    parser.add_argument("--exclude_files", nargs="*", default=None, 
            help="specify the files(directories) you want to exclude from tracing. Can't be used with --include_files")
    parser.add_argument("--include_files", nargs="*", default=None,
            help="specify the only files(directories) you want to include from tracing. Can't be used with --exclude_files")
    parser.add_argument("--ignore_c_function", action="store_true", default=False,
            help="ignore all c functions including most builtin functions and libraries")
    parser.add_argument("--log_return_value", action="store_true", default=False,
            help="log return value of the function in the report")
    parser.add_argument("--log_print", action="store_true", default=False,
            help="replace all print() function to adding an event to the result")
    parser.add_argument("--pid_suffix", action="store_true", default=False,
            help="append pid to file name. This should be used when you try to trace multi process programs. Will by default generate json files")
    parser.add_argument("--save_flamegraph", action="store_true", default=False,
            help="save flamegraph after generating the VizTracer report")
    parser.add_argument("--generate_flamegraph", nargs="?", default=None,
            help="generate a flamegraph from json VizTracer report. Specify the json file to use")
    parser.add_argument("--run", nargs="*", default=[],
            help="explicitly specify the python commands you want to trace. Should be used if there's ambiguity")
    parser.add_argument("--module", "-m", nargs="?", default=None,
            help="run module with VizTracer")
    parser.add_argument("--combine", nargs="*", default=[],
            help="combine all json reports to a single report. Specify all the json reports you want to combine")
    parser.add_argument("command", nargs=argparse.REMAINDER,
            help="python commands to trace")
    options = parser.parse_args(sys.argv[1:])

    if options.command:
        command = options.command
    elif options.run:
        command = options.run
    elif options.module:
        command = options.command
    elif options.generate_flamegraph:
        flamegraph = FlameGraph()
        flamegraph.load(options.generate_flamegraph)
        if options.output_file:
            ofile = options.output_file
        else:
            ofile = "result_flamegraph.html"
        flamegraph.save(ofile)
        exit(0)
    elif options.combine:
        builder = ReportBuilder(options.combine)
        if options.output_file:
            ofile = options.output_file
        else:
            ofile = "result.html"
        builder.save(output_file=ofile)
        exit(0)
    else:
        parser.print_help()
        exit(0)

    if options.module:
        code = "run_module(modname, run_name='__main__')"
        global_dict = {
            "run_module": runpy.run_module,
            "modname": options.module
        }
        sys.argv = [options.module] + command[:]
    else:
        file_name = command[0]
        if not os.path.exists(file_name):
            if sys.platform in ["linux", "linux2", "darwin"]:
                p = subprocess.Popen(["which", file_name], stdout=subprocess.PIPE)
                file_name = p.communicate()[0].decode("utf-8").strip()
                if not file_name or not os.path.exists(file_name):
                    print("No such file as {}".format(file_name))
                    exit(1)
            else:
                print("No such file as {}".format(file_name))
                exit(1)

        code_string = open(file_name).read()
        global_dict = {
            "__name__": "__main__",
            "__file__": file_name,
            "__package__": None,
            "__cached__": None
        }
        code = compile(code_string, file_name, "exec")
        sys.path.insert(0, os.path.dirname(file_name))
        sys.argv = command[:]

    if options.quiet:
        verbose = 0
    else:
        verbose = 1

    if options.output_file:
        ofile = options.output_file
    elif options.pid_suffix:
        ofile = "result.json"
    else:
        ofile = "result.html"

    if options.output_dir:
        if not os.path.exists(options.output_dir):
            os.mkdir(options.output_dir)
        ofile = os.path.join(options.output_dir, ofile)
        print(ofile)

    tracer = VizTracer(
        tracer=options.tracer,
        tracer_entries=options.tracer_entries,
        verbose=verbose,
        output_file=ofile,
        max_stack_depth=options.max_stack_depth,
        exclude_files=options.exclude_files,
        include_files=options.include_files,
        ignore_c_function=options.ignore_c_function,
        log_return_value=options.log_return_value,
        save_on_exit=True,
        pid_suffix=options.pid_suffix,
        log_print=options.log_print
    )

    tracer.start()
    exec(code, global_dict)
    tracer.stop()
    tracer.save(output_file=ofile, save_flamegraph=options.save_flamegraph)
