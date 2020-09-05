Installation
============

VizTracer requires python 3.6+ and can work on Linux/MacOs/Windows. No other dependency. For now, VizTracer only supports CPython.

The prefered way to install VizTracer is via pip

.. code-block::

    pip install viztracer


You can also download the source code and build it yourself.

Even though VizTracer functions without any other packages, it is still recommended to install the following packages to have a better performance.

* orjson: better json dump/load performance
* rich: better interactive shell for vdb

.. code-block::

    pip install orjson rich

Or you can install *full* version of viztracer:

.. code-block::

    pip install viztracer[full]