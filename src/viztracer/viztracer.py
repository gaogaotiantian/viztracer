# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import multiprocessing
import builtins
from .tracer import _VizTracer
from .flamegraph import FlameGraph
from .report_builder import ReportBuilder
from .vizplugin import VizPluginManager


# This is the interface of the package. Almost all user should use this
# class for the functions
class VizTracer(_VizTracer):
    def __init__(self,
                 tracer_entries=1000000,
                 verbose=1,
                 max_stack_depth=-1,
                 include_files=None,
                 exclude_files=None,
                 ignore_c_function=False,
                 ignore_frozen=False,
                 log_func_retval=False,
                 log_func_args=False,
                 log_print=False,
                 log_gc=False,
                 log_sparse=False,
                 novdb=False,
                 pid_suffix=False,
                 file_info=False,
                 register_global=True,
                 output_file="result.html",
                 plugins=[]):
        super().__init__(
            tracer_entries=tracer_entries,
            max_stack_depth=max_stack_depth,
            include_files=include_files,
            exclude_files=exclude_files,
            ignore_c_function=ignore_c_function,
            ignore_frozen=ignore_frozen,
            log_func_retval=log_func_retval,
            log_print=log_print,
            log_gc=log_gc,
            novdb=novdb,
            log_func_args=log_func_args
        )
        self.verbose = verbose
        self.pid_suffix = pid_suffix
        self.file_info = file_info
        self.output_file = output_file
        self.system_print = None
        self.log_sparse = log_sparse
        if register_global:
            self.register_global()

        self._afterfork_cb = None
        self._afterfork_args = None
        self._afterfork_kwargs = None

        # load in plugins
        self._plugin_manager = VizPluginManager(self, plugins)

    @property
    def verbose(self):
        return self.__verbose

    @verbose.setter
    def verbose(self, verbose):
        if type(verbose) is str:
            try:
                self.__verbose = int(verbose)
            except ValueError:
                raise ValueError("Verbose needs to be an integer, not {}".format(verbose))
        elif type(verbose) is int:
            self.__verbose = verbose
        else:
            raise ValueError("Verbose needs to be an integer, not {}".format(verbose))

    @property
    def pid_suffix(self):
        return self.__pid_suffix

    @pid_suffix.setter
    def pid_suffix(self, pid_suffix):
        if type(pid_suffix) is bool:
            self.__pid_suffix = pid_suffix
        else:
            raise ValueError("pid_suffix needs to be a boolean, not {}".format(pid_suffix))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, trace):
        self.stop()
        if type is None:
            self.save()
        self.terminate()

    def register_global(self):
        builtins.__dict__["__viz_tracer__"] = self

    def set_afterfork(self, callback, *args, **kwargs):
        self._afterfork_cb = callback
        self._afterfork_args = args
        self._afterfork_kwargs = kwargs

    def start(self):
        if not self.enable:
            self._plugin_manager.event("pre-start")
            _VizTracer.start(self)

    def stop(self):
        if self.enable:
            _VizTracer.stop(self)
            self._plugin_manager.event("post-stop")

    def run(self, command, output_file=None):
        self.start()
        exec(command)
        self.stop()
        self.save(output_file)

    def save(self, output_file=None, save_flamegraph=False, file_info=None):
        if file_info is None:
            file_info = self.file_info
        enabled = False
        if self.enable:
            enabled = True
            self.stop()
        if not self.parsed:
            self.parse()
        if output_file is None:
            output_file = self.output_file
        if self.pid_suffix:
            output_file_parts = output_file.split(".")
            output_file_parts[-2] = output_file_parts[-2] + "_" + str(os.getpid())
            output_file = ".".join(output_file_parts)

        self._plugin_manager.event("pre-save")

        output_file = os.path.abspath(output_file)
        if not os.path.isdir(os.path.dirname(output_file)):
            os.makedirs(os.path.dirname(output_file), exist_ok=True)

        rb = ReportBuilder(self.data, self.verbose)
        rb.save(output_file=output_file, file_info=self.file_info)

        if save_flamegraph:
            self.save_flamegraph(".".join(output_file.split(".")[:-1]) + "_flamegraph.html")

        if enabled:
            self.start()

    def generate_json(self, allow_binary=False):
        rb = ReportBuilder(self.data, self.verbose)
        return rb.generate_json(allow_binary=allow_binary)

    def generate_report(self):
        rb = ReportBuilder(self.data, self.verbose)
        return rb.generate_report()

    def fork_save(self, output_file=None, save_flamegraph=False):
        if multiprocessing.get_start_method() != "fork":
            # You have to parse first if you are not forking, address space is not copied
            # Since it's not forking, we can't pickle tracer, just set it to None when
            # we spawn
            if not self.parsed:
                self.parse()
            tracer = self._tracer
            self._tracer = None
        else:
            # Fix the current pid so it won't give new pid when parsing
            self._tracer.setpid()

        p = multiprocessing.Process(target=self.save, daemon=False,
                                    kwargs={"output_file": os.path.abspath(output_file), "save_flamegraph": save_flamegraph})
        p.start()

        if multiprocessing.get_start_method() != "fork":
            self._tracer = tracer
        else:
            # Revert to the normal pid mode
            self._tracer.setpid(0)

    def save_flamegraph(self, output_file=None):
        flamegraph = FlameGraph(self.data)
        if output_file is None:
            name_list = self.output_file.split(".")
            output_file = ".".join(name_list[:-1]) + "_flamegraph." + name_list[-1]
        flamegraph.save(output_file)

    def terminate(self):
        self._plugin_manager.terminate()
