# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import os
import platform
import sys
import textwrap
from typing import Any, Callable, Dict, List, Sequence, Union

from .viztracer import VizTracer


def patch_subprocess(viz_args) -> None:

    def subprocess_init(self, args: Union[str, Sequence], **kwargs) -> None:
        if int(platform.python_version_tuple()[1]) >= 7:
            from collections.abc import Sequence
        else:
            from collections import Sequence
        if isinstance(args, str):
            args = args.split()
        if isinstance(args, Sequence):
            args = list(args)
            if "python" in os.path.basename(args[0]):
                args = ["viztracer", "--quiet"] + viz_args + ["--"] + args[1:]
        self.__originit__(args, **kwargs)

    import subprocess
    setattr(subprocess.Popen, "__originit__", subprocess.Popen.__init__)
    setattr(subprocess.Popen, "__init__", subprocess_init)


def patch_multiprocessing(tracer: VizTracer) -> None:

    # For fork process
    def func_after_fork(tracer: VizTracer):

        def exit_routine():
            tracer.exit_routine()

        from multiprocessing.util import Finalize  # type: ignore
        Finalize(tracer, exit_routine, exitpriority=32)

        tracer.register_exit()

        tracer.clear()
        tracer._set_curr_stack_depth(1)

        if tracer._afterfork_cb:
            tracer._afterfork_cb(tracer, *tracer._afterfork_args, **tracer._afterfork_kwargs)

    from multiprocessing.util import register_after_fork

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
        import atexit

        tracer = viztracer.VizTracer(**self._viztracer_kwargs)
        tracer.register_exit()
        tracer.start()
        self._run()
        atexit._run_exitfuncs()


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

    if int(platform.python_version_tuple()[1]) >= 8:
        multiprocessing.spawn._main = _main_3839  # type: ignore
    else:
        multiprocessing.spawn._main = _main_3637  # type: ignore
