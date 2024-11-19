Installation
============

VizTracer works with python 3.9+ on Linux/MacOs/Windows. No other dependency. For now, VizTracer only supports CPython.

The preferred way to install VizTracer is via pip

.. code-block::

    pip install viztracer

You can also install with conda

.. code-block::

    conda install conda-forge::viztracer

    // Or if you already have conda forge set up
    conda install viztracer


You can also download the source code and build it yourself.

Even though VizTracer functions without any other packages,
``orjson`` could improve the performance of json dump/load.

.. code-block::

    pip install orjson

Or you can install *full* version of viztracer:

.. code-block::

    pip install viztracer[full]
