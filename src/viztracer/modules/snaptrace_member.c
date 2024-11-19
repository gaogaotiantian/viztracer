// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#include "pythoncapi_compat.h"
#include "snaptrace.h"

extern PyObject* asyncio_module;
extern PyObject* asyncio_tasks_module;
extern PyObject* curr_task_getters[2];

// ================================================================
// Tracer members
// ================================================================

static int
Tracer_max_stack_depth_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "max_stack_depth must be an integer");
        return -1;
    }

    self->max_stack_depth = PyLong_AsLong(value);

    if (self->max_stack_depth >= 0) {
        SET_FLAG(self->check_flags, SNAPTRACE_MAX_STACK_DEPTH);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_MAX_STACK_DEPTH);
    }
    return 0;
}

static PyObject*
Tracer_max_stack_depth_getter(TracerObject* self, void* closure)
{
    return PyLong_FromLong(self->max_stack_depth);
}

static int
Tracer_include_files_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyList_Check(value) && value != Py_None) {
        PyErr_SetString(PyExc_TypeError, "include_files must be a list or None");
        return -1;
    }

    Py_XDECREF(self->include_files);
    if (value == Py_None || PyList_Size(value) == 0) {
        self->include_files = NULL;
        UNSET_FLAG(self->check_flags, SNAPTRACE_INCLUDE_FILES);
    } else {
        self->include_files = Py_NewRef(value);
        SET_FLAG(self->check_flags, SNAPTRACE_INCLUDE_FILES);
    }
    return 0;
}

static PyObject*
Tracer_include_files_getter(TracerObject* self, void* closure)
{
    if (self->include_files) {
        return Py_NewRef(self->include_files);
    } else {
        Py_RETURN_NONE;
    }
}

static int
Tracer_exclude_files_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyList_Check(value) && value != Py_None) {
        PyErr_SetString(PyExc_TypeError, "exclude_files must be a list or None");
        return -1;
    }

    Py_XDECREF(self->exclude_files);
    if (value == Py_None || PyList_Size(value) == 0) {
        self->exclude_files = NULL;
        UNSET_FLAG(self->check_flags, SNAPTRACE_EXCLUDE_FILES);
    } else {
        self->exclude_files = Py_NewRef(value);
        SET_FLAG(self->check_flags, SNAPTRACE_EXCLUDE_FILES);
    }
    return 0;
}

static PyObject*
Tracer_exclude_files_getter(TracerObject* self, void* closure)
{
    if (self->exclude_files) {
        return Py_NewRef(self->exclude_files);
    } else {
        Py_RETURN_NONE;
    }
}

static int
Tracer_ignore_c_function_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "ignore_c_function must be a boolean");
        return -1;
    }

    if (value == Py_True) {
        SET_FLAG(self->check_flags, SNAPTRACE_IGNORE_C_FUNCTION);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_IGNORE_C_FUNCTION);
    }
    return 0;
}

static PyObject*
Tracer_ignore_c_function_getter(TracerObject* self, void* closure)
{
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_IGNORE_C_FUNCTION)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static int
Tracer_ignore_frozen_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "ignore_frozen must be a boolean");
        return -1;
    }

    if (value == Py_True) {
        SET_FLAG(self->check_flags, SNAPTRACE_IGNORE_FROZEN);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_IGNORE_FROZEN);
    }
    return 0;
}

static PyObject*
Tracer_ignore_frozen_getter(TracerObject* self, void* closure)
{
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_IGNORE_FROZEN)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static int
Tracer_verbose_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "verbose must be an integer");
        return -1;
    }

    self->verbose = PyLong_AsLong(value);
    return 0;
}

static PyObject*
Tracer_verbose_getter(TracerObject* self, void* closure)
{
    return PyLong_FromLong(self->verbose);
}

static int
Tracer_lib_file_path_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyUnicode_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "lib_file_path must be a string");
        return -1;
    }

    // Obviously we need to copy the string here or it would fail on
    // MacOS + python3.8
    // The documentation did not say whether the value persists on "s"
    // so we should copy it anyway. 

    const char* lib_file_path = PyUnicode_AsUTF8(value);

    if (self->lib_file_path) {
        PyMem_FREE(self->lib_file_path);
    }
    self->lib_file_path = PyMem_Calloc((strlen(lib_file_path) + 1), sizeof(char));
    if (!self->lib_file_path) {
        PyErr_NoMemory();
        return -1;
    }
    strcpy(self->lib_file_path, lib_file_path);

    return 0;
}

static PyObject*
Tracer_lib_file_path_getter(TracerObject* self, void* closure)
{
    return PyUnicode_FromString(self->lib_file_path);
}

static int
Tracer_process_name_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (value == Py_None) {
        Py_CLEAR(self->process_name);
        return 0;
    }

    if (!PyUnicode_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "process_name must be a string");
        return -1;
    }

    Py_INCREF(value);
    Py_XSETREF(self->process_name, value);
    return 0;
}

static PyObject*
Tracer_process_name_getter(TracerObject* self, void* closure)
{
    if (self->process_name == NULL) {
        Py_RETURN_NONE;
    }
    return Py_NewRef(self->process_name);
}

static int
Tracer_min_duration_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (PyFloat_Check(value)) {
        self->min_duration = PyFloat_AsDouble(value);
    } else if (PyLong_Check(value)) {
        self->min_duration = PyLong_AsDouble(value);
    } else {
        PyErr_SetString(PyExc_TypeError, "min_duration must be a float or an integer");
        return -1;
    }

    if (self->min_duration < 0) {
        self->min_duration = 0;
    }

    // In Python code the default unit is us
    // Convert to ns which is what c Code uses
    self->min_duration *= 1000;

    return 0;
}

static PyObject*
Tracer_min_duration_getter(TracerObject* self, void* closure)
{
    return PyFloat_FromDouble(self->min_duration);
}

static int
Tracer_log_func_args_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "log_func_args must be a boolean");
        return -1;
    }

    if (value == Py_True) {
        SET_FLAG(self->check_flags, SNAPTRACE_LOG_FUNCTION_ARGS);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_LOG_FUNCTION_ARGS);
    }
    return 0;
}

static PyObject*
Tracer_log_func_args_getter(TracerObject* self, void* closure)
{
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_FUNCTION_ARGS)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static int
Tracer_log_func_retval_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "log_func_retval must be a boolean");
        return -1;
    }

    if (value == Py_True) {
        SET_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE);
    }
    return 0;
}

static PyObject*
Tracer_log_func_retval_getter(TracerObject* self, void* closure)
{
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static int
Tracer_log_async_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "log_async must be a boolean");
        return -1;
    }

    if (value == Py_True) {
        // Lazy import asyncio because it's slow
        if (asyncio_module == NULL) {
            asyncio_module = PyImport_ImportModule("asyncio");
            asyncio_tasks_module = PyImport_AddModule("asyncio.tasks");
            if (PyObject_HasAttrString(asyncio_tasks_module, "current_task")) {
                curr_task_getters[0] = PyObject_GetAttrString(asyncio_tasks_module, "current_task");
            }
        }
        SET_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC);
    }
    return 0;
}

static PyObject*
Tracer_log_async_getter(TracerObject* self, void* closure)
{
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static int
Tracer_trace_self_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (!PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "trace_self must be a boolean");
        return -1;
    }

    if (value == Py_True) {
        SET_FLAG(self->check_flags, SNAPTRACE_TRACE_SELF);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_TRACE_SELF);
    }
    return 0;
}

static PyObject*
Tracer_trace_self_getter(TracerObject* self, void* closure)
{
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_TRACE_SELF)) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static int
Tracer_log_func_repr_setter(TracerObject* self, PyObject* value, void* closure)
{
    if (value == NULL) {
        PyErr_SetString(PyExc_AttributeError, "Cannot delete the attribute");
        return -1;
    }

    if (value == Py_None) {
        Py_CLEAR(self->log_func_repr);
        return 0;
    }

    if (!PyCallable_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "log_func_repr must be a boolean");
        return -1;
    }

    Py_INCREF(value);
    Py_XSETREF(self->log_func_repr, value);

    return 0;
}

static PyObject*
Tracer_log_func_repr_getter(TracerObject* self, void* closure)
{
    if (self->log_func_repr == NULL) {
        Py_RETURN_NONE;
    }
    return Py_NewRef(self->log_func_repr);
}

PyGetSetDef Tracer_getsetters[] = {
    {"max_stack_depth", (getter)Tracer_max_stack_depth_getter, (setter)Tracer_max_stack_depth_setter, "max_stack_depth", NULL},
    {"include_files", (getter)Tracer_include_files_getter, (setter)Tracer_include_files_setter, "include_files", NULL},
    {"exclude_files", (getter)Tracer_exclude_files_getter, (setter)Tracer_exclude_files_setter, "exclude_files", NULL},
    {"ignore_c_function", (getter)Tracer_ignore_c_function_getter, (setter)Tracer_ignore_c_function_setter, "ignore_c_function", NULL},
    {"ignore_frozen", (getter)Tracer_ignore_frozen_getter, (setter)Tracer_ignore_frozen_setter, "ignore_frozen", NULL},
    {"verbose", (getter)Tracer_verbose_getter, (setter)Tracer_verbose_setter, "verbose", NULL},
    {"lib_file_path", (getter)Tracer_lib_file_path_getter, (setter)Tracer_lib_file_path_setter, "lib_file_path", NULL},
    {"process_name", (getter)Tracer_process_name_getter, (setter)Tracer_process_name_setter, "process_name", NULL},
    {"min_duration", (getter)Tracer_min_duration_getter, (setter)Tracer_min_duration_setter, "min_duration", NULL},
    {"log_func_retval", (getter)Tracer_log_func_retval_getter, (setter)Tracer_log_func_retval_setter, "log_func_retval", NULL},
    {"log_func_args", (getter)Tracer_log_func_args_getter, (setter)Tracer_log_func_args_setter, "log_func_args", NULL},
    {"log_async", (getter)Tracer_log_async_getter, (setter)Tracer_log_async_setter, "log_async", NULL},
    {"trace_self", (getter)Tracer_trace_self_getter, (setter)Tracer_trace_self_setter, "trace_self", NULL},
    {"log_func_repr", (getter)Tracer_log_func_repr_getter, (setter)Tracer_log_func_repr_setter, "log_func_repr", NULL},
    {NULL}
};
