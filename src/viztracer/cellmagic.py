# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

try:
    from IPython.core.magic import cell_magic, magics_class, Magics, needs_local_scope  # type: ignore

    @magics_class
    class VizTracerMagics(Magics):
        @needs_local_scope
        @cell_magic
        def viztracer(self, line, cell, local_ns):
            from .viztracer import VizTracer
            from .viewer import view
            from IPython.display import display  # type: ignore
            from ipywidgets import Button  # type: ignore
            code = self.shell.transform_cell(cell)
            file_path = "./viztracer_report.json"
            with VizTracer(verbose=0, output_file=file_path):
                exec(code, local_ns, local_ns)

            button = Button(description="VizTracer Report")
            button.on_click(lambda b: view(file_path, once=True))

            display(button)

except ImportError:  # pragma: no cover
    pass


def load_ipython_extension(ipython):
    """
    Use `%load_ext viztracer`
    """
    ipython.register_magics(VizTracerMagics)
