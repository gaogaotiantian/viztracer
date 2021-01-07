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
int snaptrace_tracefuncdisabled(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg);
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
static PyObject* snaptrace_addraw(TracerObject* self, PyObject* args);
static PyObject* snaptrace_addfunctionarg(TracerObject* self, PyObject* args);
static PyObject* snaptrace_getfunctionarg(TracerObject* self, PyObject* args);
static PyObject* snaptrace_getts(TracerObject* self, PyObject* args);
static PyObject* snaptrace_setcurrstack(TracerObject* self, PyObject* args);
static void snaptrace_threaddestructor(void* key);
static struct ThreadInfo* snaptrace_createthreadinfo(TracerObject* self);
static void log_func_args(struct FunctionNode* node, PyFrameObject* frame);

TracerObject* curr_tracer = NULL;
PyObject* threading_module = NULL;
PyObject* multiprocessing_module = NULL;

#if _WIN32
LARGE_INTEGER qpc_freq; 
#endif

// Utility functions

static void Print_Py(PyObject* o)
{
    PyObject* repr = PyObject_Repr(o);
    printf("%s\n", PyUnicode_AsUTF8(repr));
    Py_DECREF(repr);
}

static struct ThreadInfo* get_thread_info(TracerObject* self)
{
    struct ThreadInfo* info = NULL;

    if (!self) {
        return NULL;
    }
#if _WIN32
    info = TlsGetValue(self->dwTlsIndex);
#else
    info = pthread_getspecific(self->thread_key);
#endif
    return info;
}

static inline double get_ts()
{
    static double prev_ts = 0;
    double curr_ts = 0;

#if _WIN32
    LARGE_INTEGER counter = {0};
    QueryPerformanceCounter(&counter);
    counter.QuadPart *= 1000000000LL;
    counter.QuadPart /= qpc_freq.QuadPart;
    curr_ts = (double) counter.QuadPart;
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    curr_ts = ((double)t.tv_sec * 1e9 + t.tv_nsec);
#endif
    if (curr_ts == prev_ts) {
        curr_ts += 20;
    }
    prev_ts = curr_ts;
    return curr_ts;
}

static inline void clear_node(struct EventNode* node) {
    switch (node->ntype) {
    case FEE_NODE:
        if (node->data.fee.type == PyTrace_CALL || node->data.fee.type == PyTrace_RETURN) {
            Py_DECREF(node->data.fee.co_filename);
            Py_DECREF(node->data.fee.co_name);
            node->data.fee.co_firstlineno = 0;
            if (node->data.fee.args) {
                Py_DECREF(node->data.fee.args);
                node->data.fee.args = NULL;
            }
            if (node->data.fee.retval) {
                Py_DECREF(node->data.fee.retval);
                node->data.fee.retval = NULL;
            }
        } else {
            node->data.fee.ml_name = NULL;
            if (node->data.fee.m_module) {
                // The function belongs to a module
                Py_DECREF(node->data.fee.m_module);
                node->data.fee.m_module = NULL;
            } else {
                // The function is a class method
                if (node->data.fee.tp_name) {
                    // It's not a static method, has __self__
                    node->data.fee.tp_name = NULL;
                }
            }
        }
        break;
    case INSTANT_NODE:
        Py_DECREF(node->data.instant.name);
        Py_DECREF(node->data.instant.args);
        Py_DECREF(node->data.instant.scope);
        node->data.instant.name = NULL;
        node->data.instant.args = NULL;
        node->data.instant.scope = NULL;
        break;
    case COUNTER_NODE:
        Py_DECREF(node->data.counter.name);
        Py_DECREF(node->data.counter.args);
        node->data.counter.name = NULL;
        node->data.counter.args = NULL;
        break;
    case OBJECT_NODE:
        Py_DECREF(node->data.object.ph);
        Py_DECREF(node->data.object.id);
        Py_DECREF(node->data.object.name);
        Py_DECREF(node->data.object.args);
        node->data.object.ph = NULL;
        node->data.object.id = NULL;
        node->data.object.name = NULL;
        node->data.object.args = NULL;
        break;
    case RAW_NODE:
        Py_DECREF(node->data.raw);
        node->data.raw = NULL;
        break;
    default:
        printf("Unknown Node Type When Clearing!\n");
        exit(1);
    }
}

static inline struct EventNode* get_next_node(TracerObject* self)
{
    struct EventNode* node = NULL;

    node = self->buffer + self->buffer_tail_idx;
    self->buffer_tail_idx = (self->buffer_tail_idx + 1) % self->buffer_size;
    if (self->buffer_tail_idx == self->buffer_head_idx) {
        self->buffer_head_idx = (self->buffer_head_idx + 1) % self->buffer_size;
        clear_node(self->buffer + self->buffer_tail_idx);
    } else {
        self->total_entries += 1;
    }

    return node;
}

static void log_func_args(struct FunctionNode* node, PyFrameObject* frame)
{
    PyObject* func_arg_dict = PyDict_New();
    PyCodeObject* code = frame->f_code;
    PyObject* names = code->co_varnames;
    PyObject* locals = PyEval_GetLocals();

    int idx = 0;
    if (!node->args) {
        node->args = PyDict_New();
    }

    int name_length = code->co_argcount + code->co_kwonlyargcount;
    if (code->co_flags & CO_VARARGS) {
        name_length ++;
    }

    if (code->co_flags & CO_VARKEYWORDS) {
        name_length ++;
    }

    while (idx < name_length) {
        // Borrowed
        PyObject* name = PyTuple_GET_ITEM(names, idx);
        // New
        PyObject* repr = PyObject_Repr(PyDict_GetItem(locals, name));
        if (!repr) {
            repr = PyUnicode_FromString("Not Displayable");
            PyErr_Clear();
        }
        PyDict_SetItem(func_arg_dict, name, repr);
        Py_DECREF(repr);
        idx++;
    }

    PyDict_SetItemString(node->args, "func_args", func_arg_dict);
    Py_DECREF(func_arg_dict);
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

void clear_stack(struct FunctionNode** stack_top) {
    if ((*stack_top)->args) {
        Py_DECREF((*stack_top)->args);
        (*stack_top)->args = NULL;
    }
    while ((*stack_top)->prev) {
        (*stack_top) = (*stack_top) -> prev;
        if ((*stack_top)->args) {
            Py_DECREF((*stack_top)->args);
            (*stack_top)->args = NULL;
        }
    }
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
    {"addraw", (PyCFunction)snaptrace_addraw, METH_VARARGS, "add raw event"},
    {"addfunctionarg", (PyCFunction)snaptrace_addfunctionarg, METH_VARARGS, "add function arg"},
    {"getfunctionarg", (PyCFunction)snaptrace_getfunctionarg, METH_VARARGS, "get current function arg"},
    {"getts", (PyCFunction)snaptrace_getts, METH_VARARGS, "get timestamp"},
    {"setcurrstack", (PyCFunction)snaptrace_setcurrstack, METH_VARARGS, "set current stack depth"},
    {"pause", (PyCFunction)snaptrace_pause, METH_VARARGS, "pause profiling"},
    {"resume", (PyCFunction)snaptrace_resume, METH_VARARGS, "resume profiling"},
    {NULL, NULL, 0, NULL}
};

static PyMethodDef Snaptrace_methods[] = {
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
snaptrace_tracefuncdisabled(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg)
{
    TracerObject* self = (TracerObject*) obj;
    if (self->collecting) {
        PyEval_SetProfile(snaptrace_tracefunc, obj);
        return snaptrace_tracefunc(obj, frame, what, arg);
    }
    return 0;
}

int
snaptrace_tracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg)
{
    TracerObject* self = (TracerObject*) obj;
    if (!self->collecting) {
        PyEval_SetProfile(snaptrace_tracefuncdisabled, obj);
        return 0;
    }
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

        // Exclude Self
        if (is_python && is_call) {
            PyObject* file_name = frame->f_code->co_filename;
            if (self->lib_file_path && startswith(PyUnicode_AsUTF8(file_name), self->lib_file_path)) {
                info->ignore_stack_depth += 1;
                return 0;
            }
        }
        
        // IMPORTANT: the C function will always be called from our python methods, 
        // so this check is redundant. However, the user should never be allowed 
        // to call our C methods directly! Otherwise C functions will be recorded.
        // We keep this part in case we need to use it in the future

        //if (is_c && is_call) {
        //    PyCFunctionObject* func = (PyCFunctionObject*) arg;
        //    if (func->m_module) {
        //        if (startswith(PyUnicode_AsUTF8(func->m_module), snaptracemodule.m_name)) {
        //            printf("ignored\n");
        //            info->ignore_stack_depth += 1;
        //            return 0;
        //        }
        //    }
        //} 

        // Check max stack depth
        if (CHECK_FLAG(self->check_flags, SNAPTRACE_MAX_STACK_DEPTH)) {
            if (is_call) {
                info->curr_stack_depth += 1;
                if (info->curr_stack_depth > self->max_stack_depth) {
                    return 0;
                }
            } else if (is_return) {
                if (info->curr_stack_depth > 0) {
                    info->curr_stack_depth -= 1;
                    if (info->curr_stack_depth + 1 > self->max_stack_depth) {
                        return 0;
                    }
                }
            }
        }

        // Check include/exclude files
        if (CHECK_FLAG(self->check_flags, SNAPTRACE_INCLUDE_FILES | SNAPTRACE_EXCLUDE_FILES) && is_python && is_call) {
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

        if (CHECK_FLAG(self->check_flags, SNAPTRACE_IGNORE_FROZEN)) {
            if (is_python && is_call) {
                PyObject* file_name = frame->f_code->co_filename;
                if (startswith(PyUnicode_AsUTF8(file_name), "<frozen")) {
                    info->ignore_stack_depth += 1;
                    return 0;
                }
            }
        }

        if (is_call) {
            // If it's a call, we need a new node, and we need to update the stack
            if (!info->stack_top->next) {
                info->stack_top->next = (struct FunctionNode*) PyMem_Calloc(1, sizeof(struct FunctionNode));
                info->stack_top->next->prev = info->stack_top;
            }
            info->stack_top = info->stack_top->next;
            info->stack_top->ts = get_ts();
            if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_FUNCTION_ARGS)) {
                log_func_args(info->stack_top, frame);
            }
        } else if (is_return) {
            struct FunctionNode* stack_top = info->stack_top;
            if (stack_top->prev) {
                // if stack_top has prev, it's not the fake node so it's at least root
                node = get_next_node(self);
                node->ntype = FEE_NODE;
                node->ts = info->stack_top->ts;
                node->data.fee.dur = get_ts() - info->stack_top->ts;
                info->stack_top = info->stack_top->prev;
                node->tid = info->tid;
                node->data.fee.type = what;
                if (is_python) {
                    node->data.fee.co_name = frame->f_code->co_name;
                    node->data.fee.co_filename = frame->f_code->co_filename;
                    node->data.fee.co_firstlineno = frame->f_code->co_firstlineno;
                    Py_INCREF(node->data.fee.co_name);
                    Py_INCREF(node->data.fee.co_filename);
                    if (stack_top->args) {
                        // steal the reference when return
                        node->data.fee.args = stack_top->args;
                        stack_top->args = NULL;
                    }
                    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE)) {
                        node->data.fee.retval = PyObject_Repr(arg);
                    }
                    if (!CHECK_FLAG(self->check_flags, SNAPTRACE_NOVDB) && frame->f_back) {
                        node->data.fee.caller_lineno = PyFrame_GetLineNumber(frame->f_back);
                    } else {
                        node->data.fee.caller_lineno = -1;
                    }
                } else if (is_c) {
                    PyCFunctionObject* cfunc = (PyCFunctionObject*) arg;
                    node->data.fee.ml_name = cfunc->m_ml->ml_name;
                    if (cfunc->m_module) {
                        // The function belongs to a module
                        node->data.fee.m_module = cfunc->m_module;
                        Py_INCREF(cfunc->m_module);
                    } else {
                        // The function is a class method
                        node->data.fee.m_module = NULL;
                        if (cfunc->m_self) {
                            // It's not a static method, has __self__
                            node->data.fee.tp_name = cfunc->m_self->ob_type->tp_name;
                        } else {
                            // It's a static method, does not have __self__
                            node->data.fee.tp_name = NULL;
                        }
                    }
                    if (!CHECK_FLAG(self->check_flags, SNAPTRACE_NOVDB)) {
                        node->data.fee.caller_lineno = PyFrame_GetLineNumber(frame);
                    } else {
                        node->data.fee.caller_lineno = -1;
                    }
                } 
            }
            return 0;
        } else {
            printf("Unexpected event!\n");
        }
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
    PyEval_SetProfile(snaptrace_tracefuncdisabled, obj);
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
    snaptrace_tracefuncdisabled(obj, frame, what, trace_args);
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

    self->collecting = 1;
    PyEval_SetProfile(snaptrace_tracefunc, (PyObject*) self);

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_stop(TracerObject* self, PyObject* args)
{
    struct ThreadInfo* info = get_thread_info(self);
    self->collecting = 0;

    if (info) {
        info->curr_stack_depth = 0;
        info->ignore_stack_depth = 0;
        info->paused = 0;
        clear_stack(&info->stack_top);
    }
    curr_tracer = NULL;
    PyEval_SetProfile(NULL, NULL);

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_pause(PyObject* self, PyObject* args)
{
    if (curr_tracer->collecting) {
        PyGILState_STATE state = PyGILState_Ensure();
        struct ThreadInfo* info = get_thread_info((TracerObject*)self);

        if (!info->paused) {
            PyEval_SetProfile(NULL, NULL);
            // When we enter this function, viztracer.pause and
            // tracer.pause both have been called. We need to
            // reduce the ignore_stack_depth to simulate the
            // returns from these two functions
            info->ignore_stack_depth -= 2;
            info->paused = 1;
        }
        PyGILState_Release(state);
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_resume(PyObject* self, PyObject* args)
{
    if (curr_tracer->collecting) {
        PyGILState_STATE state = PyGILState_Ensure();
        struct ThreadInfo* info = get_thread_info((TracerObject*)self);

        if (info->paused) {
            PyEval_SetProfile(snaptrace_tracefunc, self);
            // When we enter this function, viztracer.pause and
            // tracer.pause both have been called but not recorded.
            // It seems like C function tracer.pause's return will not
            // be recorded.
            // We need to increment the ignore_stack_depth to simulate the
            // call of the function
            info->ignore_stack_depth += 1;
            info->paused = 0;
        }
        PyGILState_Release(state);
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_load(TracerObject* self, PyObject* args)
{
    PyObject* lst = PyList_New(0);
    struct EventNode* curr = self->buffer + self->buffer_head_idx;
    PyObject* pid = NULL;
    PyObject* cat_fee = PyUnicode_FromString("FEE");
    PyObject* cat_instant = PyUnicode_FromString("INSTANT");
    PyObject* ph_B = PyUnicode_FromString("B");
    PyObject* ph_E = PyUnicode_FromString("E");
    PyObject* ph_I = PyUnicode_FromString("I");
    PyObject* ph_X = PyUnicode_FromString("X");
    PyObject* ph_C = PyUnicode_FromString("C");
    PyObject* ph_M = PyUnicode_FromString("M");
    unsigned long counter = 0;
    unsigned long prev_counter = 0;
    struct MetadataNode* metadata_node = NULL;

    if (self->fix_pid > 0) {
        pid = PyLong_FromLong(self->fix_pid);
    } else {
#if _WIN32
        pid = PyLong_FromLong(GetCurrentProcessId());
#else
        pid = PyLong_FromLong(getpid());
#endif
    }

    // == Load the metadata first ==
    //    Process Name
    {
        PyObject* dict = PyDict_New();
        PyObject* args = PyDict_New();
        PyObject* process_name_string = PyUnicode_FromString("process_name");
        PyObject* current_process_method = PyObject_GetAttrString(multiprocessing_module, "current_process");
        if (!current_process_method) {
            perror("Failed to access multiprocessing.current_process()");
            exit(-1);
        }
        PyObject* current_process = PyObject_CallObject(current_process_method, NULL);
        if (!current_process_method) {
            perror("Failed to access multiprocessing.current_process()");
            exit(-1);
        }
        PyObject* process_name = PyObject_GetAttrString(current_process, "name");

        Py_DECREF(current_process_method);
        PyDict_SetItemString(dict, "ph", ph_M);
        PyDict_SetItemString(dict, "pid", pid);
        PyDict_SetItemString(dict, "tid", pid);
        PyDict_SetItemString(dict, "name", process_name_string);
        Py_DECREF(process_name_string);
        PyDict_SetItemString(args, "name", process_name);
        PyDict_SetItemString(dict, "args", args);
        Py_DECREF(args);
        Py_DECREF(process_name);
        PyList_Append(lst, dict);
    }

    
    //    Thread Name
    metadata_node = self->metadata_head;
    while (metadata_node) {
        PyObject* dict = PyDict_New();
        PyObject* args = PyDict_New();
        PyObject* tid = PyLong_FromLong(metadata_node->tid);
        PyObject* thread_name_string = PyUnicode_FromString("thread_name");

        PyDict_SetItemString(dict, "ph", ph_M);
        PyDict_SetItemString(dict, "pid", pid);
        PyDict_SetItemString(dict, "tid", tid);
        Py_DECREF(tid);
        PyDict_SetItemString(dict, "name", thread_name_string);
        Py_DECREF(thread_name_string);
        PyDict_SetItemString(args, "name", metadata_node->name);
        PyDict_SetItemString(dict, "args", args);
        Py_DECREF(args);
        metadata_node = metadata_node->next;
        PyList_Append(lst, dict);
    }
    while (curr != self->buffer + self->buffer_tail_idx) {
        struct EventNode* node = curr;
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
                name = PyUnicode_FromFormat("%s (%s:%d)",
                       PyUnicode_AsUTF8(node->data.fee.co_name),
                       PyUnicode_AsUTF8(node->data.fee.co_filename),
                       node->data.fee.co_firstlineno);
            } else {
                if (node->data.fee.m_module) {
                    // The function belongs to a module
                    name = PyUnicode_FromFormat("%s.%s",
                           PyUnicode_AsUTF8(node->data.fee.m_module),
                           node->data.fee.ml_name);
                } else {
                    // The function is a class method
                    if (node->data.fee.tp_name) {
                        // It's not a static method, has __self__
                        name = PyUnicode_FromFormat("%s.%s",
                               node->data.fee.tp_name,
                               node->data.fee.ml_name);
                    } else {
                        // It's a static method, does not have __self__
                        name = PyUnicode_FromFormat("%s",
                               node->data.fee.ml_name);
                    }
                }
            }

            PyObject* dur = PyFloat_FromDouble(node->data.fee.dur / 1000);
            PyDict_SetItemString(dict, "dur", dur);
            Py_DECREF(dur);
            PyDict_SetItemString(dict, "name", name);
            Py_DECREF(name);

            if (node->data.fee.caller_lineno >= 0) {
                PyObject* caller_lineno = PyLong_FromLong(node->data.fee.caller_lineno);
                PyDict_SetItemString(dict, "caller_lineno", caller_lineno);
                Py_DECREF(caller_lineno);
            }

            PyObject* arg_dict = NULL;
            if (node->data.fee.args) {
                arg_dict = node->data.fee.args;
                Py_INCREF(arg_dict);
            }
            if (node->data.fee.retval) {
                if (!arg_dict) {
                    arg_dict = PyDict_New();
                }
                PyDict_SetItemString(arg_dict, "return_value", node->data.fee.retval);
            }
            if (arg_dict) {
                PyDict_SetItemString(dict, "args", arg_dict);
                Py_DECREF(arg_dict);
            }

            PyDict_SetItemString(dict, "ph", ph_X);
            PyDict_SetItemString(dict, "cat", cat_fee);
            break;
        case INSTANT_NODE:
            PyDict_SetItemString(dict, "ph", ph_I);
            PyDict_SetItemString(dict, "cat", cat_instant);
            PyDict_SetItemString(dict, "name", node->data.instant.name);
            PyDict_SetItemString(dict, "args", node->data.instant.args);
            PyDict_SetItemString(dict, "s", node->data.instant.scope);
            break;
        case COUNTER_NODE:
            PyDict_SetItemString(dict, "ph", ph_C);
            PyDict_SetItemString(dict, "name", node->data.counter.name);
            PyDict_SetItemString(dict, "args", node->data.counter.args);
            break;
        case OBJECT_NODE:
            PyDict_SetItemString(dict, "ph", node->data.object.ph);
            PyDict_SetItemString(dict, "id", node->data.object.id);
            PyDict_SetItemString(dict, "name", node->data.object.name);
            if (!(node->data.object.args == Py_None)) {
                PyDict_SetItemString(dict, "args", node->data.object.args);
            }
            break;
        case RAW_NODE:
            // We still need to tid from node and we need the pid
            tid = PyLong_FromLong(node->tid);

            Py_DECREF(dict);
            dict = node->data.raw;

            PyDict_SetItemString(dict, "pid", pid);
            PyDict_SetItemString(dict, "tid", tid);
            Py_DECREF(tid);

            Py_INCREF(dict);
            break;
        default:
            printf("Unknown Node Type!\n");
            exit(1);
        }
        clear_node(node);
        PyList_Append(lst, dict);
        curr = curr + 1;
        if (curr == self->buffer + self->buffer_size) {
            curr = self->buffer;
        }

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
    Py_DECREF(ph_M);
    self->buffer_tail_idx = self->buffer_head_idx;
    return lst;
}

static PyObject*
snaptrace_clear(TracerObject* self, PyObject* args)
{
    struct EventNode* curr = self->buffer + self->buffer_head_idx;
    while (curr != self->buffer + self->buffer_tail_idx) {
        struct EventNode* node = curr;
        clear_node(node);
        curr = curr + 1;
        if (curr == self->buffer + self->buffer_size) {
            curr = self->buffer;
        }
    }
    self->buffer_tail_idx = self->buffer_head_idx;

    Py_RETURN_NONE;
}

static PyObject* 
snaptrace_cleanup(TracerObject* self, PyObject* args)
{
    snaptrace_clear(self, args);
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
snaptrace_getts(TracerObject* self, PyObject* args)
{
    double ts = get_ts();

    return PyFloat_FromDouble(ts / 1000);
}

static PyObject*
snaptrace_setcurrstack(TracerObject* self, PyObject* args)
{
    int stack_depth = 1;
    struct ThreadInfo* info = get_thread_info(self);

    if (!PyArg_ParseTuple(args, "|i", &stack_depth)) {
        printf("Error when parsing arguments!\n");
        exit(1);
    }

    info->curr_stack_depth = stack_depth;

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_config(TracerObject* self, PyObject* args, PyObject* kw)
{
    static char* kwlist[] = {"verbose", "lib_file_path", "max_stack_depth", 
            "include_files", "exclude_files", "ignore_c_function", "ignore_frozen",
            "log_func_retval", "novdb", "log_func_args",
            NULL};
    int kw_verbose = -1;
    int kw_max_stack_depth = 0;
    char* kw_lib_file_path = NULL;
    PyObject* kw_include_files = NULL;
    PyObject* kw_exclude_files = NULL;
    int kw_ignore_c_function = -1;
    int kw_ignore_frozen = -1;
    int kw_log_func_retval = -1;
    int kw_novdb = -1;
    int kw_log_func_args = -1;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "|isiOOppppp", kwlist, 
            &kw_verbose,
            &kw_lib_file_path,
            &kw_max_stack_depth,
            &kw_include_files,
            &kw_exclude_files,
            &kw_ignore_c_function,
            &kw_ignore_frozen,
            &kw_log_func_retval,
            &kw_novdb,
            &kw_log_func_args)) {
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

    if (kw_ignore_frozen == 1) {
        SET_FLAG(self->check_flags, SNAPTRACE_IGNORE_FROZEN);
    } else if (kw_ignore_frozen == 0) {
        UNSET_FLAG(self->check_flags, SNAPTRACE_IGNORE_FROZEN);
    }

    if (kw_log_func_retval == 1) {
        SET_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE);
    } else if (kw_log_func_retval == 0) {
        UNSET_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE);
    }

    if (kw_novdb == 1) {
        SET_FLAG(self->check_flags, SNAPTRACE_NOVDB);
    } else if (kw_novdb == 0) {
        UNSET_FLAG(self->check_flags, SNAPTRACE_NOVDB);
    }

    if (kw_log_func_args == 1) {
        SET_FLAG(self->check_flags, SNAPTRACE_LOG_FUNCTION_ARGS);
    } else if (kw_log_func_args == 0) {
        UNSET_FLAG(self->check_flags, SNAPTRACE_LOG_FUNCTION_ARGS);
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
snaptrace_addfunctionarg(TracerObject* self, PyObject* args)
{
    PyObject* key = NULL;
    PyObject* value = NULL;
    struct ThreadInfo* info = get_thread_info(self);
    if (!PyArg_ParseTuple(args, "OO", &key, &value)) {
        printf("Error when parsing arguments!\n");
        exit(1);
    }

    struct FunctionNode* fnode = info->stack_top;
    if (!fnode->args) {
        fnode->args = PyDict_New();
    }

    PyDict_SetItem(fnode->args, key, value);

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
    Py_INCREF(counter_args);

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
    Py_INCREF(object_args);

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_addraw(TracerObject* self, PyObject* args)
{
    PyObject* raw = NULL;
    struct ThreadInfo* info = get_thread_info(self);
    struct EventNode* node = NULL;
    if (!PyArg_ParseTuple(args, "O", &raw)) {
        printf("Error when parsing arguments!\n");
        exit(1);
    }

    node = get_next_node(self);
    node->tid = info->tid;
    node->ntype = RAW_NODE;
    node->data.raw = raw;
    Py_INCREF(raw);

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_getfunctionarg(TracerObject* self, PyObject* args)
{
    struct ThreadInfo* info = get_thread_info(self);

    struct FunctionNode* fnode = info->stack_top;
    if (!fnode->args) {
        Py_RETURN_NONE;
    }

    Py_INCREF(fnode->args);

    return fnode->args;
}

static struct ThreadInfo* snaptrace_createthreadinfo(TracerObject* self) {
    struct ThreadInfo* info = calloc(1, sizeof(struct ThreadInfo));

    info->stack_top = (struct FunctionNode*) PyMem_Calloc(1, sizeof(struct FunctionNode));

#if _WIN32  
    info->tid = GetCurrentThreadId();
#elif __APPLE__
    __uint64_t tid = 0;
    if (pthread_threadid_np(NULL, &tid)) {
        info->tid = (unsigned long)pthread_self();
    } else {
        info->tid = tid;
    }
#else
    info->tid = syscall(SYS_gettid);
#endif

#if _WIN32
    TlsSetValue(self->dwTlsIndex, info);
#else
    pthread_setspecific(self->thread_key, info);
#endif

    PyGILState_STATE state = PyGILState_Ensure();

    PyObject* current_thread_method = PyObject_GetAttrString(threading_module, "current_thread");
    if (!current_thread_method) {
        perror("Failed to access threading.current_thread()");
        exit(-1);
    }
    PyObject* current_thread = PyObject_CallObject(current_thread_method, NULL);
    if (!current_thread) {
        perror("Failed to access threading.current_thread()");
        exit(-1);
    }
    PyObject* thread_name = PyObject_GetAttrString(current_thread, "name");

    Py_DECREF(current_thread_method);

    // Check for existing node for the same tid first
    struct MetadataNode* node = self->metadata_head;
    int found_node = 0;

    while (node) {
        if (node->tid == info->tid) {
            Py_DECREF(node->name);
            node->name = thread_name;
            found_node = 1;
            break;
        }
        node = node->next;
    }

    if (!found_node) {
        node = (struct MetadataNode*) PyMem_Calloc(1, sizeof(struct MetadataNode));
        if (!node) {
            perror("Out of memory!");
            exit(-1);
        }
        node->name = thread_name;
        node->tid = info->tid;
        node->next = self->metadata_head;
        self->metadata_head = node;
    }

    PyGILState_Release(state);

    return info;
}

static void snaptrace_threaddestructor(void* key) {
    struct ThreadInfo* info = key;
    struct FunctionNode* tmp = NULL;
    if (info) {
        info->paused = 0;
        info->curr_stack_depth = 0;
        info->ignore_stack_depth = 0;
        info->tid = 0;
        if (info->stack_top) {
            while (info->stack_top->prev) {
                info->stack_top = info->stack_top->prev;
            }
            PyGILState_STATE state = PyGILState_Ensure();
            while (info->stack_top) {
                tmp = info->stack_top;
                if (tmp->args) {
                    Py_DECREF(tmp->args);
                    tmp->args = NULL;
                }
                info->stack_top = info->stack_top->next;
                PyMem_FREE(tmp);
            }
            PyGILState_Release(state);
        }
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
        if (!PyArg_ParseTuple(args, "l", &self->buffer_size)) {
            printf("You need to specify buffer size when initializing Tracer\n");
            exit(-1);
        }
        // We need an extra slot for circular buffer
        self->buffer_size += 1;
        self->collecting = 0;
        self->fix_pid = 0;
        self->total_entries = 0;
        self->check_flags = 0;
        self->verbose = 0;
        self->lib_file_path = NULL;
        self->max_stack_depth = 0;
        self->include_files = NULL;
        self->exclude_files = NULL;
        self->buffer = (struct EventNode*) PyMem_Calloc(self->buffer_size, sizeof(struct EventNode));
        if (!self->buffer) {
            printf("Out of memory!\n");
            exit(1);
        }
        self->buffer_head_idx = 0;
        self->buffer_tail_idx = 0;
        self->metadata_head = NULL;
        snaptrace_createthreadinfo(self);
        // Python: threading.setprofile(tracefuncdisabled)
        {
            PyObject* setprofile = PyObject_GetAttrString(threading_module, "setprofile");

            PyObject* handler = PyCFunction_New(&Tracer_methods[0], (PyObject*)self);
            PyObject* callback = Py_BuildValue("(N)", handler);

            if (PyObject_CallObject(setprofile, callback) == NULL) {
                perror("Failed to call threading.setprofile() properly");
                exit(-1);
            }
            Py_DECREF(callback);
        }
        PyEval_SetProfile(snaptrace_tracefuncdisabled, (PyObject*)self);
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
    PyMem_FREE(self->buffer);

    struct MetadataNode* node = self->metadata_head;
    struct MetadataNode* prev = NULL;
    while (node) {
        prev = node;
        Py_DECREF(node->name);
        node->name = NULL;
        node = node->next;
        PyMem_FREE(prev);
    }

    // threading.setprofile(None)
    PyObject* setprofile = PyObject_GetAttrString(threading_module, "setprofile");
    // This is important to keep REFCNT normal
    if (setprofile != Py_None) {
        PyObject* tuple = PyTuple_New(1);
        PyTuple_SetItem(tuple, 0, Py_None);
        if (PyObject_CallObject(setprofile, tuple) == NULL) {
            perror("Failed to call threading.setprofile() properly dealloc");
            exit(-1);
        }
        Py_DECREF(tuple);
    }

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

    threading_module = PyImport_ImportModule("threading");
    multiprocessing_module = PyImport_ImportModule("multiprocessing");

    return m;
}