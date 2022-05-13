// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#include <Python.h>
#include <time.h>
#include "snaptrace.h"


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
