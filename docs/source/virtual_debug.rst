Virtual Debug
=============

To use virtual debug, use ``vdb`` with your json report

.. code-block::

    vdb <your_json_report>

You can use the following commands in the interactive shell:

(They are very similar to pdb)

.. py:attribute:: s

    single step to next function entry/exit

.. py:attribute:: sb

    single step **back** to last function entry/exit

.. py:attribute:: n

    go to next function entry/exit without entering other function

.. py:attribute:: nb

    go to **last** function entry/exit without entering other function

.. py:attribute:: r

    go forward and return to the caller function

.. py:attribute:: r

    go backward and return to the caller function

.. py:attribute:: t [<timestamp>]

    if ``<timestamp>`` is not specified, display current timestamp, otherwise
    go to the time specified by ``<timestamp>``. ``<timestamp>`` has the unit of us.

.. py:attribute:: tid [<tid>]

    if ``<tid>`` is not specified, list the current thread ids in the current process, otherwise
    go to the thread at the current timestamp

.. py:attribute:: pid [<pid>]

    if ``<pid>`` is not specified, list the current process ids, otherwise
    go to the first spawned thread in the specified process at the current timestamp

.. py:attribute:: w

    list the call stack with ``>`` showing the current frame

.. py:attribute:: u

    go up a level to inspect the outer frame

.. py:attribute:: d

    go down a level to inspect the inner frame

.. py:attribute:: counter

    print the counter recorded at the current timestamp

.. py:attribute:: a, arg, args

    print the function args logged in VizTracer

.. py:attribute:: q, quit, exit

    exit the program
