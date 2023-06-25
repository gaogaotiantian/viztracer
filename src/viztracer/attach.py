# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import base64
import builtins
import gc
import json
import sys
from dataclasses import dataclass

from .viztracer import VizTracer, get_tracer


@dataclass
class AttachStatus:
    created_tracer: bool
    save_path: str
    attached: bool


attach_status = AttachStatus(created_tracer=False, save_path="", attached=False)


def start_attach(init_kwargs_b64: str) -> None:
    init_kwargs = json.loads(base64.urlsafe_b64decode(init_kwargs_b64.encode("ascii")).decode("ascii"))
    tracer = get_tracer()
    if tracer is None:
        attach_status.created_tracer = True
        tracer = VizTracer(**init_kwargs)
    elif tracer.enable:
        print("Can't attach when VizTracer is already running.", file=sys.stderr)
        return
    attach_status.attached = True
    attach_status.save_path = init_kwargs["output_file"]
    if tracer.verbose > 0:
        print("Detected attaching viztracer, start tracing.", flush=True)
    tracer.start()


def stop_attach() -> None:
    if attach_status.attached:
        tracer = get_tracer()
        if tracer:
            tracer.stop()
            tracer.save(attach_status.save_path)
            if tracer.verbose > 0:
                print(f"Saved report to {attach_status.save_path}", flush=True)
            attach_status.attached = False
            if attach_status.created_tracer:
                tracer.stop()
                attach_status.created_tracer = False
                builtins.__dict__.pop("__viz_tracer__")
                gc.collect()
        attach_status.attached = False


def uninstall_attach():
    attach_status.created_tracer = False
    attach_status.save_path = ""
    attach_status.attached = False
    tracer = get_tracer()
    if tracer:
        tracer.stop()
        tracer.clear()
        builtins.__dict__.pop("__viz_tracer__")
        gc.collect()
