#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <frameobject.h>

int
snaptrace_tracefunc(PyObject *obj, PyFrameObject *frame, int what, PyObject *arg)
{
    if (what == PyTrace_CALL) {
        printf("Call\n");
    }

    return 0;
}

static PyObject*
snaptrace_start(PyObject* self, PyObject *args)
{
    PyEval_SetProfile(snaptrace_tracefunc, NULL);

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_stop(PyObject* self, PyObject *args)
{
    PyEval_SetProfile(NULL, NULL);
    
    Py_RETURN_NONE;
}

static PyMethodDef SnaptraceMethods[] = {
    {"start", snaptrace_start, METH_VARARGS, "start profiling"},
    {"stop", snaptrace_stop, METH_VARARGS, "stop profiling"}
};

static struct PyModuleDef snaptracemodule = {
    PyModuleDef_HEAD_INIT,
    "codesnap.snaptrace",
    NULL,
    -1,
    SnaptraceMethods
};

PyMODINIT_FUNC
PyInit_snaptrace(void) 
{
    return PyModule_Create(&snaptracemodule);
}