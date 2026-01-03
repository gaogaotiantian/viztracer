# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

from __future__ import annotations

import functools
import multiprocessing.spawn
import multiprocessing.util
import os
import re
import shutil
import subprocess
import sys
import textwrap
import weakref
from multiprocessing import Process
from typing import TYPE_CHECKING, Any, Callable, Sequence, no_type_check

if TYPE_CHECKING:
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
        mode: list[str] | None = []
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
                    cm_arg = cm_arg or next(args_iter, None)
                    if cm_arg is not None:
                        if cm_arg.split(".")[0] == "viztracer":
                            # Avoid tracing viztracer subprocess
                            # This is mainly used to avoid tracing --open
                            return None
                        mode.append(cm_arg)
                    else:
                        mode = None
                break

            # -pyopts
            py_args.append(arg)
            if arg in ("-X", "-W", "--check-hash-based-pycs"):
                arg_next = next(args_iter, None)
                if arg_next is not None:
                    py_args.append(arg_next)
                else:
                    return None

        if script:
            return [
                sys.executable,
                *py_args,
                "-m",
                "viztracer",
                "--quiet",
                *viz_args,
                "--",
                script,
                *args_iter,
            ]
        elif mode:
            return [
                sys.executable,
                *py_args,
                "-m",
                "viztracer",
                "--quiet",
                *viz_args,
                *mode,
                "--",
                *args_iter,
            ]
        return None

    def is_python_entry(path: str) -> bool:
        real_path = shutil.which(path)
        if real_path is None:
            return False
        try:
            with open(real_path, "rb") as f:
                if f.read(2) == b"#!":
                    executable = f.readline().decode("utf-8").strip()
                    if "python" in executable.split("/")[-1]:
                        return True
        except Exception:  # pragma: no cover
            pass
        return False

    @functools.wraps(subprocess.Popen.__init__)
    def subprocess_init(
        self: subprocess.Popen[Any], args: str | Sequence[Any] | Any, **kwargs: Any
    ) -> None:
        new_args = args
        if isinstance(new_args, str):
            new_args = shlex.split(new_args, posix=sys.platform != "win32")
        if isinstance(new_args, Sequence):
            if "python" in os.path.basename(new_args[0]):
                new_args = build_command(new_args)
            elif is_python_entry(new_args[0]):
                new_args = [
                    "python",
                    "-m",
                    "viztracer",
                    "--quiet",
                    *viz_args,
                    "--",
                    *new_args,
                ]
            else:
                new_args = None
            if new_args is not None and kwargs.get("shell") and isinstance(args, str):
                # For shell=True, we should convert the commands back to string
                # if it was passed as string
                # This is mostly for Unix shell
                new_args = " ".join(new_args)

        if new_args is None:
            new_args = args
        assert hasattr(subprocess_init, "__wrapped__")  # for mypy
        subprocess_init.__wrapped__(self, new_args, **kwargs)

    setattr(subprocess.Popen, "__originit__", subprocess.Popen.__init__)
    setattr(subprocess.Popen, "__init__", subprocess_init)


def patch_multiprocessing(tracer: VizTracer, viz_args: list[str]) -> None:
    tracer_ref = weakref.ref(tracer)

    # For fork process
    def func_after_fork(tracer: VizTracer):
        # This is the callback specifically for multiprocessing
        # We have to re-register exit handler here because multiprocessing clears it
        # We also want to reset the stack so it believes the current frame is the root
        tracer.register_exit()
        tracer.clear()
        tracer.reset_stack()

        tracer.connect_report_server()

        if tracer._afterfork_cb:
            tracer._afterfork_cb(
                tracer, *tracer._afterfork_args, **tracer._afterfork_kwargs
            )

    from multiprocessing.util import register_after_fork  # type: ignore

    register_after_fork(tracer, func_after_fork)

    if sys.platform == "win32":
        # For spawn process on Windows
        @functools.wraps(multiprocessing.spawn.get_command_line)
        def get_command_line(**kwds) -> list[str]:
            """
            Returns prefix of command line used for spawning a child process
            """
            if getattr(sys, "frozen", False):  # pragma: no cover
                return [sys.executable, "--multiprocessing-fork"] + [
                    "%s=%r" % item for item in kwds.items()
                ]
            else:
                if (tracer := tracer_ref()) is None:
                    prog = (
                        "from multiprocessing.spawn import spawn_main; spawn_main(%s)"
                    )
                else:
                    prog = textwrap.dedent(f"""
                        from multiprocessing.spawn import spawn_main;
                        from viztracer.patch import patch_spawned_process;
                        patch_spawned_process({tracer.init_kwargs}, {viz_args});
                        spawn_main(%s)
                    """)
                prog %= ", ".join("%s=%r" % item for item in kwds.items())
                opts = multiprocessing.util._args_from_interpreter_flags()  # type: ignore
                return (
                    [multiprocessing.spawn._python_exe]
                    + opts
                    + ["-c", prog, "--multiprocessing-fork"]
                )  # type: ignore

        multiprocessing.spawn.get_command_line_orig = (
            multiprocessing.spawn.get_command_line
        )
        multiprocessing.spawn.get_command_line = get_command_line
    else:
        # POSIX
        # For forkserver process and spawned process
        # We patch spawnv_passfds to trace forkserver parent process so the forked
        # children can be traced
        _spawnv_passfds = multiprocessing.util.spawnv_passfds

        @functools.wraps(_spawnv_passfds)
        def spawnv_passfds(path, args, passfds):
            if "-c" in args:
                idx = args.index("-c")
                cmd = args[idx + 1]
                if "forkserver" in cmd:
                    # forkserver will not end before main process, avoid deadlock by --patch_only
                    args = (
                        args[:idx]
                        + ["-m", "viztracer", "--patch_only", *viz_args]
                        + args[idx:]
                    )
                elif "resource_tracker" not in cmd:
                    # We don't trace resource_tracker as it does not quit before the main process
                    # This is a normal spawned process. Only one of spawnv_passfds and spawn._main
                    # can be patched. forkserver process will use spawn._main after forking a child,
                    # so on POSIX we patch spawnv_passfds which has a similar effect on spawned processes.
                    args = args[:idx] + ["-m", "viztracer", *viz_args] + args[idx:]
            ret = _spawnv_passfds(path, args, passfds)
            return ret

        multiprocessing.util.spawnv_passfds_orig = multiprocessing.util.spawnv_passfds  # type: ignore
        multiprocessing.util.spawnv_passfds = spawnv_passfds  # type: ignore


class SpawnProcess:
    def __init__(
        self,
        viztracer_kwargs: dict[str, Any],
        run: Callable,
        target: Callable,
        args: list[Any],
        kwargs: dict[str, Any],
        cmdline_args: list[str],
    ):
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
        tracer.register_exit()
        tracer.start()
        self._run()


def patch_spawned_process(viztracer_kwargs: dict[str, Any], cmdline_args: list[str]):
    from multiprocessing import process, reduction  # type: ignore
    from multiprocessing.spawn import prepare

    @no_type_check
    @functools.wraps(multiprocessing.spawn._main)
    def _main(fd, parent_sentinel) -> Any:
        with os.fdopen(fd, "rb", closefd=True) as from_parent:
            process.current_process()._inheriting = True
            try:
                preparation_data = reduction.pickle.load(from_parent)
                prepare(preparation_data)
                self: Process = reduction.pickle.load(from_parent)
                sp = SpawnProcess(
                    viztracer_kwargs,
                    self.run,
                    self._target,
                    self._args,
                    self._kwargs,
                    cmdline_args,
                )
                self.run = sp.run
            finally:
                del process.current_process()._inheriting
        return self._bootstrap(parent_sentinel)

    multiprocessing.spawn._main_orig = multiprocessing.spawn._main  # type: ignore
    multiprocessing.spawn._main = _main  # type: ignore


class HookManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._tracer = None
            cls._installed = False
        return cls._instance

    def set_tracer(self, tracer: VizTracer | None) -> None:
        self._tracer = weakref.ref(tracer) if tracer is not None else None
        self.install_hooks()

    def install_hooks(self):
        if not self._installed:
            if hasattr(os, "register_at_fork"):
                os.register_at_fork(after_in_child=self._after_fork)
            sys.addaudithook(self._audit_callback)
            self._installed = True

    def _after_fork(self):
        if (
            self._tracer
            and (tracer := self._tracer())
            and not tracer.ignore_multiprocess
        ):
            if tracer.report_server_process is not None:
                tracer.report_server_process = None
            if tracer.report_socket_file is not None:
                # Reconnect to report server in the forked child process
                # otherwise it conflicts with the parent's connection
                tracer.connect_report_server()
            tracer.register_exit()
            tracer.start()

    def _audit_callback(self, event: str, args: Any) -> None:  # pragma: no cover
        if (
            self._tracer
            and (tracer := self._tracer())
            and not tracer.ignore_multiprocess
        ):
            if event == "os.exec":
                tracer.exit_routine()

            if tracer.log_audit is not None:
                audit_regex_list = [re.compile(regex) for regex in tracer.log_audit]
                if len(audit_regex_list) == 0 or any(
                    (regex.fullmatch(event) for regex in audit_regex_list)
                ):
                    tracer.log_instant(event, args={"args": [str(arg) for arg in args]})


def install_all_hooks(tracer: VizTracer) -> None:
    uninstall_all_hooks()

    args = tracer.get_args()

    # multiprocess hook
    if not tracer.ignore_multiprocess:
        patch_multiprocessing(tracer, args)
        patch_subprocess(args)

    HookManager().set_tracer(tracer)


def uninstall_all_hooks() -> None:
    HookManager().set_tracer(None)

    if hasattr(subprocess.Popen, "__originit__"):
        setattr(subprocess.Popen, "__init__", subprocess.Popen.__originit__)  # type: ignore
        delattr(subprocess.Popen, "__originit__")

    if hasattr(multiprocessing.spawn, "_main_orig"):
        setattr(multiprocessing.spawn, "_main", multiprocessing.spawn._main_orig)
        delattr(multiprocessing.spawn, "_main_orig")

    if hasattr(multiprocessing.spawn, "get_command_line_orig"):
        setattr(
            multiprocessing.spawn,
            "get_command_line",
            multiprocessing.spawn.get_command_line_orig,
        )
        delattr(multiprocessing.spawn, "get_command_line_orig")

    if hasattr(multiprocessing.util, "spawnv_passfds_orig"):
        setattr(
            multiprocessing.util,
            "spawnv_passfds",
            multiprocessing.util.spawnv_passfds_orig,
        )
        delattr(multiprocessing.util, "spawnv_passfds_orig")
