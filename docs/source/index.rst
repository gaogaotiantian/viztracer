.. VizTracer documentation master file, created by
   sphinx-quickstart on Sun Aug 23 11:51:08 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Welcome to VizTracer's documentation!
=====================================

VizTracer is a deterministic debugging/profiling tool that can trace and visualize your python code to help you intuitively understand your code better and figure out the time consuming part of your code.

VizTracer can display every function executed and the corresponding entry/exit time from the beginning of the program to the end, which is helpful for programmers to catch sporatic performance issues. VizTracer is also capable of generating traditional flamegraph which is a good summary of the execution of the program

.. toctree::
   :maxdepth: 1
   :caption: Getting Started
   
   installation
   basic_usage
   advanced_usage
   limitations

.. toctree::
   :maxdepth: 1
   :caption: API Reference
   
   viztracer
   custom_event
   decorator
   multi_process
   virtual_debug 

.. toctree::
   :maxdepth: 1
   :caption: About
   
   contact
   license

