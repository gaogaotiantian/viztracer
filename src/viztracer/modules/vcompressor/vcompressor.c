// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#include <Python.h>
#include "vcompressor.h"
#include "vc_dump.h"

static PyObject* 
vcompressor_new(PyTypeObject* type, PyObject* args, PyObject* kwargs)
{
    PyObject* self = PyType_GenericNew(type, args, kwargs);
    return (PyObject*)self;
}

static void 
vcompressor_dealloc(VcompressorObject* self)
{
    Py_TYPE(self)->tp_free((PyObject*) self);
}

static PyObject*
parse_trace_events(PyObject* trace_events)
{
    PyObject* parsed_events = NULL;
    PyObject* fee_events = NULL;
    PyObject* process_names = NULL;
    PyObject* thread_names = NULL;
    PyObject* key = NULL;

    if (!PyList_CheckExact(trace_events)) {
        return NULL;
    }

    // Initialize the event holder
    parsed_events = PyDict_New();
    fee_events = PyDict_New();
    process_names = PyDict_New();
    thread_names = PyDict_New();
    PyDict_SetItemString(parsed_events, "fee_events", fee_events);
    PyDict_SetItemString(parsed_events, "process_names", process_names);
    PyDict_SetItemString(parsed_events, "thread_names", thread_names);
    Py_DECREF(fee_events);
    Py_DECREF(process_names);
    Py_DECREF(thread_names);

    for (Py_ssize_t i = 0; i < PyList_GET_SIZE(trace_events); i++) {
        PyObject* event = PyList_GetItem(trace_events, i);
        PyObject* ph = NULL;
        PyObject* name = NULL;
        PyObject* args_name = NULL;
        PyObject* pid = NULL;
        PyObject* tid = NULL;
        PyObject* ts = NULL;
        PyObject* dur = NULL;
        PyObject* event_ts_list = NULL;
        if (PyErr_Occurred() || !PyDict_CheckExact(event)) {
            PyErr_SetString(PyExc_ValueError, "event format failure");
            goto clean_exit;
        }
        ph = PyDict_GetItemString(event, "ph");
        if (!ph || !PyUnicode_CheckExact(ph)) {
            PyErr_SetString(PyExc_ValueError, "event format failure");
            goto clean_exit;
        }
        switch (PyUnicode_AsUTF8(ph)[0]) {
            case 'X':
                name = PyDict_GetItemString(event, "name");
                ts = PyDict_GetItemString(event, "ts");
                dur = PyDict_GetItemString(event, "dur");
                pid = PyDict_GetItemString(event, "pid");
                tid = PyDict_GetItemString(event, "tid");
                if (!ts || !dur || !pid || !tid) {
                    PyErr_SetString(PyExc_ValueError, "event format failure");
                    goto clean_exit;
                }
                // Prepare the tuple key
                key = PyTuple_New(3);

                // PyTuple_SetItem steals reference
                Py_INCREF(pid);
                Py_INCREF(tid);
                Py_INCREF(name);
                PyTuple_SetItem(key, 0, pid);
                PyTuple_SetItem(key, 1, tid);
                PyTuple_SetItem(key, 2, name);

                if (!PyDict_Contains(fee_events, key)) {
                    event_ts_list = PyList_New(0);
                    PyDict_SetItem(fee_events, key, event_ts_list);
                    Py_DECREF(event_ts_list);
                } else {
                    event_ts_list = PyDict_GetItem(fee_events, key);
                }
                Py_DECREF(key);
                PyList_Append(event_ts_list, ts);
                PyList_Append(event_ts_list, dur);
                break;
            case 'M':
                name = PyDict_GetItemString(event, "name");
                pid = PyDict_GetItemString(event, "pid");
                tid = PyDict_GetItemString(event, "tid");
                if (!name || !pid || !tid) {
                    PyErr_SetString(PyExc_ValueError, "event format failure");
                    goto clean_exit;
                }
                args_name = PyDict_GetItemString(
                    PyDict_GetItemString(event, "args"),
                    "name"
                );
                PyObject* id_key = PyTuple_New(2);

                // PyTuple_SetItem steals reference
                Py_INCREF(pid);
                Py_INCREF(tid);
                PyTuple_SetItem(id_key, 0, pid);
                PyTuple_SetItem(id_key, 1, tid);

                if (PyUnicode_CompareWithASCIIString(name, "process_name") == 0) {
                    PyDict_SetItem(process_names, id_key, args_name);
                } else if (PyUnicode_CompareWithASCIIString(name, "thread_name") == 0) {
                    PyDict_SetItem(thread_names, id_key, args_name);
                } else {
                    PyErr_SetString(PyExc_ValueError, "event format failure");
                    Py_DECREF(id_key);
                    goto clean_exit;
                }
                Py_DECREF(id_key);
                break;
        }
    }

clean_exit:

    if (PyErr_Occurred()) {
        if (parsed_events) {
            Py_DECREF(parsed_events);
        }
        return NULL;
    }

    return parsed_events;
}

static PyObject* vcompressor_compress(VcompressorObject* self, PyObject* args)
{
    PyObject* raw_data = NULL;
    PyObject* trace_events = NULL;
    PyObject* parsed_events = NULL;
    PyObject* file_info = NULL;
    const char* filename = NULL;
    FILE* fptr = NULL;

    if (!PyArg_ParseTuple(args, "Os", &raw_data, &filename)) {
        PyErr_SetString(PyExc_ValueError, "Can't parse the argument correctly");
        goto clean_exit;
    }

    if (!PyDict_CheckExact(raw_data)) {
        PyErr_SetString(PyExc_ValueError, "You need to pass in a dict");
        goto clean_exit;
    }

    trace_events = PyDict_GetItemString(raw_data, "traceEvents");

    if (!trace_events || !PyList_CheckExact(trace_events)) {
        PyErr_SetString(PyExc_ValueError, "Unable to find traceEvents");
        goto clean_exit;
    }

    fptr = fopen(filename, "wb");
    if (!fptr) {
        PyErr_Format(PyExc_ValueError, "Can't open file %s to write", filename);
        goto clean_exit;
    }

    dump_metadata(fptr);

    parsed_events = parse_trace_events(trace_events);

    if (!parsed_events) {
        PyErr_SetString(PyExc_ValueError, "Unable to find traceEvents");
        goto clean_exit;
    } 
    Py_INCREF(parsed_events);

    dump_parsed_trace_events(parsed_events, fptr);

    
    file_info = PyDict_GetItemString(raw_data, "file_info");
    if(file_info != NULL){
        dump_file_info(file_info, fptr);
    }


clean_exit:

    if (parsed_events) {
        Py_DECREF(parsed_events);
    }

    if (fptr) {
        fclose(fptr);
    }

    if (PyErr_Occurred()) {
        return NULL;
    }

    return parsed_events;

    // Py_RETURN_NONE;
}
static PyObject*
vcompressor_decompress(VcompressorObject* self, PyObject* args) {
    PyObject* parsed_events = NULL;
    PyObject* file_info = NULL;
    const char* filename = NULL;
    FILE* fptr = NULL;

    if (!PyArg_ParseTuple(args, "s", &filename)) {
        return NULL;
    }

    fptr = fopen(filename, "rb");
    if (!fptr) {
        PyErr_Format(PyExc_ValueError, "Can't open file %s to write", filename);
        goto clean_exit;
    }

    parsed_events = load_events_from_file(fptr);

    file_info = load_file_info(fptr);
    if(file_info){
        PyDict_SetItemString(parsed_events, "file_info", file_info);
        Py_DECREF(file_info);
    }



clean_exit:

    if (fptr) {
        fclose(fptr);
    }

    if (PyErr_Occurred()) {
        if (parsed_events) {
            Py_DECREF(parsed_events);
        }

        Py_RETURN_NONE;
    }

    return parsed_events;
}


// ================================================================
// Python interface
// ================================================================

static PyMethodDef Vcompressor_methods[] = {
    {"compress", (PyCFunction)vcompressor_compress, METH_VARARGS, "compress function"},
    {"decompress", (PyCFunction)vcompressor_decompress, METH_VARARGS, "decompress function"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef compressormodule = {
    PyModuleDef_HEAD_INIT,
    "viztracer.vcompressor",
    NULL,
    -1,
    Vcompressor_methods
};

static PyTypeObject VcompressorType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "viztracer.Vcompressor",
    .tp_doc = "Vcompressor",
    .tp_basicsize = sizeof(VcompressorObject),
    .tp_itemsize = 0,
    .tp_dict = NULL,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = vcompressor_new,
    .tp_dealloc = (destructor) vcompressor_dealloc,
    .tp_methods = Vcompressor_methods
};

PyMODINIT_FUNC
PyInit_vcompressor(void) 
{
    // Tracer Module
    PyObject* m = NULL;

    if (PyType_Ready(&VcompressorType) < 0) {
        return NULL;
    }

    m = PyModule_Create(&compressormodule);

    if (!m) {
        return NULL;
    }

    Py_INCREF(&VcompressorType);

    if (PyModule_AddObject(m, "VCompressor", (PyObject*) &VcompressorType) < 0) {
        Py_DECREF(&VcompressorType);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}