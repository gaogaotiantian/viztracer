# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import argparse
import atexit
import builtins
import configparser
import multiprocessing.util  # type: ignore
import platform
import os
import re
import shutil
import signal
import sys
import tempfile
import threading
import time
import types
from typing import Any, Dict, List, Optional, Tuple

from . import __version__
from .code_monkey import CodeMonkey
from .patch import patch_multiprocessing, patch_subprocess
from .report_builder import ReportBuilder
from .util import time_str_to_us, color_print, same_line_print
from .viztracer import VizTracer


class VizUI:
    def __init__(self):
        self.tracer: Optional[VizTracer] = None
        self.parser: argparse.ArgumentParser = self.create_parser()
        self.verbose: int = 1
        self.ofile: str = "result.json"
        self.options: argparse.Namespace = argparse.Namespace()
        self.args: List[str] = []
        self._exiting: bool = False
        self.multiprocess_output_dir: str = tempfile.mkdtemp()
        self.cwd: str = os.getcwd()

    def create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="python -m viztracer")
        parser.add_argument("--version", action="store_true", default=False,
                            help="show version of viztracer")
        parser.add_argument("-c", "--cmd_string", nargs="?", default=None,
                            help="program passed in as string")
        parser.add_argument("--rcfile", nargs="?", default=None,
                            help="specify rcfile for viztracer")
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
        parser.add_argument("--trace_self", action="store_true", default=False,
                            help=argparse.SUPPRESS)
        parser.add_argument("--plugins", nargs="*", default=[],
                            help="specify plugins for VizTracer")
        parser.add_argument("--max_stack_depth", nargs="?", type=int, default=-1,
                            help="maximum stack depth you want to trace.")
        parser.add_argument("--min_duration", nargs="?", default="0",
                            help="minimum duration of function to log")
        parser.add_argument("--exclude_files", nargs="*", default=None,
                            help=("specify the files(directories) you want to exclude from tracing. "
                                  "Can't be used with --include_files"))
        parser.add_argument("--include_files", nargs="*", default=None,
                            help=("specify the only files(directories) you want to include from tracing. "
                                  "Can't be used with --exclude_files"))
        parser.add_argument("--ignore_c_function", action="store_true", default=False,
                            help="ignore all c functions including most builtin functions and libraries")
        parser.add_argument("--ignore_frozen", action="store_true", default=False,
                            help="ignore all functions that are frozen(like import)")
        parser.add_argument("--log_exit", action="store_true", default=False,
                            help="log functions in exit functions like atexit")
        parser.add_argument("--log_func_retval", action="store_true", default=False,
                            help="log return value of the function in the report")
        parser.add_argument("--log_print", action="store_true", default=False,
                            help="replace all print() function to adding an event to the result")
        parser.add_argument("--log_sparse", action="store_true", default=False,
                            help="log only selected functions with @log_sparse")
        parser.add_argument("--log_func_args", action="store_true", default=False,
                            help="log all function arguments, this will introduce large overhead")
        parser.add_argument("--log_gc", action="store_true", default=False,
                            help="log ref cycle garbage collection operations")
        parser.add_argument("--log_var", nargs="*", default=None,
                            help="log variable with specified names")
        parser.add_argument("--log_number", nargs="*", default=None,
                            help="log variable with specified names as a number(using VizCounter)")
        parser.add_argument("--log_attr", nargs="*", default=None,
                            help="log attribute with specified names")
        parser.add_argument("--log_audit", nargs="*", default=None,
                            help="log audit when audit event is raised, takes regex")
        parser.add_argument("--log_func_exec", nargs="*", default=None,
                            help="log execution of function with specified names")
        parser.add_argument("--log_func_entry", nargs="*", default=None,
                            help="log entry of the function with specified names")
        parser.add_argument("--log_exception", action="store_true", default=False,
                            help="log all exception when it's raised")
        parser.add_argument("--log_subprocess", action="store_true", default=False,
                            help=argparse.SUPPRESS)
        parser.add_argument("--subprocess_child", action="store_true", default=False,
                            help=argparse.SUPPRESS)
        parser.add_argument("--dump_raw", action="store_true", default=False,
                            help=argparse.SUPPRESS)
        parser.add_argument("--log_multiprocess", action="store_true", default=False,
                            help=argparse.SUPPRESS)
        parser.add_argument("--log_async", action="store_true", default=False,
                            help="log as async format")
        parser.add_argument("--ignore_multiprocess", action="store_true", default=False,
                            help="Do not log any process other than the main process")
        parser.add_argument("--magic_comment", action="store_true", default=False,
                            help="Process VizTracer specific comments")
        parser.add_argument("--minimize_memory", action="store_true", default=False,
                            help="Use json.dump to dump chunks to file to save memory")
        parser.add_argument("--vdb", action="store_true", default=False,
                            help="Instrument for vdb, will increase the overhead")
        parser.add_argument("--pid_suffix", action="store_true", default=False,
                            help=("append pid to file name. "
                                  "This should be used when you try to trace multi process programs. "
                                  "Will by default generate json files"))
        parser.add_argument("--module", "-m", nargs="?", default=None,
                            help="run module with VizTracer")
        parser.add_argument("--combine", nargs="*", default=[],
                            help=("combine all json reports to a single report. "
                                  "Specify all the json reports you want to combine"))
        parser.add_argument("--align_combine", nargs="*", default=[],
                            help=("combine all json reports to a single report and align them from the start "
                                  "Specify all the json reports you want to combine"))
        parser.add_argument("--open", action="store_true", default=False,
                            help="open the report in browser after saving")
        parser.add_argument("--attach", type=int, nargs="?", default=-1,
                            help="pid of process with VizTracer installed")
        parser.add_argument("-t", type=float, nargs="?", default=-1,
                            help="time you want to trace the process")
        return parser

    @property
    def is_main_process(self) -> bool:
        options = self.options
        if options.subprocess_child:
            return False  # pragma: no cover
        return self.parent_pid == os.getpid()

    def load_config_file(self, filename=".viztracerrc"):
        ret = argparse.Namespace()
        if os.path.exists(filename):
            cfg_parser = configparser.ConfigParser()
            cfg_parser.read(filename)
            if "default" not in cfg_parser:
                raise ValueError("Config file does not contain [default] section")
            for action in self.parser._actions:
                if hasattr(action, "dest") and action.dest in cfg_parser["default"]:
                    if action.nargs == 0:
                        setattr(ret, action.dest, action.const)
                    elif action.nargs is None or action.nargs == "?":
                        if action.type == bool:  # pragma: no cover
                            # VizTracer does not have any option that belongs to this case
                            # store_true/store_false has nargs == 0, this only happens
                            # when it's a store, but with type == bool
                            setattr(ret, action.dest, cfg_parser["default"].getboolean(action.dest))
                        else:
                            convert = action.type if action.type is not None else str
                            setattr(ret, action.dest, convert(cfg_parser["default"][action.dest]))
                    else:
                        convert = action.type if action.type is not None else str
                        setattr(ret, action.dest, [convert(val) for val in cfg_parser["default"][action.dest].strip().split()])
        else:
            if filename != ".viztracerrc":
                # User specified name, raise error
                raise FileNotFoundError(f"{filename} does not exist")
        return ret

    def parse(self, argv: List[str]) -> Tuple[bool, Optional[str]]:
        # If -- or --run exists, all the commands after --/--run are the commands we need to run
        # We need to filter those out, they might conflict with our arguments
        idx: Optional[int] = None
        if "--" in argv[1:]:
            idx = argv.index("--")
        elif "--run" in argv[1:]:
            idx = argv.index("--run")

        rcfile_parser = argparse.ArgumentParser()
        rcfile_parser.add_argument("--rcfile", nargs="?", default=".viztracerrc")
        rc_options, _ = rcfile_parser.parse_known_args(argv[1:])
        default_namespace = self.load_config_file(rc_options.rcfile)

        if idx is not None:
            options, command = self.parser.parse_args(argv[1:idx], namespace=default_namespace), argv[idx + 1:]
            self.args = argv[1:idx]
        else:
            options, command = self.parser.parse_known_args(argv[1:], namespace=default_namespace)
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

        if options.subprocess_child:
            # If it's a subprocess, we need to store the FEE data to the
            # directory from the parent process.
            # It's not practical to cover this line as it requires coverage
            # instrumentation on subprocess.
            output_file = self.ofile  # pragma: no cover
        else:
            output_file = os.path.join(self.multiprocess_output_dir, "result.json")

        if options.log_async:
            if int(platform.python_version_tuple()[1]) < 7:
                return False, "log_async only supports python 3.7+"

        if options.log_multiprocess or options.log_subprocess:  # pragma: no cover
            color_print(
                "WARNING",
                "--log_multiprocess and --log_subprocess are no longer needed to trace multi-process program")

        try:
            min_duration = time_str_to_us(options.min_duration)
        except ValueError:
            return False, f"Can't convert {options.min_duration} to time. Format should be 0.3ms or 13us"

        self.options, self.command = options, command
        self.init_kwargs = {
            "tracer_entries": options.tracer_entries,
            "verbose": 0,
            "output_file": output_file,
            "max_stack_depth": options.max_stack_depth,
            "exclude_files": options.exclude_files,
            "include_files": options.include_files,
            "ignore_c_function": options.ignore_c_function,
            "ignore_frozen": options.ignore_frozen,
            "log_func_retval": options.log_func_retval,
            "log_func_args": options.log_func_args,
            "log_print": options.log_print,
            "log_gc": options.log_gc,
            "log_sparse": options.log_sparse,
            "log_async": options.log_async,
            "vdb": options.vdb,
            "pid_suffix": True,
            "file_info": False,
            "register_global": True,
            "plugins": options.plugins,
            "trace_self": options.trace_self,
            "min_duration": min_duration,
            "dump_raw": True,
            "minimize_memory": options.minimize_memory
        }

        return True, None

    def search_file(self, file_name: str) -> Optional[str]:
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

    def install_all_hooks(self, tracer: VizTracer) -> None:
        options = self.options

        # multiprocess hook
        if not options.ignore_multiprocess:
            patch_multiprocessing(tracer)
            if not options.subprocess_child:
                patch_subprocess(self.args + ["--subprocess_child", "--dump_raw", "-o", tracer.output_file])

            # If we want to hook fork correctly with file waiter, we need to
            # use os.register_at_fork to write the file, and make sure
            # os.exec won't clear viztracer so that the file lives forever.
            # This is basically equivalent to py3.8 + Linux
            if hasattr(sys, "addaudithook"):
                if hasattr(os, "register_at_fork"):
                    def audit_hook(event, args):  # pragma: no cover
                        if event == "os.exec":
                            tracer.exit_routine()
                    sys.addaudithook(audit_hook)  # type: ignore
                    os.register_at_fork(after_in_child=lambda: tracer.label_file_to_write())  # type: ignore
                if options.log_audit is not None:
                    audit_regex_list = [re.compile(regex) for regex in options.log_audit]

                    def audit_hook(event, args):  # pragma: no cover
                        if len(audit_regex_list) == 0 or any((regex.fullmatch(event) for regex in audit_regex_list)):
                            tracer.log_instant(event, args={"args": [str(arg) for arg in args]})
                    sys.addaudithook(audit_hook)  # type: ignore

        # SIGTERM hook
        def term_handler(signalnum, frame):
            sys.exit(0)

        if self.is_main_process:
            signal.signal(signal.SIGTERM, term_handler)
            multiprocessing.util.Finalize(self, self.exit_routine, exitpriority=-1)
        else:
            signal.signal(signal.SIGTERM, term_handler)
            multiprocessing.util.Finalize(tracer, tracer.exit_routine, exitpriority=-1)

    def run(self) -> Tuple[bool, Optional[str]]:
        if self.options.version:
            return self.show_version()
        elif self.options.attach > 0:
            return self.attach()
        elif self.options.cmd_string is not None:
            return self.run_string()
        elif self.options.module:
            return self.run_module()
        elif self.command:
            return self.run_command()
        elif self.options.combine:
            return self.run_combine(files=self.options.combine)
        elif self.options.align_combine:
            return self.run_combine(files=self.options.align_combine, align=True)
        else:
            self.parser.print_help()
            return True, None

    def run_code(self, code: Any, global_dict: Dict[str, Any]):
        options = self.options
        self.parent_pid = os.getpid()

        tracer = VizTracer(**self.init_kwargs)
        self.tracer = tracer

        self.install_all_hooks(tracer)

        if options.log_sparse:
            tracer.enable = True
        else:
            tracer.start()

        exec(code, global_dict)

        if not options.log_exit:
            tracer.stop()

        # The user code may forked, check it because Finalize won't execute
        # if the pid is not the same
        if os.getpid() != self.parent_pid and not options.ignore_multiprocess:
            multiprocessing.util.Finalize(self.tracer, self.tracer.exit_routine, exitpriority=-1)

        # issue141 - concurrent.future requires a proper release by executing
        # threading._threading_atexits or it will deadlock if not explicitly
        # release the resource in the code
        # Python 3.9+ has this issue
        try:
            if threading._threading_atexits:  # type: ignore
                for atexit_call in threading._threading_atexits:  # type: ignore
                    atexit_call()
                threading._threading_atexits = []  # type: ignore
        except AttributeError:
            pass

        return True, None

    def run_module(self):
        import runpy
        code = "run_module(modname, run_name='__main__', alter_sys=True)"
        global_dict = {
            "run_module": runpy.run_module,
            "modname": self.options.module
        }
        sys.argv = [self.options.module] + self.command[:]
        sys.path.insert(0, os.getcwd())
        return self.run_code(code, global_dict)

    def run_string(self):
        cmd_string = self.options.cmd_string
        main_mod = types.ModuleType("__main__")
        setattr(main_mod, "__file__", "<string>")
        setattr(main_mod, "__builtins__", globals()["__builtins__"])

        sys.modules["__main__"] = main_mod
        code = compile(cmd_string, "<string>", "exec")
        sys.argv = ["-c"] + self.command[:]
        return self.run_code(code, main_mod.__dict__)

    def run_command(self) -> Tuple[bool, Optional[str]]:
        command = self.command
        options = self.options
        file_name = command[0]
        search_result = self.search_file(file_name)
        if not search_result:
            return False, "No such file as {}".format(file_name)
        file_name = search_result
        with open(file_name, "rb") as f:
            code_string = f.read()
        if options.magic_comment or options.log_var or options.log_number or options.log_attr or \
                options.log_func_exec or options.log_exception or options.log_func_entry:
            monkey = CodeMonkey(file_name)
            if options.magic_comment:
                monkey.add_source_processor()
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
            builtins.compile = monkey.compile  # type: ignore

        main_mod = types.ModuleType("__main__")
        setattr(main_mod, "__file__", os.path.abspath(file_name))
        setattr(main_mod, "__builtins__", globals()["__builtins__"])

        sys.modules["__main__"] = main_mod
        code = compile(code_string, os.path.abspath(file_name), "exec")
        sys.path.insert(0, os.path.dirname(file_name))
        sys.argv = command[:]
        return self.run_code(code, main_mod.__dict__)

    def run_combine(self, files: List[str], align: bool = False) -> Tuple[bool, Optional[str]]:
        options = self.options
        builder = ReportBuilder(files, align=align, minimize_memory=options.minimize_memory)
        if options.output_file:
            ofile = options.output_file
        else:
            ofile = "result.json"
        builder.save(output_file=ofile)

        return True, None

    def show_version(self) -> Tuple[bool, Optional[str]]:
        print(__version__)
        return True, None

    def attach(self) -> Tuple[bool, Optional[str]]:
        if sys.platform == "win32":
            return False, "VizTracer does not support this feature on Windows"
        pid = self.options.attach
        interval = self.options.t
        try:
            os.kill(pid, signal.SIGUSR1)
        except OSError:
            return False, f"pid {pid} does not exist"
        try:
            if interval > 0:
                time.sleep(interval)
            else:
                while True:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            pass

        try:
            os.kill(pid, signal.SIGUSR2)
        except OSError:  # pragma: no cover
            return False, f"pid {pid} already finished"

        return True, None

    def save(self) -> None:
        # This function will only be called from main process
        options = self.options
        ofile = self.ofile

        self.wait_children_finish()
        builder = ReportBuilder(
            [os.path.join(self.multiprocess_output_dir, f)
                for f in os.listdir(self.multiprocess_output_dir) if f.endswith(".json")],
            minimize_memory=options.minimize_memory,
            verbose=self.verbose)
        builder.save(output_file=ofile)
        shutil.rmtree(self.multiprocess_output_dir)

    def wait_children_finish(self) -> None:
        try:
            if any((f.endswith(".viztmp") for f in os.listdir(self.multiprocess_output_dir))):
                same_line_print("Wait for child processes to finish, Ctrl+C to skip")
                while any((f.endswith(".viztmp") for f in os.listdir(self.multiprocess_output_dir))):
                    time.sleep(0.5)
        except KeyboardInterrupt:
            pass

    def exit_routine(self) -> None:
        if self.tracer is not None:
            if not self._exiting:
                self._exiting = True
                if self.verbose > 0:
                    same_line_print("Saving trace data, this could take a while")
                self.tracer.exit_routine()
                self.save()
                if self.options.open:  # pragma: no cover
                    import subprocess
                    subprocess.run(["vizviewer", "--once", os.path.abspath(self.ofile)])


def main():
    ui = VizUI()
    success, err_msg = ui.parse(sys.argv)
    if not success:
        print(err_msg)
        sys.exit(1)
    try:
        success, err_msg = ui.run()
        if not success:
            print(err_msg)
            sys.exit(1)
    finally:
        atexit._run_exitfuncs()
