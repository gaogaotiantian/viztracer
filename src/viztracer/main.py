# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import sys
import argparse
import os
import subprocess
import builtins
import webbrowser
from . import VizTracer
from . import FlameGraph
from .report_builder import ReportBuilder
from .util import get_url_from_file
from .code_monkey import CodeMonkey


def search_file(file_name):
    if os.path.isfile(file_name):
        return file_name
    
    # search file in $PATH
    if "PATH" in os.environ:
        if sys.platform in ["linux", "linux2", "darwin"]: 
            path_sep = ":"
        elif sys.platform in ["win32"]:
            path_sep = ";"
        else: # pragma: no cover
            return None
    
        for dir_name in os.environ["PATH"].split(path_sep):
            candidate = os.path.join(dir_name, file_name)
            if os.path.isfile(candidate):
                return candidate

    return None


def main():
    import runpy

    parser = argparse.ArgumentParser(prog="python -m viztracer")
    parser.add_argument("--tracer_entries", nargs="?", type=int, default=1000000,
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
    parser.add_argument("--ignore_non_file", action="store_true", default=False,
                        help="ignore all functions that are not in a vaild file(like import)")
    parser.add_argument("--log_return_value", action="store_true", default=False,
                        help="log return value of the function in the report")
    parser.add_argument("--log_print", action="store_true", default=False,
                        help="replace all print() function to adding an event to the result")
    parser.add_argument("--log_function_args", action="store_true", default=False,
                        help="log all function arguments, this will introduce large overhead")
    parser.add_argument("--log_gc", action="store_true", default=False,
                        help="log ref cycle garbage collection operations")
    parser.add_argument("--log_var", nargs="*", default=None,
                        help="log variable with specified names")
    parser.add_argument("--log_number", nargs="*", default=None,
                        help="log variable with specified names as a number(using VizCounter)")
    parser.add_argument("--log_attr", nargs="*", default=None,
                        help="log attribute with specified names")
    parser.add_argument("--log_func_exec", nargs="*", default=None,
                        help="log execution of function with specified names")
    parser.add_argument("--log_exception", action="store_true", default=False,
                        help="log all exception when it's raised")
    parser.add_argument("--novdb", action="store_true", default=False,
                        help="Do not instrument for vdb, will reduce the overhead")
    parser.add_argument("--pid_suffix", action="store_true", default=False,
                        help="append pid to file name. This should be used when you try to trace multi process programs. Will by default generate json files")
    parser.add_argument("--save_flamegraph", action="store_true", default=False,
                        help="save flamegraph after generating the VizTracer report")
    parser.add_argument("--generate_flamegraph", nargs="?", default=None,
                        help="generate a flamegraph from json VizTracer report. Specify the json file to use")
    parser.add_argument("--module", "-m", nargs="?", default=None,
                        help="run module with VizTracer")
    parser.add_argument("--combine", nargs="*", default=[],
                        help="combine all json reports to a single report. Specify all the json reports you want to combine")
    parser.add_argument("--open", action="store_true", default=False,
                        help="open the report in browser after saving")

    # If -- or --run exists, all the commands after --/--run are the commands we need to run
    # We need to filter those out, they might conflict with our arguments
    if "--" in sys.argv[1:]:
        idx = sys.argv.index("--")
    elif "--run" in sys.argv[1:]:
        idx = sys.argv.index("--run")
    else:
        idx = None

    if idx:
        if idx == len(sys.argv) - 1:
            print("You need to specify commands after --/--run")
            exit(1)
        else:
            options, command = parser.parse_args(sys.argv[1:idx]), sys.argv[idx+1:]
    else:
        options, command = parser.parse_known_args(sys.argv[1:])

    if not command and not options.module:
        if options.generate_flamegraph:
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
        search_result = search_file(file_name)
        if not search_result:
            print("No such file as {}".format(file_name))
            exit(1)
        file_name = search_result
        code_string = open(file_name, "rb").read()
        global_dict = {
            "__name__": "__main__",
            "__file__": file_name,
            "__package__": None,
            "__cached__": None
        }
        if options.log_var or options.log_number or options.log_attr or \
                options.log_func_exec or options.log_exception:
            monkey = CodeMonkey(code_string, file_name)
            if options.log_var:
                monkey.add_instrument("log_var", {"varnames": options.log_var})
            if options.log_number:
                monkey.add_instrument("log_number", {"varnames": options.log_number})
            if options.log_attr:
                monkey.add_instrument("log_attr", {"varnames": options.log_attr})
            if options.log_func_exec:
                monkey.add_instrument("log_func_exec", {"funcnames": options.log_func_exec})
            if options.log_exception:
                monkey.add_instrument("log_exception", {})
            builtins.compile = monkey.compile
        code = compile(code_string, os.path.abspath(file_name), "exec")
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
        tracer_entries=options.tracer_entries,
        verbose=verbose,
        output_file=ofile,
        max_stack_depth=options.max_stack_depth,
        exclude_files=options.exclude_files,
        include_files=options.include_files,
        ignore_c_function=options.ignore_c_function,
        ignore_non_file=options.ignore_non_file,
        log_return_value=options.log_return_value,
        log_function_args=options.log_function_args,
        log_print=options.log_print,
        log_gc=options.log_gc,
        novdb=options.novdb,
        save_on_exit=True,
        pid_suffix=options.pid_suffix
    )

    builtins.__dict__["__viz_tracer__"] = tracer
    global_dict["__builtins__"] = globals()["__builtins__"]
    tracer.start()
    exec(code, global_dict)
    tracer.stop()
    tracer.save(output_file=ofile, save_flamegraph=options.save_flamegraph)
    
    if options.open:
        try:
            webbrowser.open(get_url_from_file(os.path.abspath(ofile)))
        except webbrowser.Error as e: # pragma: no cover
            print(e, "Can not open the report")
