# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import sys
import textwrap
from typing import Any, Callable, Dict, List, Sequence, Union

from .viztracer import VizTracer


def patch_subprocess(viz_args) -> None:

    def subprocess_init(self, args: Union[str, Sequence], **kwargs) -> None:
        if sys.version_info >= (3, 7):
            from collections.abc import Sequence
        else:
            from collections import Sequence

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

    import subprocess
    setattr(subprocess.Popen, "__originit__", subprocess.Popen.__init__)
    setattr(subprocess.Popen, "__init__", subprocess_init)


def patch_multiprocessing(tracer: VizTracer) -> None:

    # For fork process
    def func_after_fork(tracer: VizTracer):
        tracer.register_exit()

        tracer.clear()
        tracer._set_curr_stack_depth(1)

        if tracer._afterfork_cb:
            tracer._afterfork_cb(tracer, *tracer._afterfork_args, **tracer._afterfork_kwargs)

    from multiprocessing.util import register_after_fork  # type: ignore

    register_after_fork(tracer, func_after_fork)

    # For spawn process
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
                    patch_spawned_process({tracer.init_kwargs});
                    spawn_main(%s)
                    """)
            prog %= ', '.join('%s=%r' % item for item in kwds.items())
            opts = multiprocessing.util._args_from_interpreter_flags()
            return [multiprocessing.spawn._python_exe] + opts + ['-c', prog, '--multiprocessing-fork']  # type: ignore

    import multiprocessing.spawn
    multiprocessing.spawn.get_command_line = get_command_line


class SpawnProcess:
    def __init__(
            self,
            viztracer_kwargs: Dict[str, Any],
            target: Callable,
            args: List[Any],
            kwargs: Dict[str, Any]):
        self._viztracer_kwargs = viztracer_kwargs
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._exiting = False

    def run(self):
        import viztracer

        tracer = viztracer.VizTracer(**self._viztracer_kwargs)
        tracer.register_exit()
        tracer.start()
        self._run()


def patch_spawned_process(viztracer_kwargs: Dict[str, Any]):
    from multiprocessing import reduction, process  # type: ignore
    from multiprocessing.spawn import prepare
    import multiprocessing.spawn

    def _main_3839(fd, parent_sentinel):
        with os.fdopen(fd, 'rb', closefd=True) as from_parent:
            process.current_process()._inheriting = True
            try:
                preparation_data = reduction.pickle.load(from_parent)
                prepare(preparation_data)
                self = reduction.pickle.load(from_parent)
                sp = SpawnProcess(viztracer_kwargs, self._target, self._args, self._kwargs)
                sp._run = self.run
                self.run = sp.run
            finally:
                del process.current_process()._inheriting
        return self._bootstrap(parent_sentinel)

    def _main_3637(fd):
        with os.fdopen(fd, 'rb', closefd=True) as from_parent:
            process.current_process()._inheriting = True
            try:
                preparation_data = reduction.pickle.load(from_parent)
                prepare(preparation_data)
                self = reduction.pickle.load(from_parent)
                sp = SpawnProcess(viztracer_kwargs, self._target, self._args, self._kwargs)
                sp._run = self.run
                self.run = sp.run
            finally:
                del process.current_process()._inheriting
        return self._bootstrap()

    if sys.version_info >= (3, 8):
        multiprocessing.spawn._main = _main_3839  # type: ignore
    else:
        multiprocessing.spawn._main = _main_3637  # type: ignore
