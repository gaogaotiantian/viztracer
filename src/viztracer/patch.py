# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from __future__ import annotations

import functools
import os
import re
import sys
import textwrap
from multiprocessing import Process
from typing import Any, Callable, Dict, List, Sequence, Union, no_type_check

from .viztracer import VizTracer


def patch_subprocess(viz_args: list[str]) -> None:
    import shlex
    import subprocess

    # Try to detect the end of the python argument list and parse out various invocation patterns:
    # `file.py args` | - args | `-- file.py args` | `-cprint(5) args` | `-Esm mod args`
    py_arg_pat = re.compile("([^-].+)|-$|(--)$|-([a-z]+)?(c|m)(.+)?", re.IGNORECASE)
    # Note: viztracer doesn't really work in interactive mode and arg handling is weird.
    # Unlikely to be used in practice anyway so we just skip wrapping interactive python processes.
    interactive_pat = re.compile("-[A-Za-z]*?i[A-Za-z]*$")

    def build_command(args: Sequence[str]) -> list[str] | None:
        py_args: list[str] = []
        mode = []
        script = None
        args_iter = iter(args[1:])
        for arg in args_iter:
            if interactive_pat.match(arg):
                return None

            match = py_arg_pat.match(arg)
            if match:
                file, ddash, cm_py_args, cm, cm_arg = match.groups()
                if file:
                    # file.py [script args]
                    script = file
                elif ddash:
                    # -- file.py [script args]
                    script = next(args_iter, None)
                elif cm:
                    # -m mod [script args]
                    if cm_py_args:
                        # "-[pyopts]m"
                        py_args.append(f"-{cm_py_args}")
                    mode = [f"-{cm}"]
                    # -m mod | -mmod
                    mode.append(cm_arg or next(args_iter, None))
                break

            # -pyopts
            py_args.append(arg)

        if script:
            return [sys.executable, *py_args, "-m", "viztracer", "--quiet", *viz_args, "--", script, *args_iter]
        elif mode and mode[-1] is not None:
            return [sys.executable, *py_args, "-m", "viztracer", "--quiet", *viz_args, *mode, "--", *args_iter]
        return None

    @functools.wraps(subprocess.Popen.__init__)
    def subprocess_init(self: subprocess.Popen[Any], args: Union[str, Sequence[Any], Any], **kwargs: Any) -> None:
        new_args = args
        if isinstance(new_args, str):
            new_args = shlex.split(new_args)
        if isinstance(new_args, Sequence):
            if "python" in os.path.basename(new_args[0]):
                new_args = build_command(new_args)
            else:
                new_args = None

        if new_args is None:
            new_args = args
        assert hasattr(subprocess_init, "__wrapped__")  # for mypy
        subprocess_init.__wrapped__(self, new_args, **kwargs)

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

    import multiprocessing.spawn
    from multiprocessing.util import register_after_fork  # type: ignore

    register_after_fork(tracer, func_after_fork)

    # For spawn process
    @functools.wraps(multiprocessing.spawn.get_command_line)
    def get_command_line(**kwds) -> List[str]:
        """
        Returns prefix of command line used for spawning a child process
        """
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
    import multiprocessing.spawn
    from multiprocessing import process, reduction  # type: ignore
    from multiprocessing.spawn import prepare

    @no_type_check
    @functools.wraps(multiprocessing.spawn._main)
    def _main(fd, parent_sentinel) -> Any:
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

    multiprocessing.spawn._main = _main  # type: ignore


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
