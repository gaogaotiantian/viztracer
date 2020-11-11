# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import atexit
import sys
import argparse
import os
from multiprocessing import get_start_method
import types
import builtins
import signal
import shutil
from . import VizTracer
from . import FlameGraph
from .report_builder import ReportBuilder
from .util import get_url_from_file
from .code_monkey import CodeMonkey


class VizUI:
    def __init__(self):
        self.tracer = None
        self.parser = self.create_parser()
        self.verbose = 1
        self.ofile = "result.html"
        self.options = None
        self.args = []
        self._exiting = False
        self.multiprocess_output_dir = "./viztracer_multiprocess_tmp"

    def create_parser(self):
        parser = argparse.ArgumentParser(prog="python -m viztracer")
        parser.add_argument("--tracer_entries", nargs="?", type=int, default=1000000,
                            help="size of circular buffer. How many entries can it store")
        parser.add_argument("--output_file", "-o", nargs="?", default=None,
                            help="output file path. End with .json or .html or .gz")
        parser.add_argument("--output_dir", nargs="?", default=None,
                            help="output directory. Should only be used when --pid_suffix is used")
        parser.add_argument("--file_info", action="store_true", default=False,
                            help=argparse.SUPPRESS)
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
        parser.add_argument("--log_sparse", action="store_true", default=False,
                            help="log only selected functions with @log_sparse")
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
        parser.add_argument("--log_func_entry", nargs="*", default=None,
                            help="log entry of the function with specified names")
        parser.add_argument("--log_exception", action="store_true", default=False,
                            help="log all exception when it's raised")
        parser.add_argument("--log_subprocess", action="store_true", default=False,
                            help="log subprocesses")
        parser.add_argument("--subprocess_child", action="store_true", default=False,
                            help=argparse.SUPPRESS)
        parser.add_argument("--log_multiprocess", action="store_true", default=False,
                            help="log multiprocesses")
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
        return parser

    def parse(self, argv):
        # If -- or --run exists, all the commands after --/--run are the commands we need to run
        # We need to filter those out, they might conflict with our arguments
        if "--" in argv[1:]:
            idx = argv.index("--")
        elif "--run" in argv[1:]:
            idx = argv.index("--run")
        else:
            idx = None

        if idx:
            if idx == len(sys.argv) - 1:
                return False, "You need to specify commands after --/--run"
            else:
                options, command = self.parser.parse_args(argv[1:idx]), argv[idx+1:]
                self.args = argv[1:idx]
        else:
            options, command = self.parser.parse_known_args(argv[1:])
            self.args = [elem for elem in argv[1:] if elem not in command]

        if options.quiet:
            self.verbose = 0

        if options.output_file:
            self.ofile = options.output_file
        elif options.pid_suffix:
            self.ofile = "result.json"

        if options.output_dir:
            if not os.path.exists(options.output_dir):
                os.mkdir(options.output_dir)
            self.ofile = os.path.join(options.output_dir, self.ofile)

        if options.log_subprocess:
            if not options.subprocess_child:
                self.args = self.args + ["--subprocess_child", "--output_dir", self.multiprocess_output_dir, "-o", "result.json", "--pid_suffix"]
            self.patch_subprocess()

        self.options, self.command = options, command

        return True, None

    def search_file(self, file_name):
        if os.path.isfile(file_name):
            return file_name

        # search file in $PATH
        if "PATH" in os.environ:
            if sys.platform in ["linux", "linux2", "darwin"]:
                path_sep = ":"
            elif sys.platform in ["win32"]:
                path_sep = ";"
            else:  # pragma: no cover
                return None

            for dir_name in os.environ["PATH"].split(path_sep):
                candidate = os.path.join(dir_name, file_name)
                if os.path.isfile(candidate):
                    return candidate

        return None

    def patch_subprocess(self):
        ui = self

        def subprocess_init(self, args, **kwargs):
            if type(args) is list:
                if args[0].startswith("python"):
                    args = ["viztracer"] + ui.args + ["--"] + args[1:]
            self.__originit__(args, **kwargs)

        import subprocess
        subprocess.Popen.__originit__ = subprocess.Popen.__init__
        subprocess.Popen.__init__ = subprocess_init

    def patch_multiprocessing(self, tracer):

        def func_after_fork(tracer):

            def exit_routine():
                self.exit_routine()

            from multiprocessing.util import Finalize
            import signal
            Finalize(tracer, exit_routine, exitpriority=32)

            def term_handler(signalnum, frame):
                self.exit_routine()
            signal.signal(signal.SIGTERM, term_handler)

        from multiprocessing.util import register_after_fork
        tracer.pid_suffix = True
        tracer.output_file = os.path.join(self.multiprocess_output_dir, "result.json")
        register_after_fork(tracer, func_after_fork)

    def run(self):
        if self.options.module:
            return self.run_module()
        elif self.command:
            return self.run_command()
        elif self.options.generate_flamegraph:
            return self.run_generate_flamegraph()
        elif self.options.combine:
            return self.run_combine()
        else:
            self.parser.print_help()
            return True, None

    def run_code(self, code, global_dict):
        options = self.options
        verbose = self.verbose
        ofile = self.ofile

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
            pid_suffix=options.pid_suffix
        )

        self.tracer = tracer

        builtins.__dict__["__viz_tracer__"] = tracer

        self.parent_pid = os.getpid()
        if options.log_multiprocess:
            if get_start_method() != "fork":
                return False, "Only fork based multiprocess is supported"
            self.patch_multiprocessing(tracer)

        def term_handler(signalnum, frame):
            self.exit_routine()
        signal.signal(signal.SIGTERM, term_handler)

        atexit.register(self.exit_routine)
        if options.log_sparse:
            tracer.enable = True
        else:
            tracer.start()
        exec(code, global_dict)
        tracer.stop()

        self.exit_routine()

    def run_module(self):
        import runpy
        code = "run_module(modname, run_name='__main__')"
        global_dict = {
            "run_module": runpy.run_module,
            "modname": self.options.module
        }
        sys.argv = [self.options.module] + self.command[:]
        sys.path.append(os.getcwd())
        return self.run_code(code, global_dict)

    def run_command(self):
        command = self.command
        options = self.options
        file_name = command[0]
        search_result = self.search_file(file_name)
        if not search_result:
            return False, "No such file as {}".format(file_name)
        file_name = search_result
        code_string = open(file_name, "rb").read()
        if options.log_var or options.log_number or options.log_attr or \
                options.log_func_exec or options.log_exception or options.log_func_entry:
            monkey = CodeMonkey(code_string, file_name)
            if options.log_var:
                monkey.add_instrument("log_var", {"varnames": options.log_var})
            if options.log_number:
                monkey.add_instrument("log_number", {"varnames": options.log_number})
            if options.log_attr:
                monkey.add_instrument("log_attr", {"varnames": options.log_attr})
            if options.log_func_exec:
                monkey.add_instrument("log_func_exec", {"funcnames": options.log_func_exec})
            if options.log_func_entry:
                monkey.add_instrument("log_func_entry", {"funcnames": options.log_func_entry})
            if options.log_exception:
                monkey.add_instrument("log_exception", {})
            builtins.compile = monkey.compile

        main_mod = types.ModuleType("__main__")
        main_mod.__file__ = os.path.abspath(file_name)
        main_mod.__builtins__ = globals()["__builtins__"]

        sys.modules["__main__"] = main_mod
        code = compile(code_string, os.path.abspath(file_name), "exec")
        sys.path.insert(0, os.path.dirname(file_name))
        sys.argv = command[:]
        return self.run_code(code, main_mod.__dict__)

    def run_generate_flamegraph(self):
        options = self.options
        flamegraph = FlameGraph()
        flamegraph.load(options.generate_flamegraph)
        if options.output_file:
            ofile = options.output_file
        else:
            ofile = "result_flamegraph.html"
        flamegraph.save(ofile)

        return True, None

    def run_combine(self):
        options = self.options
        builder = ReportBuilder(options.combine)
        if options.output_file:
            ofile = options.output_file
        else:
            ofile = "result.html"
        builder.save(output_file=ofile)

        return True, None

    def save(self, tracer):
        options = self.options
        ofile = self.ofile

        tracer.stop()

        if options.log_multiprocess:
            is_main_process = os.getpid() == self.parent_pid
        elif options.log_subprocess:
            is_main_process = not options.subprocess_child

        if options.log_subprocess or options.log_multiprocess:
            tracer.pid_suffix = True
            if is_main_process:
                tracer.save(output_file=os.path.join(self.multiprocess_output_dir, "result.json"))
                builder = ReportBuilder([os.path.join(self.multiprocess_output_dir, f) for f in os.listdir(self.multiprocess_output_dir)])
                builder.save(output_file=ofile)
                shutil.rmtree(self.multiprocess_output_dir)
            else:  # pragma: no cover
                tracer.save(save_flamegraph=options.save_flamegraph)
        else:
            tracer.save(output_file=ofile, save_flamegraph=options.save_flamegraph, file_info=options.file_info)

    def exit_routine(self):
        atexit.unregister(self.exit_routine)
        if not self._exiting:
            self._exiting = True
            self.save(self.tracer)
            if self.options.open:
                import webbrowser
                try:
                    webbrowser.open(get_url_from_file(os.path.abspath(self.ofile)))
                except webbrowser.Error:  # pragma: no cover
                    return False, "Can not open the report"
            exit(0)


def main():
    ui = VizUI()
    success, err_msg = ui.parse(sys.argv)
    if not success:
        print(err_msg)
        exit(1)
    success, err_msg = ui.run()
    if not success:
        print(err_msg)
        exit(1)
