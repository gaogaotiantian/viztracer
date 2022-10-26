# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import functools
from multiprocessing import Process
import os
import re
import sys
import textwrap
from typing import Any, Callable, Dict, List, Sequence, Union

from .viztracer import VizTracer


def patch_subprocess(viz_args) -> None:
    import subprocess

    @functools.wraps(subprocess.Popen.__init__)
    def subprocess_init(self, args: Union[str, Sequence], **kwargs) -> None:
        from collections.abc import Sequence

        new_args: Union[str, Sequence[Any]] = args
        if isinstance(new_args, str):
            new_args = new_args.split()
        if isinstance(new_args, Sequence):
            new_args = list(new_args)
            if "python" in os.path.basename(new_args[0]):
                for py_arg in "bBdEhiIOqsSuvVx":
                    if f"-{py_arg}" in new_args:
                        new_args.remove(f"-{py_arg}")
                if "-c" in new_args:
                    # If python use -c mode, we move this to viztracer command
                    idx = new_args.index("-c")
                    viz_args.append(new_args.pop(idx))
                    viz_args.append(new_args.pop(idx))
                new_args = ["viztracer", "--quiet"] + viz_args + ["--"] + new_args[1:]
            else:
                new_args = args

        self.__originit__(new_args, **kwargs)

    # We need to filter the arguments as there are something we may not want
    if "-m" in viz_args:
        # If it's a module run, we don't want to use that module for subprocess
        idx = viz_args.index("-m")
        viz_args.pop(idx)
        viz_args.pop(idx)

    setattr(subprocess.Popen, "__originit__", subprocess.Popen.__init__)
    setattr(subprocess.Popen, "__init__", subprocess_init)


def patch_multiprocessing(tracer: VizTracer, args: List[str]) -> None:

    # For fork process
    def func_after_fork(tracer: VizTracer):
        tracer.register_exit()

        tracer.clear()
        tracer._set_curr_stack_depth(1)

        if tracer._afterfork_cb:
            tracer._afterfork_cb(tracer, *tracer._afterfork_args, **tracer._afterfork_kwargs)

    from multiprocessing.util import register_after_fork  # type: ignore
    import multiprocessing.spawn

    register_after_fork(tracer, func_after_fork)

    # For spawn process
    @functools.wraps(multiprocessing.spawn.get_command_line)
    def get_command_line(**kwds) -> List[str]:
        '''
        Returns prefix of command line used for spawning a child process
        '''
        if getattr(sys, 'frozen', False):  # pragma: no cover
            return ([sys.executable, '--multiprocessing-fork']
                    + ['%s=%r' % item for item in kwds.items()])
        else:
            prog = textwrap.dedent(f"""
                    from multiprocessing.spawn import spawn_main;
                    from viztracer.patch import patch_spawned_process;
                    patch_spawned_process({tracer.init_kwargs}, {args});
                    spawn_main(%s)
                    """)
            prog %= ', '.join('%s=%r' % item for item in kwds.items())
            opts = multiprocessing.util._args_from_interpreter_flags()  # type: ignore
            return [multiprocessing.spawn._python_exe] + opts + ['-c', prog, '--multiprocessing-fork']  # type: ignore

    multiprocessing.spawn.get_command_line = get_command_line


class SpawnProcess:
    def __init__(
            self,
            viztracer_kwargs: Dict[str, Any],
            run: Callable,
            target: Callable,
            args: List[Any],
            kwargs: Dict[str, Any],
            cmdline_args: List[str]):
        self._viztracer_kwargs = viztracer_kwargs
        self._run = run
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._cmdline_args = cmdline_args
        self._exiting = False

    def run(self) -> None:
        import viztracer

        tracer = viztracer.VizTracer(**self._viztracer_kwargs)
        install_all_hooks(tracer, self._cmdline_args)
        tracer.register_exit()
        tracer.start()
        self._run()


def patch_spawned_process(viztracer_kwargs: Dict[str, Any], cmdline_args: List[str]):
    from multiprocessing import reduction, process  # type: ignore
    from multiprocessing.spawn import prepare
    import multiprocessing.spawn

    @functools.wraps(multiprocessing.spawn._main)
    def _main_3839(fd, parent_sentinel):
        with os.fdopen(fd, 'rb', closefd=True) as from_parent:
            process.current_process()._inheriting = True
            try:
                preparation_data = reduction.pickle.load(from_parent)
                prepare(preparation_data)
                self: Process = reduction.pickle.load(from_parent)
                sp = SpawnProcess(viztracer_kwargs, self.run, self._target, self._args, self._kwargs, cmdline_args)
                self.run = sp.run
            finally:
                del process.current_process()._inheriting
        return self._bootstrap(parent_sentinel)

    @functools.wraps(multiprocessing.spawn._main)
    def _main_3637(fd):
        with os.fdopen(fd, 'rb', closefd=True) as from_parent:
            process.current_process()._inheriting = True
            try:
                preparation_data = reduction.pickle.load(from_parent)
                prepare(preparation_data)
                self: Process = reduction.pickle.load(from_parent)
                sp = SpawnProcess(viztracer_kwargs, self.run, self._target, self._args, self._kwargs, cmdline_args)
                self.run = sp.run
            finally:
                del process.current_process()._inheriting
        return self._bootstrap()

    if sys.version_info >= (3, 8):
        multiprocessing.spawn._main = _main_3839  # type: ignore
    else:
        multiprocessing.spawn._main = _main_3637  # type: ignore


def install_all_hooks(
        tracer: VizTracer,
        args: List[str],
        patch_multiprocess: bool = True) -> None:

    # multiprocess hook
    if patch_multiprocess:
        patch_multiprocessing(tracer, args)
        patch_subprocess(args + ["--subprocess_child", "--dump_raw", "-o", tracer.output_file])

    # If we want to hook fork correctly with file waiter, we need to
    # use os.register_at_fork to write the file, and make sure
    # os.exec won't clear viztracer so that the file lives forever.
    # This is basically equivalent to py3.8 + Linux
    if hasattr(sys, "addaudithook"):
        if hasattr(os, "register_at_fork") and patch_multiprocess:
            def audit_hook(event, _):  # pragma: no cover
                if event == "os.exec":
                    tracer.exit_routine()
            sys.addaudithook(audit_hook)  # type: ignore
            os.register_at_fork(after_in_child=lambda: tracer.label_file_to_write())  # type: ignore
        if tracer.log_audit is not None:
            audit_regex_list = [re.compile(regex) for regex in tracer.log_audit]

            def audit_hook(event, _):  # pragma: no cover
                if len(audit_regex_list) == 0 or any((regex.fullmatch(event) for regex in audit_regex_list)):
                    tracer.log_instant(event, args={"args": [str(arg) for arg in args]})
            sys.addaudithook(audit_hook)  # type: ignore
