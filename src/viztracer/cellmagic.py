# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt
import re
import inspect

try:
    from IPython.core.magic import (Magics, cell_magic,  # type: ignore
                                    magics_class, needs_local_scope)

    @magics_class
    class VizTracerMagics(Magics):
        @needs_local_scope
        @cell_magic
        def viztracer(self, line, cell, local_ns) -> None:
            from IPython.display import display  # type: ignore
            from ipywidgets import Button  # type: ignore

            from .viewer import ServerThread
            from .viztracer import VizTracer
            tracer_kwargs, viewer_kwargs = self.make_kwargs(
                line, inspect.signature(VizTracer), inspect.signature(ServerThread)
            )
            code = self.shell.transform_cell(cell)
            with VizTracer(**tracer_kwargs):
                exec(code, local_ns, local_ns)

            def view():  # pragma: no cover
                server = ServerThread(**viewer_kwargs)
                server.start()
                server.ready.wait()
                import webbrowser
                webbrowser.open_new_tab(f'http://127.0.0.1:{server.port}')

            button = Button(description="VizTracer Report")
            button.on_click(lambda b: view())

            display(button)

        def make_kwargs(self, line, tracer_signature, viewer_signature):
            line = line.split('#')[0]
            pattern = r'(\w+=\w+)\s'
            default_path = "./viztracer_report.json"

            tracer_kwargs = {'verbose': 0, 'output_file': default_path}
            viewer_kwargs = {'path': default_path, 'once': True}

            for item in re.split(pattern, line):
                if item == '':
                    continue
                name, value = item.split('=')
                if name == 'output_file':
                    tracer_kwargs['output_file'] = value
                    viewer_kwargs['path'] = value
                elif name in viewer_signature.parameters:
                    annotation = viewer_signature.parameters[name].annotation
                    kwargs = viewer_kwargs
                elif name in tracer_signature.parameters:
                    annotation = tracer_signature.parameters[name].annotation
                    kwargs = tracer_kwargs
                else:
                    raise ValueError(f'{name} is not a parameter of VizTracer or ServerThread')

                if value == 'None':
                    kwargs[name] = None
                else:
                    kwargs[name] = annotation(value)
            return tracer_kwargs, viewer_kwargs

except ImportError:  # pragma: no cover
    pass


def load_ipython_extension(ipython) -> None:
    """
    Use `%load_ext viztracer`
    """
    ipython.register_magics(VizTracerMagics)
