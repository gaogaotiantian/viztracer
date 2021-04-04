try:
    from IPython.core.magic import cell_magic, magics_class, Magics, needs_local_scope
    from IPython.display import display
    import ipywidgets

    @magics_class
    class VizTracerMagics(Magics):
        @needs_local_scope
        @cell_magic
        def viztracer(self, line, cell, local_ns):
            from .viztracer import VizTracer
            from .viewer import view
            code = self.shell.transform_cell(cell)
            file_path = "./viztracer_report.html"
            with VizTracer(verbose=0, output_file=file_path):
                exec(code, local_ns, local_ns)

            button = ipywidgets.Button(description="Show VizTracer Report")
            button.on_click(lambda b: view(file_path))

            display(button)

except ImportError:
    pass


def load_ipython_extension(ipython):
    """
    Use `%load_ext viztracer`
    """
    ipython.register_magics(VizTracerMagics)
