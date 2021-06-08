# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .viztracer import VizTracer
import os
import platform
import sys
import textwrap
from typing import Any, Callable, Dict, List, Sequence, Union


def patch_subprocess(ui) -> None:

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
                args = ["viztracer"] + ui.args + ["--"] + args[1:]
        self.__originit__(args, **kwargs)

    import subprocess
    setattr(subprocess.Popen, "__originit__", subprocess.Popen.__init__)
    setattr(subprocess.Popen, "__init__", subprocess_init)


def patch_multiprocessing(ui, tracer: VizTracer) -> None:

    # For fork process
    def func_after_fork(tracer: VizTracer):

        def exit_routine():
            ui.exit_routine()

        from multiprocessing.util import Finalize  # type: ignore
        import signal
        Finalize(tracer, exit_routine, exitpriority=32)

        def term_handler(signalnum, frame):
            ui.exit_routine()
        signal.signal(signal.SIGTERM, term_handler)

        tracer.clear()
        tracer._set_curr_stack_depth(1)

        if tracer._afterfork_cb:
            tracer._afterfork_cb(tracer, *tracer._afterfork_args, **tracer._afterfork_kwargs)

    from multiprocessing.util import register_after_fork

    tracer.pid_suffix = True
    tracer.output_file = os.path.join(ui.multiprocess_output_dir, "result.json")
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
                    patch_spawned_process({ui.init_kwargs}, '{ui.multiprocess_output_dir}');
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
            multiprocess_output_dir: str,
            target: Callable,
            args: List[Any],
            kwargs: Dict[str, Any]):
        self._viztracer_kwargs = viztracer_kwargs
        self._multiprocess_output_dir = multiprocess_output_dir
        self._target = target
        self._args = args
        self._kwargs = kwargs
        self._exiting = False

    def run(self):
        import os
        import viztracer
        import signal
        import atexit

        def exit_routine() -> None:
            tracer = viztracer.get_tracer()
            if tracer is not None:
                tracer.stop()
                atexit.unregister(exit_routine)
                if not self._exiting:
                    self._exiting = True
                    tracer.save()
                    tracer.terminate()
                    exit(0)

        def term_handler(signalnum, frame):
            exit_routine()

        atexit.register(exit_routine)
        signal.signal(signal.SIGTERM, term_handler)

        tracer = viztracer.VizTracer(**self._viztracer_kwargs)
        tracer.start()
        tracer.pid_suffix = True
        tracer.output_file = os.path.join(self._multiprocess_output_dir, "result.json")
        self._run()
        atexit._run_exitfuncs()


def patch_spawned_process(viztracer_kwargs: Dict[str, Any], multiprocess_output_dir: str):
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
                sp = SpawnProcess(viztracer_kwargs, multiprocess_output_dir, self._target, self._args, self._kwargs)
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
                sp = SpawnProcess(viztracer_kwargs, multiprocess_output_dir, self._target, self._args, self._kwargs)
                sp._run = self.run
                self.run = sp.run
            finally:
                del process.current_process()._inheriting
        return self._bootstrap()

    if int(platform.python_version_tuple()[1]) >= 8:
        multiprocessing.spawn._main = _main_3839  # type: ignore
    else:
        multiprocessing.spawn._main = _main_3637  # type: ignore
