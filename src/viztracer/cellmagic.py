# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

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
            assert self.shell is not None
            code = self.shell.transform_cell(cell)
            file_path = "./viztracer_report.json"
            with VizTracer(verbose=0, output_file=file_path):
                exec(code, local_ns, local_ns)

            def view():  # pragma: no cover
                server = ServerThread(file_path, once=True)
                server.start()
                server.ready.wait()
                import webbrowser
                webbrowser.open_new_tab(f'http://127.0.0.1:{server.port}')

            button = Button(description="VizTracer Report")
            button.on_click(lambda b: view())

            display(button)

except ImportError:  # pragma: no cover
    pass


def load_ipython_extension(ipython) -> None:
    """
    Use `%load_ext viztracer`
    """
    ipython.register_magics(VizTracerMagics)
