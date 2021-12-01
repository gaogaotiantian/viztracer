// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#if _WIN32
#include <windows.h>
#endif
#include <Python.h>
#include <time.h>
#include "snaptrace.h"


#if _WIN32
LARGE_INTEGER qpc_freq;
#endif

// Utility functions

void Print_Py(PyObject* o)
{
    PyObject* repr = PyObject_Repr(o);
    printf("%s\n", PyUnicode_AsUTF8(repr));
    Py_DECREF(repr);
}

void fprintjson(FILE* fptr, PyObject* obj)
{
    PyObject* json_dumps = PyObject_GetAttrString(json_module, "dumps");
    PyObject* call_args = PyTuple_New(1);
    PyTuple_SetItem(call_args, 0, obj);
    PyObject* args_str = PyObject_CallObject(json_dumps, call_args);
    fprintf(fptr, "%s", PyUnicode_AsUTF8(args_str));
    Py_DECREF(json_dumps);
    Py_DECREF(call_args);
    Py_DECREF(args_str);
}

double get_ts(void)
{
    static double prev_ts = 0;
    double curr_ts = 0;

#if _WIN32
    LARGE_INTEGER counter = {0};
    QueryPerformanceCounter(&counter);
    curr_ts = (double) counter.QuadPart;
    curr_ts *= 1000000000LL;
    curr_ts /= qpc_freq.QuadPart;
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    curr_ts = ((double)t.tv_sec * 1e9 + t.tv_nsec);
#endif
    if (curr_ts <= prev_ts) {
        // We use artificial timestamp to avoid timestamp conflict.
        // 20 ns should be a safe granularity because that's normally
        // how long clock_gettime() takes.
        // It's possible to have three same timestamp in a row so we
        // need to check if curr_ts <= prev_ts instead of ==
        curr_ts = prev_ts + 20;
    }
    prev_ts = curr_ts;
    return curr_ts;
}
