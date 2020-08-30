// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#define PY_SSIZE_T_CLEAN
#include <stdlib.h>
#include <Python.h>
#include <frameobject.h>
#include <time.h>
#if _WIN32
#include <windows.h>
#elif __APPLE
#include <pthread.h>
#else
#include <pthread.h>
#include <sys/syscall.h>
#endif

#include "snaptrace.h"

// Function declarations

int snaptrace_tracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg);
static PyObject* snaptrace_threadtracefunc(PyObject* obj, PyObject* args);
static PyObject* snaptrace_start(TracerObject* self, PyObject* args);
static PyObject* snaptrace_stop(TracerObject* self, PyObject* args);
static PyObject* snaptrace_pause(PyObject* self, PyObject* args);
static PyObject* snaptrace_resume(PyObject* self, PyObject* args);
static PyObject* snaptrace_load(TracerObject* self, PyObject* args);
static PyObject* snaptrace_clear(TracerObject* self, PyObject* args);
static PyObject* snaptrace_cleanup(TracerObject* self, PyObject* args);
static PyObject* snaptrace_setpid(TracerObject* self, PyObject* args);
static PyObject* snaptrace_config(TracerObject* self, PyObject* args, PyObject* kw);
static PyObject* snaptrace_addinstant(TracerObject* self, PyObject* args);
static PyObject* snaptrace_addcounter(TracerObject* self, PyObject* args);
static PyObject* snaptrace_addobject(TracerObject* self, PyObject* args);
static void snaptrace_threaddestructor(void* key);
static struct ThreadInfo* snaptrace_createthreadinfo(TracerObject* self);

TracerObject* curr_tracer = NULL;
PyObject* thread_module = NULL;

#if _WIN32
LARGE_INTEGER qpc_freq; 
#endif

// Utility functions

static void Print_Py(PyObject* o)
{
    printf("%s\n", PyUnicode_AsUTF8(PyObject_Repr(o)));
}

static struct ThreadInfo* get_thread_info(TracerObject* self)
{
    struct ThreadInfo* info = NULL;
#if _WIN32
    info = TlsGetValue(self->dwTlsIndex);
#else
    info = pthread_getspecific(self->thread_key);
#endif
    return info;
}

static inline double get_ts()
{
#if _WIN32
    LARGE_INTEGER counter = {0};
    QueryPerformanceCounter(&counter);
    counter.QuadPart *= 1000000000LL;
    counter.QuadPart /= qpc_freq.QuadPart;
    return (double) counter.QuadPart;
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return ((double)t.tv_sec * 1e9 + t.tv_nsec);
#endif
}

static inline struct EventNode* get_next_node(TracerObject* self)
{
    struct EventNode* node = NULL;

    if (self->buffer_tail->next) {
        node = self->buffer_tail->next;
    } else {
        node = (struct EventNode*)PyMem_Calloc(1, sizeof(struct EventNode));
        if (!node) {
            printf("Out of memory!\n");
            exit(1);
        }
        node->next = NULL;
        self->buffer_tail->next = node;
        node->prev = self->buffer_tail;
    }
    self->buffer_tail = node;

    return node;
}

static void verbose_printf(TracerObject* self, int v, const char* fmt, ...)
{
    va_list args;
    if (self->verbose >= v) {
        va_start(args, fmt);
        vprintf(fmt, args);
        va_end(args);
        fflush(stdout);
    }
}

// target and prefix has to be NULL-terminated
static inline int startswith(const char* target, const char* prefix)
{
    while(*target != 0 && *prefix != 0) {
#if _WIN32
        // Windows path has double slashes and case-insensitive
        if (*prefix == '\\' && prefix[-1] == '\\') {
            prefix++;
        }
        if (*target == '\\' && target[-1] == '\\') {
            target++;
        }
        if (*target != *prefix && *target != *prefix - ('a'-'A') && *target != *prefix + ('a'-'A')) {
            return 0;
        }
#else
        if (*target != *prefix) {
            return 0;
        }
#endif
        target++;
        prefix++;
    }

    return (*prefix) == 0;
}

static PyMethodDef Tracer_methods[] = {
    {"threadtracefunc", (PyCFunction)snaptrace_threadtracefunc, METH_VARARGS, "trace function"},
    {"start", (PyCFunction)snaptrace_start, METH_VARARGS, "start profiling"},
    {"stop", (PyCFunction)snaptrace_stop, METH_VARARGS, "stop profiling"},
    {"load", (PyCFunction)snaptrace_load, METH_VARARGS, "load buffer"},
    {"clear", (PyCFunction)snaptrace_clear, METH_VARARGS, "clear buffer"},
    {"cleanup", (PyCFunction)snaptrace_cleanup, METH_VARARGS, "free the memory allocated"},
    {"setpid", (PyCFunction)snaptrace_setpid, METH_VARARGS, "set fixed pid"},
    {"config", (PyCFunction)snaptrace_config, METH_VARARGS|METH_KEYWORDS, "config the snaptrace module"},
    {"addinstant", (PyCFunction)snaptrace_addinstant, METH_VARARGS, "add instant event"},
    {"addcounter", (PyCFunction)snaptrace_addcounter, METH_VARARGS, "add counter event"},
    {"addobject", (PyCFunction)snaptrace_addobject, METH_VARARGS, "add object event"},
    {NULL, NULL, 0, NULL}
};

static PyMethodDef Snaptrace_methods[] = {
    {"pause", (PyCFunction)snaptrace_pause, METH_VARARGS, "pause profiling"},
    {"resume", (PyCFunction)snaptrace_resume, METH_VARARGS, "resume profiling"},
    {NULL, NULL, 0, NULL}
};

// ================================================================
// Python interface
// ================================================================

static struct PyModuleDef snaptracemodule = {
    PyModuleDef_HEAD_INIT,
    "viztracer.snaptrace",
    NULL,
    -1,
    Snaptrace_methods
};

// =============================================================================
// Tracing function, triggered when FEE
// =============================================================================

int
snaptrace_tracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg)
{
    TracerObject* self = (TracerObject*) obj;
    if (what == PyTrace_CALL || what == PyTrace_RETURN || 
            (!CHECK_FLAG(self->check_flags, SNAPTRACE_IGNORE_C_FUNCTION) && (what == PyTrace_C_CALL || what == PyTrace_C_RETURN || what == PyTrace_C_EXCEPTION))) {
        struct EventNode* node = NULL;
        struct ThreadInfo* info = get_thread_info(self);

        int is_call = (what == PyTrace_CALL || what == PyTrace_C_CALL);
        int is_return = (what == PyTrace_RETURN || what == PyTrace_C_RETURN || what == PyTrace_C_EXCEPTION);
        int is_python = (what == PyTrace_CALL || what == PyTrace_RETURN);
        int is_c = (what == PyTrace_C_CALL || what == PyTrace_C_RETURN || what == PyTrace_C_EXCEPTION);

        if (info->paused) {
            return 0;
        }

        if (info->ignore_stack_depth > 0) {
            if (is_call) {
                info->ignore_stack_depth += 1;
                return 0;
            } else if (is_return) {
                info->ignore_stack_depth -= 1;
                return 0;
            }
        }

        if (!info->stack_top && is_return) {
            return 0;
        }

        // Exclude Self
        if (is_c && is_call) {
            PyCFunctionObject* func = (PyCFunctionObject*) arg;
            if (func->m_module) {
                if (startswith(PyUnicode_AsUTF8(func->m_module), snaptracemodule.m_name)) {
                    info->ignore_stack_depth += 1;
                    return 0;
                }
            }
        } else if (is_python && is_call) {
            PyObject* file_name = frame->f_code->co_filename;
            if (self->lib_file_path && startswith(PyUnicode_AsUTF8(file_name), self->lib_file_path)) {
                info->ignore_stack_depth += 1;
                return 0;
            }
        }

        // Check max stack depth
        if (CHECK_FLAG(self->check_flags, SNAPTRACE_MAX_STACK_DEPTH)) {
            if (is_call) {
                info->curr_stack_depth += 1;
                if (info->curr_stack_depth > self->max_stack_depth) {
                    return 0;
                }
            } else if (is_return) {
                info->curr_stack_depth -= 1;
                if (info->curr_stack_depth + 1 > self->max_stack_depth) {
                    return 0;
                }
            }
        }

        // Check include/exclude files
        if (CHECK_FLAG(self->check_flags, SNAPTRACE_INCLUDE_FILES | SNAPTRACE_EXCLUDE_FILES)) {
            if (info->ignore_stack_depth == 0) {
                PyObject* files = NULL;
                int record = 0;
                int is_include = CHECK_FLAG(self->check_flags, SNAPTRACE_INCLUDE_FILES);
                if (is_include) {
                    files = self->include_files;
                    record = 0;
                } else {
                    files = self->exclude_files;
                    record = 1;
                }
                Py_ssize_t length = PyList_GET_SIZE(files);
                PyObject* name = frame->f_code->co_filename;
                for (int i = 0; i < length; i++) {
                    PyObject* f = PyList_GET_ITEM(files, i);
                    if (startswith(PyUnicode_AsUTF8(name), PyUnicode_AsUTF8(f))) {
                        record = 1 - record;
                        break;
                    }
                }
                if (record == 0) {
                    info->ignore_stack_depth += 1;
                    return 0;
                }
            } else {
                return 0;
            }
        }

        if (is_call) {
            // If it's a call, we need a new node, and we need to update the stack
            node = get_next_node(self);
            node->ntype = FEE_NODE;
            node->ts = get_ts();
            node->data.fee.dur = 0;
            node->data.fee.parent = info->stack_top;
            info->stack_top = node;
            node->data.fee.type = what;
            node->tid = info->tid;
            if (what == PyTrace_CALL) {
                node->data.fee.file_name = frame->f_code->co_filename;
                Py_INCREF(node->data.fee.file_name);
                node->data.fee.first_lineno = frame->f_code->co_firstlineno;
                node->data.fee.func_name = frame->f_code->co_name;
                Py_INCREF(node->data.fee.func_name);
            } else if (what == PyTrace_C_CALL) {
                PyCFunctionObject* func = (PyCFunctionObject*) arg;
                node->data.fee.func_name = PyUnicode_FromString(func->m_ml->ml_name);
                if (func->m_module) {
                    node->data.fee.file_name = func->m_module;
                    Py_INCREF(node->data.fee.file_name);
                } else {
                    node->data.fee.file_name = PyUnicode_FromString(func->m_self->ob_type->tp_name);
                }
            } 
        } else if (is_return) {
            struct EventNode* stack_top = info->stack_top;
            if (stack_top) {
                stack_top->data.fee.dur = get_ts() - stack_top->ts;
                info->stack_top = stack_top->data.fee.parent;
                if (is_python && CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE)) {
                    stack_top->data.fee.args = PyObject_Repr(arg);
                }
            } else {
                printf("return out of stack\n");
            }
            return 0;
        } else {
            printf("Unexpected event!\n");
        }
        self->total_entries += 1;
    }

    return 0;
}

static PyObject* snaptrace_threadtracefunc(PyObject* obj, PyObject* args) 
{
    PyFrameObject* frame = NULL;
    char* event = NULL;
    PyObject* trace_args = NULL;
    int what = 0;
    if (!PyArg_ParseTuple(args, "OsO", &frame, &event, &trace_args)) {
        printf("Error when parsing arguments!\n");
        exit(1);
    }
    snaptrace_createthreadinfo((TracerObject*) obj);
    PyEval_SetProfile(snaptrace_tracefunc, obj);
    if (!strcmp(event, "call")) {
        what = PyTrace_CALL;
    } else if (!strcmp(event, "c_call")) {
        what = PyTrace_C_CALL;
    } else if (!strcmp(event, "return")) {
        what = PyTrace_RETURN;
    } else if (!strcmp(event, "c_return")) {
        what = PyTrace_C_RETURN;
    } else {
        printf("Unexpected event type: %s\n", event);
    }
    snaptrace_tracefunc(obj, frame, what, trace_args);
    Py_RETURN_NONE;
}

// =============================================================================
// Control interface with python
// =============================================================================

static PyObject*
snaptrace_start(TracerObject* self, PyObject* args)
{
    if (curr_tracer) {
        printf("Warning! Overwrite tracer! You should not have two VizTracer recording at the same time!\n");
    } else {
        curr_tracer = self;
    }
    // Python: threading.setprofile(tracefunc)
    {
        PyObject* threading = PyImport_ImportModule("threading");
        assert(threading != NULL);
        PyObject* setprofile = PyObject_GetAttrString(threading, "setprofile");

        PyObject* handler = PyCFunction_New(&Tracer_methods[0], (PyObject*)self);
        PyObject* callback = Py_BuildValue("(O)", handler);

        if (PyObject_CallObject(setprofile, callback) == NULL) {
            perror("Failed to call threading.setprofile() properly");
            exit(-1);
        }
    }
    PyEval_SetProfile(snaptrace_tracefunc, (PyObject*)self);

    self->collecting = 1;

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_stop(TracerObject* self, PyObject* args)
{
    PyEval_SetProfile(NULL, NULL);
    curr_tracer = NULL;
    if (self->collecting == 1) {
        struct ThreadInfo* info = get_thread_info(self);
        snaptrace_threaddestructor(info);
    }
    
    Py_RETURN_NONE;
}

static PyObject*
snaptrace_pause(PyObject* self, PyObject* args)
{
    if (curr_tracer->collecting) {
        struct ThreadInfo* info = get_thread_info(curr_tracer);
        if (info) {
            info->paused += 1;
        }
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_resume(PyObject* self, PyObject* args)
{
    if (curr_tracer->collecting) {
        struct ThreadInfo* info = get_thread_info(curr_tracer);
        if (info && info->paused > 0) {
            info->paused -= 1;
        }
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_load(TracerObject* self, PyObject* args)
{
    PyObject* lst = PyList_New(0);
    struct EventNode* curr = self->buffer_head;
    PyObject* pid = NULL;
    PyObject* cat_fee = PyUnicode_FromString("FEE");
    PyObject* cat_instant = PyUnicode_FromString("INSTANT");
    PyObject* ph_B = PyUnicode_FromString("B");
    PyObject* ph_E = PyUnicode_FromString("E");
    PyObject* ph_I = PyUnicode_FromString("I");
    PyObject* ph_X = PyUnicode_FromString("X");
    PyObject* ph_C = PyUnicode_FromString("C");
    unsigned long counter = 0;
    unsigned long prev_counter = 0;

    if (self->fix_pid > 0) {
        pid = PyLong_FromLong(self->fix_pid);
    } else {
#if _WIN32
        pid = PyLong_FromLong(GetCurrentProcessId());
#else
        pid = PyLong_FromLong(getpid());
#endif
    }

    while (curr != self->buffer_tail && curr->next) {
        struct EventNode* node = curr->next;
        PyObject* dict = PyDict_New();
        PyObject* name = NULL;
        PyObject* tid = PyLong_FromLong(node->tid);
        PyObject* ts = PyFloat_FromDouble(node->ts / 1000);

        PyDict_SetItemString(dict, "pid", pid);
        PyDict_SetItemString(dict, "tid", tid);
        Py_DECREF(tid);
        PyDict_SetItemString(dict, "ts", ts);
        Py_DECREF(ts);

        switch (node->ntype) {
        case FEE_NODE:
            if (node->data.fee.type == PyTrace_CALL || node->data.fee.type == PyTrace_RETURN) {
                name = PyUnicode_FromFormat("%s(%d).%s", 
                       PyUnicode_AsUTF8(node->data.fee.file_name),
                       node->data.fee.first_lineno,
                       PyUnicode_AsUTF8(node->data.fee.func_name));
                Py_DECREF(node->data.fee.file_name);
                Py_DECREF(node->data.fee.func_name);
            } else {
                name = PyUnicode_FromFormat("%s.%s", 
                       PyUnicode_AsUTF8(node->data.fee.file_name),
                       PyUnicode_AsUTF8(node->data.fee.func_name));
                Py_DECREF(node->data.fee.file_name);
                Py_DECREF(node->data.fee.func_name);
            }

            PyObject* dur = PyFloat_FromDouble(node->data.fee.dur / 1000);
            PyDict_SetItemString(dict, "dur", dur);
            Py_DECREF(dur);
            PyDict_SetItemString(dict, "name", name);
            Py_DECREF(name);
            if (node->data.fee.args) {
                PyObject* arg_dict = PyDict_New();
                PyDict_SetItemString(arg_dict, "return_value", node->data.fee.args);
                Py_DECREF(node->data.fee.args);
                PyDict_SetItemString(dict, "args", arg_dict);
                Py_DECREF(arg_dict);
            }

            switch (node->data.fee.type) {
                case PyTrace_CALL:
                case PyTrace_C_CALL:
                    // Entry
                    PyDict_SetItemString(dict, "ph", ph_X);
                    break;
                case PyTrace_RETURN:
                case PyTrace_C_RETURN:
                case PyTrace_C_EXCEPTION:
                    //Exit
                    PyDict_SetItemString(dict, "ph", ph_E);
                    break;
                default:
                    printf("Unknown Type!\n");
                    exit(1);
            }
            PyDict_SetItemString(dict, "cat", cat_fee);
            break;
        case INSTANT_NODE:
            PyDict_SetItemString(dict, "ph", ph_I);
            PyDict_SetItemString(dict, "cat", cat_instant);
            PyDict_SetItemString(dict, "name", node->data.instant.name);
            PyDict_SetItemString(dict, "args", node->data.instant.args);
            PyDict_SetItemString(dict, "s", node->data.instant.scope);
            Py_DECREF(node->data.instant.name);
            Py_DECREF(node->data.instant.args);
            Py_DECREF(node->data.instant.scope);
            break;
        case COUNTER_NODE:
            PyDict_SetItemString(dict, "ph", ph_C);
            PyDict_SetItemString(dict, "name", node->data.counter.name);
            PyDict_SetItemString(dict, "args", node->data.counter.args);
            Py_DECREF(node->data.counter.name);
            Py_DECREF(node->data.counter.args);
            break;
        case OBJECT_NODE:
            PyDict_SetItemString(dict, "ph", node->data.object.ph);
            PyDict_SetItemString(dict, "id", node->data.object.id);
            PyDict_SetItemString(dict, "name", node->data.object.name);
            if (!(node->data.object.args == Py_None)) {
                PyDict_SetItemString(dict, "args", node->data.object.args);
            }
            Py_DECREF(node->data.object.ph);
            Py_DECREF(node->data.object.id);
            Py_DECREF(node->data.object.name);
            Py_DECREF(node->data.object.args);
            break;
        default:
            printf("Unknown Node Type!\n");
            exit(1);
        }
        PyList_Append(lst, dict);
        curr = curr->next;

        counter += 1;
        if (counter - prev_counter > 10000 && (counter - prev_counter) / ((1 + self->total_entries)/100) > 0) {
            verbose_printf(self, 1, "Loading data, %lu / %lu\r", counter, self->total_entries);
            prev_counter = counter;
        }
    }
    verbose_printf(self, 1, "Loading finish                                        \n");
    Py_DECREF(pid);
    Py_DECREF(cat_fee);
    Py_DECREF(cat_instant);
    Py_DECREF(ph_B);
    Py_DECREF(ph_E);
    Py_DECREF(ph_I);
    Py_DECREF(ph_X);
    Py_DECREF(ph_C);
    self->buffer_tail = self->buffer_head;
    return lst;
}

static PyObject*
snaptrace_clear(TracerObject* self, PyObject* args)
{
    struct EventNode* curr = self->buffer_head;
    while (curr != self->buffer_tail && curr->next) {
        struct EventNode* node = curr->next;
        switch (node->ntype) {
        case FEE_NODE:
            if (node->data.fee.type == PyTrace_C_CALL || 
                    node->data.fee.type == PyTrace_C_RETURN || 
                    node->data.fee.type == PyTrace_C_EXCEPTION) {
                Py_DECREF(node->data.fee.func_name);
            } else {
                Py_DECREF(node->data.fee.file_name);
                Py_DECREF(node->data.fee.func_name);
            }
            if (node->data.fee.args) {
                Py_DECREF(node->data.fee.args);
                node->data.fee.args = NULL;
            }
            break;
        case INSTANT_NODE:
            Py_DECREF(node->data.instant.name);
            Py_DECREF(node->data.instant.args);
            Py_DECREF(node->data.instant.scope);
            break;
        case COUNTER_NODE:
            Py_DECREF(node->data.counter.name);
            Py_DECREF(node->data.counter.args);
            break;
        case OBJECT_NODE:
            Py_DECREF(node->data.object.ph);
            Py_DECREF(node->data.object.id);
            Py_DECREF(node->data.object.name);
            Py_DECREF(node->data.object.args);
            break;
        default:
            printf("Unknown Node Type!\n");
            exit(1);
        }
        curr = curr->next;
    }
    self->buffer_tail = self->buffer_head;

    Py_RETURN_NONE;
}

static PyObject* 
snaptrace_cleanup(TracerObject* self, PyObject* args)
{
    snaptrace_clear(self, args);
    while (self->buffer_head->next) {
        struct EventNode* node = self->buffer_head->next;
        self->buffer_head->next = node->next;
        PyMem_FREE(node);
    } 
    Py_RETURN_NONE;
}

static PyObject* 
snaptrace_setpid(TracerObject* self, PyObject* args)
{
    long input_pid = -1;
    if (!PyArg_ParseTuple(args, "|l", &input_pid)) {
        printf("Parsing error on setpid\n");
    }

    if (input_pid >= 0) {
        self->fix_pid = input_pid;
    } else {
#if _WIN32
        self->fix_pid = GetCurrentProcessId();
#else
        self->fix_pid = getpid();
#endif
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_config(TracerObject* self, PyObject* args, PyObject* kw)
{
    static char* kwlist[] = {"verbose", "lib_file_path", "max_stack_depth", 
            "include_files", "exclude_files", "ignore_c_function", "log_return_value",
            NULL};
    int kw_verbose = -1;
    int kw_max_stack_depth = 0;
    char* kw_lib_file_path = NULL;
    PyObject* kw_include_files = NULL;
    PyObject* kw_exclude_files = NULL;
    int kw_ignore_c_function = -1;
    int kw_log_return_value = -1;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "|isiOOpp", kwlist, 
            &kw_verbose,
            &kw_lib_file_path,
            &kw_max_stack_depth,
            &kw_include_files,
            &kw_exclude_files,
            &kw_ignore_c_function,
            &kw_log_return_value)) {
        return NULL;
    }

    if (kw_verbose >= 0) {
        self->verbose = kw_verbose;
    }

    if (kw_lib_file_path) {
        // Obviously we need to copy the string here or it would fail on
        // MacOS + python3.8
        // The documentation did not say whether the value persists on "s"
        // so we should copy it anyway. 
        if (self->lib_file_path) {
            PyMem_FREE(self->lib_file_path);
        }
        self->lib_file_path = PyMem_Calloc((strlen(kw_lib_file_path) + 1), sizeof(char));
        if (!self->lib_file_path) {
            printf("Out of memory!\n");
            exit(1);
        }
        strcpy(self->lib_file_path, kw_lib_file_path);
    }

    if (kw_ignore_c_function == 1) {
        SET_FLAG(self->check_flags, SNAPTRACE_IGNORE_C_FUNCTION);
    } else if (kw_ignore_c_function == 0) {
        UNSET_FLAG(self->check_flags, SNAPTRACE_IGNORE_C_FUNCTION);
    }

    if (kw_log_return_value == 1) {
        SET_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE);
    } else if (kw_log_return_value == 0) {
        UNSET_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE);
    }

    if (kw_max_stack_depth >= 0) {
        SET_FLAG(self->check_flags, SNAPTRACE_MAX_STACK_DEPTH);       
        self->max_stack_depth = kw_max_stack_depth;
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_MAX_STACK_DEPTH);
    }

    if (kw_include_files && kw_include_files != Py_None) {
        if (self->include_files) {
            Py_DECREF(self->include_files);
        }
        self->include_files = kw_include_files;
        Py_INCREF(self->include_files);
        SET_FLAG(self->check_flags, SNAPTRACE_INCLUDE_FILES);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_INCLUDE_FILES);
    }

    if (kw_exclude_files && kw_exclude_files != Py_None) {
        if (self->exclude_files) {
            Py_DECREF(self->exclude_files);
        }
        self->exclude_files = kw_exclude_files;
        Py_INCREF(self->exclude_files);
        SET_FLAG(self->check_flags, SNAPTRACE_EXCLUDE_FILES);
    } else {
        UNSET_FLAG(self->check_flags, SNAPTRACE_EXCLUDE_FILES);
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_addinstant(TracerObject* self, PyObject* args)
{
    PyObject* name = NULL;
    PyObject* instant_args = NULL;
    PyObject* scope = NULL;
    struct ThreadInfo* info = get_thread_info(self);
    struct EventNode* node = NULL;
    if (!PyArg_ParseTuple(args, "OOO", &name, &instant_args, &scope)) {
        printf("Error when parsing arguments!\n");
        exit(1);
    }

    node = get_next_node(self);
    node->ntype = INSTANT_NODE;
    node->tid = info->tid;
    node->ts = get_ts();
    node->data.instant.name = name;
    node->data.instant.args = instant_args;
    node->data.instant.scope = scope;
    Py_INCREF(name);
    Py_INCREF(args);
    Py_INCREF(scope);

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_addcounter(TracerObject* self, PyObject* args)
{
    PyObject* name = NULL;
    PyObject* counter_args = NULL;
    struct ThreadInfo* info = get_thread_info(self);
    struct EventNode* node = NULL;
    if (!PyArg_ParseTuple(args, "OO", &name, &counter_args)) {
        printf("Error when parsing arguments!\n");
        exit(1);
    }

    node = get_next_node(self);
    node->ntype = COUNTER_NODE;
    node->tid = info->tid;
    node->ts = get_ts();
    node->data.counter.name = name;
    node->data.counter.args = counter_args;
    Py_INCREF(name);
    Py_INCREF(args);

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_addobject(TracerObject* self, PyObject* args)
{
    PyObject* ph = NULL;
    PyObject* id = NULL;
    PyObject* name = NULL;
    PyObject* object_args = NULL;
    struct ThreadInfo* info = get_thread_info(self);
    struct EventNode* node = NULL;
    if (!PyArg_ParseTuple(args, "OOOO", &ph, &id, &name, &object_args)) {
        printf("Error when parsing arguments!\n");
        exit(1);
    }

    node = get_next_node(self);
    node->ntype = OBJECT_NODE;
    node->tid = info->tid;
    node->ts = get_ts();
    node->data.object.ph = ph;
    node->data.object.id = id;
    node->data.object.name = name;
    node->data.object.args = object_args;
    Py_INCREF(ph);
    Py_INCREF(id);
    Py_INCREF(name);
    Py_INCREF(args);

    Py_RETURN_NONE;
}

static struct ThreadInfo* snaptrace_createthreadinfo(TracerObject* self) {
    struct ThreadInfo* info = calloc(1, sizeof(struct ThreadInfo));

#if _WIN32  
    info->tid = GetCurrentThreadId();
#elif __APPLE__
    info->tid = pthread_threadid_np(NULL, NULL);
#else
    info->tid = syscall(SYS_gettid);
#endif

#if _WIN32
    TlsSetValue(self->dwTlsIndex, info);
#else
    pthread_setspecific(self->thread_key, info);
#endif

    return info;
}

static void snaptrace_threaddestructor(void* key) {
    struct ThreadInfo* info = key;
    if (info) {
        info->paused = 0;
        info->curr_stack_depth = 0;
        info->ignore_stack_depth = 0;
        info->tid = 0;
        info->stack_top = NULL;
    }
}

// ===========================================================================
// Tracer stuff 
// ===========================================================================
static PyObject* 
Tracer_New(PyTypeObject* type, PyObject* args, PyObject* kwargs)
{
    TracerObject* self = (TracerObject*) type->tp_alloc(type, 0);
    if (self) {
#if _WIN32
        if ((self->dwTlsIndex = TlsAlloc()) == TLS_OUT_OF_INDEXES) {
            printf("Error on TLS!\n");
            exit(-1);
        }
        QueryPerformanceFrequency(&qpc_freq); 
#else
        if (pthread_key_create(&self->thread_key, snaptrace_threaddestructor)) {
            perror("Failed to create Tss_Key");
            exit(-1);
        }
#endif
        snaptrace_createthreadinfo(self);
        self->collecting = 0;
        self->fix_pid = 0;
        self->total_entries = 0;
        self->check_flags = 0;
        self->verbose = 0;
        self->lib_file_path = NULL;
        self->max_stack_depth = 0;
        self->include_files = NULL;
        self->exclude_files = NULL;
        self->buffer_head = (struct EventNode*) PyMem_Malloc (sizeof(struct EventNode));
        if (!self->buffer_head) {
            printf("Out of memory!\n");
            exit(1);
        }
        self->buffer_head->ntype = EVENT_NODE;
        self->buffer_head->next = NULL;
        self->buffer_head->prev = NULL;
        self->buffer_tail = self->buffer_head; 
    }

    return (PyObject*) self;
}

static void
Tracer_dealloc(TracerObject* self)
{
    snaptrace_cleanup(self, NULL);
    if (self->lib_file_path) {
        PyMem_FREE(self->lib_file_path);
    }
    if (self->include_files) {
        Py_DECREF(self->include_files);
    }
    if (self->exclude_files) {
        Py_DECREF(self->exclude_files);
    }
    Py_DECREF(self->buffer_head);
    Py_TYPE(self)->tp_free((PyObject*) self);
}

static PyTypeObject TracerType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "viztracer.Tracer",
    .tp_doc = "Tracer",
    .tp_basicsize = sizeof(TracerObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_new = Tracer_New,
    .tp_dealloc = (destructor) Tracer_dealloc,
    .tp_methods = Tracer_methods
};

PyMODINIT_FUNC
PyInit_snaptrace(void) 
{
    // Tracer Module
    PyObject* m = NULL;

    if (PyType_Ready(&TracerType) < 0) {
        return NULL;
    }

    m = PyModule_Create(&snaptracemodule);

    if (!m) {
        return NULL;
    }

    Py_INCREF(&TracerType);
    if (PyModule_AddObject(m, "Tracer", (PyObject*) &TracerType) < 0) {
        Py_DECREF(&TracerType);
        Py_DECREF(m);
        return NULL;
    }

    thread_module = PyImport_ImportModule("threading");

    return m;
}