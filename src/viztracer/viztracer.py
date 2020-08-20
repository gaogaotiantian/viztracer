# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from .tracer import _VizTracer
from .flamegraph import FlameGraph


# This is the interface of the package. Almost all user should use this
# class for the functions
class VizTracer(_VizTracer):
    def __init__(self,
                 tracer="c",
                 verbose=1,
                 max_stack_depth=-1,
                 include_files=None,
                 exclude_files=None,
                 ignore_c_function=False,
                 log_print=False,
                 output_file="result.html"):
        super().__init__(
                tracer=tracer,
                max_stack_depth=max_stack_depth,
                include_files=include_files,
                exclude_files=exclude_files,
                ignore_c_function=ignore_c_function,
                log_print=log_print
        )
        self.verbose = verbose
        self.output_file = output_file
        self.system_print = None

    @property
    def verbose(self):
        return self.__verbose

    @verbose.setter
    def verbose(self, verbose):
        try:
            self.__verbose = int(verbose)
        except Exception as _:
            raise Exception("Verbose needs to be an integer, not {}".format(verbose))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, trace):
        self.stop()
        if type is None:
            self.save()

    def run(self, command, output_file=None):
        self.start()
        exec(command)
        self.stop()
        self.save(output_file)

    def save(self, output_file=None, save_flamegraph=False):
        if not self.parsed:
            self.parse()
        if output_file is None:
            output_file = self.output_file
        file_type = output_file.split(".")[-1]
        if file_type == "html":
            with open(output_file, "w") as f:
                f.write(self.generate_report())
        elif file_type == "json":
            with open(output_file, "w") as f:
                f.write(self.generate_json())
        else:
            raise Exception("Only html and json are supported")

        if save_flamegraph:
            self.save_flamegraph(".".join(output_file.split(".")[:-1]) + "_flamegraph.html")

    def save_flamegraph(self, output_file=None):
        flamegraph = FlameGraph(self.data)
        if output_file is None:
            name_list = self.output_file.split(".")
            output_file = ".".join(name_list[:-1]) + "_flamegraph." + name_list[-1]
        flamegraph.save(output_file)
