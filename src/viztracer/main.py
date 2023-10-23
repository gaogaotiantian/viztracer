# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import argparse
import atexit
import base64
import builtins
import configparser
import json
import multiprocessing.util  # type: ignore
import os
import shutil
import signal
import sys
import tempfile
import threading
import time
import types
from typing import Any, Dict, List, Optional, Tuple

from viztracer.vcompressor import VCompressor

from . import __version__
from .attach_process.add_code_to_python_process import run_python_code  # type: ignore
from .code_monkey import CodeMonkey
from .patch import install_all_hooks
from .report_builder import ReportBuilder
from .util import color_print, pid_exists, same_line_print, time_str_to_us
from .viztracer import VizTracer

# For all the procedures in VizUI, return a tuple as the result
# The first element bool indicates whether the procedure succeeds
# The second element is the error message if it fails.
VizProcedureResult = Tuple[bool, Optional[str]]


class VizUI:
    def __init__(self) -> None:
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
        parser.add_argument("--sanitize_function_name", action="store_true", default=False,
                            help="Sanitize logged function names to enforce utf-8 encoding")
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
        parser.add_argument("--pid_suffix", action="store_true", default=False,
                            help=("append pid to file name. "
                                  "This should be used when you try to trace multi process programs. "
                                  "Will by default generate json files"))
        parser.add_argument("--module", "-m", nargs="?", default=None,
                            help="run module with VizTracer")
        parser.add_argument("--compress", nargs="?", default=None,
                            help="Compress a json report to a compact cvf format")
        parser.add_argument("--decompress", nargs="?", default=None,
                            help="Decompress a compressed cvf file to a json format")
        parser.add_argument("--combine", nargs="*", default=[],
                            help=("combine all json reports to a single report. "
                                  "Specify all the json reports you want to combine"))
        parser.add_argument("--align_combine", nargs="*", default=[],
                            help=("combine all json reports to a single report and align them from the start "
                                  "Specify all the json reports you want to combine"))
        parser.add_argument("--open", action="store_true", default=False,
                            help="open the report in browser after saving")
        parser.add_argument("--attach", type=int, nargs="?", default=-1,
                            help="pid of Python process to trace")
        parser.add_argument("--attach_installed", type=int, nargs="?", default=-1,
                            help="pid of Python process with VizTracer installed")
        parser.add_argument("--uninstall", type=int, nargs="?", default=-1,
                            help="pid of Python process with VizTracer to be uninstalled")
        parser.add_argument("-t", type=float, nargs="?", default=-1,
                            help="time you want to trace the process")
        return parser

    def load_config_file(self, filename: str = ".viztracerrc") -> argparse.Namespace:
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

    def parse(self, argv: List[str]) -> VizProcedureResult:
        # If -- or --run exists, all the commands after --/--run are the commands we need to run
        # We need to filter those out, they might conflict with our arguments
        idx: Optional[int] = None
        if "--" in argv[1:]:
            idx = argv.index("--")
        elif "--run" in argv[1:]:
            idx = argv.index("--run")

        rcfile_parser = argparse.ArgumentParser(add_help=False)
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
            "log_audit": options.log_audit,
            "pid_suffix": True,
            "file_info": False,
            "register_global": True,
            "plugins": options.plugins,
            "trace_self": options.trace_self,
            "min_duration": min_duration,
            "sanitize_function_name": options.sanitize_function_name,
            "dump_raw": True,
            "minimize_memory": options.minimize_memory,
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

    def run(self) -> VizProcedureResult:
        if self.options.version:
            return self.show_version()
        elif self.options.attach > 0:
            return self.attach()
        elif self.options.attach_installed > 0:
            return self.attach_installed()
        elif self.options.uninstall > 0:
            return self.uninstall()
        elif self.options.cmd_string is not None:
            return self.run_string()
        elif self.options.module:
            return self.run_module()
        elif self.command:
            return self.run_command()
        elif self.options.compress:
            return self.run_compress()
        elif self.options.decompress:
            return self.run_decompress()
        elif self.options.combine:
            return self.run_combine(files=self.options.combine)
        elif self.options.align_combine:
            return self.run_combine(files=self.options.align_combine, align=True)
        else:
            self.parser.print_help()
            return True, None

    def run_code(self, code: Any, global_dict: Dict[str, Any]) -> VizProcedureResult:
        options = self.options
        self.parent_pid = os.getpid()

        tracer = VizTracer(**self.init_kwargs)
        self.tracer = tracer

        install_all_hooks(tracer,
                          self.args,
                          patch_multiprocess=not options.ignore_multiprocess)

        def term_handler(signalnum, frame):
            sys.exit(0)

        signal.signal(signal.SIGTERM, term_handler)

        if options.subprocess_child:
            multiprocessing.util.Finalize(tracer, tracer.exit_routine, exitpriority=-1)
        else:
            multiprocessing.util.Finalize(self, self.exit_routine, exitpriority=-1)

        if not options.log_sparse:
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

    def run_module(self) -> VizProcedureResult:
        import runpy
        code = "run_module(modname, run_name='__main__', alter_sys=True)"
        global_dict = {
            "run_module": runpy.run_module,
            "modname": self.options.module,
        }
        sys.argv = [self.options.module] + self.command[:]
        sys.path.insert(0, os.getcwd())
        return self.run_code(code, global_dict)

    def run_string(self) -> VizProcedureResult:
        cmd_string = self.options.cmd_string
        main_mod = types.ModuleType("__main__")
        setattr(main_mod, "__file__", "<string>")
        setattr(main_mod, "__builtins__", globals()["__builtins__"])

        sys.modules["__main__"] = main_mod
        code = compile(cmd_string, "<string>", "exec")
        sys.argv = ["-c"] + self.command[:]
        return self.run_code(code, main_mod.__dict__)

    def run_command(self) -> VizProcedureResult:
        command = self.command
        options = self.options
        file_name = command[0]
        search_result = self.search_file(file_name)
        if not search_result:
            return False, f"No such file as {file_name}"
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

    def run_compress(self):
        file_to_compress = self.options.compress
        if not file_to_compress or not os.path.exists(file_to_compress):
            return False, f"Unable to find file {file_to_compress}"

        if not file_to_compress.endswith(".json"):
            return False, "Only support compressing json report"

        if not self.options.output_file:
            output_file = "result.cvf"
        else:
            output_file = self.options.output_file

        compressor = VCompressor()

        with open(file_to_compress) as f:
            data = json.load(f)
            compressor.compress(data, output_file)

        return True, None

    def run_decompress(self):
        file_to_decompress = self.options.decompress
        if not file_to_decompress or not os.path.exists(file_to_decompress):
            return False, f"Unable to find file {file_to_decompress}"

        if not self.options.output_file:
            output_file = "result.json"
        else:
            output_file = self.options.output_file

        compressor = VCompressor()

        data = compressor.decompress(file_to_decompress)

        with open(output_file, "w") as f:
            json.dump(data, f)

        return True, None

    def run_combine(self, files: List[str], align: bool = False) -> VizProcedureResult:
        options = self.options
        builder = ReportBuilder(files, align=align, minimize_memory=options.minimize_memory)
        if options.output_file:
            ofile = options.output_file
        else:
            ofile = "result.json"
        builder.save(output_file=ofile)

        return True, None

    def show_version(self) -> VizProcedureResult:
        print(__version__)
        return True, None

    def attach(self) -> VizProcedureResult:
        pid = self.options.attach
        interval = self.options.t

        if sys.platform == "win32":
            return False, "VizTracer does not support this feature on Windows"

        if sys.platform == "darwin" and sys.version_info >= (3, 11):
            print("Warning: attach may not work on 3.11+ on Mac due to hardened runtime")

        if not pid_exists(pid):
            return False, f"pid {pid} does not exist!"

        # If we are doing attach, we need to clean init_kwargs first
        self.init_kwargs.update({
            "output_file": os.path.abspath(self.ofile),
            "pid_suffix": False,
            "file_info": True,
            "register_global": True,
            "dump_raw": False,
            "verbose": 1 if self.verbose != 0 else 0,
        })
        b64s = base64.urlsafe_b64encode(json.dumps(self.init_kwargs).encode("ascii")).decode("ascii")
        start_code = f"import viztracer.attach; viztracer.attach.start_attach(\\\"{b64s}\\\")"
        stop_code = "viztracer.attach.stop_attach()"
        retcode, _, _, = run_python_code(pid, start_code)
        if retcode != 0:  # pragma: no cover
            return False, f"Failed to inject code [err {retcode}]"

        self._wait_attach(interval)

        retcode, _, _ = run_python_code(pid, stop_code)
        if retcode != 0:  # pragma: no cover
            return False, f"Failed to inject code [err {retcode}]"

        print("Use the following command to open the report:")
        color_print("OKGREEN", f"vizviewer {self.init_kwargs['output_file']}")

        return True, None

    def uninstall(self) -> VizProcedureResult:
        pid = self.options.uninstall

        if sys.platform == "win32":
            return False, "VizTracer does not support this feature on Windows"

        if not pid_exists(pid):
            return False, f"pid {pid} does not exist!"

        stop_code = "import viztracer.attach; viztracer.attach.uninstall_attach()"

        retcode, _, _ = run_python_code(pid, stop_code)
        if retcode != 0:  # pragma: no cover
            return False, f"Failed to inject code [err {retcode}]"

        return True, None

    def attach_installed(self) -> VizProcedureResult:
        if sys.platform == "win32":
            return False, "VizTracer does not support this feature on Windows"
        pid = self.options.attach_installed
        interval = self.options.t
        try:
            os.kill(pid, signal.SIGUSR1)
        except OSError:
            return False, f"pid {pid} does not exist"

        self._wait_attach(interval)

        try:
            os.kill(pid, signal.SIGUSR2)
        except OSError:  # pragma: no cover
            return False, f"pid {pid} already finished"

        return True, None

    def _wait_attach(self, interval) -> None:
        # interval == 0 means waiting for CTRL+C
        try:
            if interval > 0:
                print(f"Attach success, collect trace after {interval}s", flush=True)
                time.sleep(interval)
            else:
                print("Attach success, press CTRL+C to stop and save report", flush=True)
                while True:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            pass

    def save(self) -> None:
        # This function will only be called from main process
        options = self.options
        ofile = self.ofile
        if options.pid_suffix:
            prefix, suffix = os.path.splitext(self.ofile)
            prefix_pid = f"{prefix}_{os.getpid()}"
            ofile = prefix_pid + suffix
        else:
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
