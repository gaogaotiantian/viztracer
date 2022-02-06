# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import base64
import builtins
import gc
import json
import sys
from .util import get_tracer
from .viztracer import VizTracer


attach_status = {
    "created_tracer": False,
    "save_path": "",
    "attached": False
}


def start_attach(init_kwargs_b64: str):
    init_kwargs = json.loads(base64.urlsafe_b64decode(init_kwargs_b64.encode("ascii")).decode("ascii"))
    tracer = get_tracer()
    if tracer is None:
        attach_status["created_tracer"] = True
        tracer = VizTracer(**init_kwargs)
    elif tracer.enable:
        print("Can't attach when VizTracer is already running.", file=sys.stderr)
        return
    attach_status["attached"] = True
    attach_status["save_path"] = init_kwargs["output_file"]
    tracer.start()


def stop_attach():
    if attach_status["attached"]:
        tracer: VizTracer = get_tracer()
        tracer.stop()
        tracer.save(attach_status["save_path"])
        attach_status["attached"] = False
        if attach_status["created_tracer"]:
            tracer.stop()
            attach_status["created_tracer"] = False
            builtins.__dict__.pop("__viz_tracer__")
            gc.collect()
        attach_status["attached"] = False


def uninstall_attach():
    global attach_status
    attach_status = {
        "created_tracer": False,
        "save_path": "",
        "attached": False
    }
    tracer = get_tracer()
    if tracer:
        tracer.stop()
        tracer.clear()
        builtins.__dict__.pop("__viz_tracer__")
        gc.collect()
