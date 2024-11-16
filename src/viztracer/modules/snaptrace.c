// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>
#include <frameobject.h>
#if _WIN32
#include <windows.h>
#elif defined(__APPLE__)
#include <pthread.h>
#elif defined(__FreeBSD__)
#include <pthread_np.h>
#else
#include <pthread.h>
#include <sys/syscall.h>
#endif

#include "pythoncapi_compat.h"
#include "snaptrace.h"
#include "quicktime.h"
#include "util.h"
#include "eventnode.h"


TracerObject* curr_tracer = NULL;
PyObject* threading_module = NULL;
PyObject* multiprocessing_module = NULL;
PyObject* json_module = NULL;
PyObject* asyncio_module = NULL;
PyObject* asyncio_tasks_module = NULL;
PyObject* trio_module = NULL;
PyObject* trio_lowlevel_module = NULL;

static PyObject* curr_task_getters[2] = {0};

// =============================================================================
// Utility function
// =============================================================================

static inline int64_t
get_ts(struct ThreadInfo* info)
{
    int64_t curr_ts = get_system_ts();
    if (curr_ts <= info->prev_ts) {
        // We use artificial timestamp to avoid timestamp conflict.
        // 20 ns should be a safe granularity because that's normally
        // how long clock_gettime() takes.
        // It's possible to have three same timestamp in a row so we
        // need to check if curr_ts <= prev_ts instead of ==
#if _WIN32 || defined(__APPLE__)
        curr_ts = info->prev_ts + 1;
#else
        curr_ts = info->prev_ts + 20;
#endif
    }
    info->prev_ts = curr_ts;
    return curr_ts;
}

static inline struct EventNode*
get_next_node(TracerObject* self)
{
    struct EventNode* node = NULL;

    SNAPTRACE_THREAD_PROTECT_START(self);
    node = self->buffer + self->buffer_tail_idx;
    // This is actually faster than modulo
    self->buffer_tail_idx = self->buffer_tail_idx + 1;
    if (self->buffer_tail_idx >= self->buffer_size) {
        self->buffer_tail_idx = 0;
    }
    if (self->buffer_tail_idx == self->buffer_head_idx) {
        self->buffer_head_idx = self->buffer_head_idx + 1;
        if (self->buffer_head_idx >= self->buffer_size) {
            self->buffer_head_idx = 0;
        }
        clear_node(self->buffer + self->buffer_tail_idx);
    } else {
        self->total_entries += 1;
    }
    SNAPTRACE_THREAD_PROTECT_END(self);

    return node;
}

static void
log_func_args(struct FunctionNode* node, PyFrameObject* frame, PyObject* log_func_repr)
{
    PyObject* func_arg_dict = PyDict_New();
    PyCodeObject* code = PyFrame_GetCode(frame);
    PyObject* names = PyCode_GetVarnames(code);

#if PY_VERSION_HEX >= 0x030D0000
    PyObject* locals = PyEval_GetFrameLocals();
#else
    PyObject* locals = PyEval_GetLocals();
#endif

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
        PyObject* repr = NULL;
        // New
        if (log_func_repr) {
            repr = PyObject_CallOneArg(log_func_repr, PyDict_GetItem(locals, name));
        } else {
            repr = PyObject_Repr(PyDict_GetItem(locals, name));
        }
        if (!repr) {
            repr = PyUnicode_FromString("Not Displayable");
            PyErr_Clear();
        }
        PyDict_SetItem(func_arg_dict, name, repr);
        Py_DECREF(repr);
        idx++;
    }

#if PY_VERSION_HEX >= 0x030D0000
    Py_DECREF(locals);
#endif

    PyDict_SetItemString(node->args, "func_args", func_arg_dict);
    Py_DECREF(func_arg_dict);

    Py_XDECREF(code);
    Py_XDECREF(names);
}

static void
verbose_printf(TracerObject* self, int v, const char* fmt, ...)
{
    va_list args;
    if (self->verbose >= v) {
        va_start(args, fmt);
        vprintf(fmt, args);
        va_end(args);
        fflush(stdout);
    }
}

void
clear_stack(struct FunctionNode** stack_top) {
    Py_CLEAR((*stack_top)->args);
    while ((*stack_top)->prev) {
        (*stack_top) = (*stack_top) -> prev;
        Py_CLEAR((*stack_top)->args);
    }
}

// =============================================================================
// Thread info related functions
// =============================================================================

static struct ThreadInfo*
get_thread_info(TracerObject* self)
{
    // self is non-NULL value
    struct ThreadInfo* info = NULL;
#if _WIN32
    info = TlsGetValue(self->dwTlsIndex);
#else
    info = pthread_getspecific(self->thread_key);
#endif
    return info;
}

static struct ThreadInfo*
snaptrace_createthreadinfo(TracerObject* self) {
    struct ThreadInfo* info = get_thread_info(self);

    if (info != NULL) {
        // If we have created the thread info, just return it.
        return info;
    }

    // Otherwise, we need to create thread info.

    info = PyMem_Calloc(1, sizeof(struct ThreadInfo));
    info->stack_top = (struct FunctionNode*) PyMem_Calloc(1, sizeof(struct FunctionNode));

#if _WIN32  
    info->tid = GetCurrentThreadId();
#elif defined(__APPLE__)
    __uint64_t tid = 0;
    if (pthread_threadid_np(NULL, &tid)) {
        info->tid = (unsigned long)pthread_self();
    } else {
        info->tid = tid;
    }
#elif defined(__FreeBSD__)
    info->tid = pthread_getthreadid_np();
#else
    info->tid = syscall(SYS_gettid);
#endif

#if _WIN32
    TlsSetValue(self->dwTlsIndex, info);
#else
    pthread_setspecific(self->thread_key, info);
#endif

    PyGILState_STATE state = PyGILState_Ensure();
    SNAPTRACE_THREAD_PROTECT_START(self);

    PyObject* current_thread = PyObject_CallMethod(threading_module, "current_thread", "");
    if (!current_thread) {
        perror("Failed to access threading.current_thread()");
        exit(-1);
    }
    PyObject* thread_name = PyObject_GetAttrString(current_thread, "name");
    if (!thread_name) {
        // It's okay not having a name
        PyErr_Clear();
        thread_name = PyUnicode_FromString("Unknown");
    }

    Py_DECREF(current_thread);

    // Check for existing node for the same tid first
    struct MetadataNode* node = self->metadata_head;
    int found_node = 0;

    while (node) {
        if (node->tid == info->tid) {
            Py_DECREF(node->name);
            node->name = thread_name;
            node->thread_info = info;
            info->metadata_node = node;
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
        node->thread_info = info;
        info->metadata_node = node;
        node->next = self->metadata_head;
        self->metadata_head = node;
    }

    info->curr_task = NULL;
    info->curr_task_frame = NULL;
    info->prev_ts = 0.0;

    SNAPTRACE_THREAD_PROTECT_END(self);
    PyGILState_Release(state);

    return info;
}

static void
snaptrace_threaddestructor(void* key) {
    struct ThreadInfo* info = key;
    struct FunctionNode* tmp = NULL;
    if (info) {
        PyGILState_STATE state = PyGILState_Ensure();
        info->paused = 0;
        info->curr_stack_depth = 0;
        info->ignore_stack_depth = 0;
        info->tid = 0;
        if (info->stack_top) {
            while (info->stack_top->prev) {
                info->stack_top = info->stack_top->prev;
            }
            while (info->stack_top) {
                tmp = info->stack_top;
                Py_CLEAR(tmp->args);
                Py_CLEAR(tmp->func);
                info->stack_top = info->stack_top->next;
                PyMem_FREE(tmp);
            }
        }
        info->stack_top = NULL;
        Py_CLEAR(info->curr_task);
        Py_CLEAR(info->curr_task_frame);
        info->metadata_node->thread_info = NULL;
        PyMem_FREE(info);
        PyGILState_Release(state);
    }
}

// =============================================================================
// Tracing function, triggered when FEE
// =============================================================================

int
tracer_pycall_callback(TracerObject* self, PyFrameObject* frame, struct ThreadInfo* info)
{
    PyCodeObject* code = PyFrame_GetCode(frame);
    PyObject* co_filename = code->co_filename;

    if (!CHECK_FLAG(self->check_flags, SNAPTRACE_TRACE_SELF)) {
        if (self->lib_file_path && co_filename && PyUnicode_Check(co_filename) &&
                startswith(PyUnicode_AsUTF8(co_filename), self->lib_file_path)) {
            info->ignore_stack_depth += 1;
            goto cleanup;
        }
    }

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
            for (int i = 0; i < length; i++) {
                PyObject* f = PyList_GET_ITEM(files, i);
                if (startswith(PyUnicode_AsUTF8(co_filename), PyUnicode_AsUTF8(f))) {
                    record = 1 - record;
                    break;
                }
            }
            if (record == 0) {
                info->ignore_stack_depth += 1;
                goto cleanup;
            }
        } else {
            goto cleanup;
        }
    }

    if (CHECK_FLAG(self->check_flags, SNAPTRACE_IGNORE_FROZEN)) {
        if (startswith(PyUnicode_AsUTF8(co_filename), "<frozen")) {
            info->ignore_stack_depth += 1;
            goto cleanup;
        }
    }

    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC) &&
            info->curr_task == NULL &&
            (code->co_flags & CO_COROUTINE) != 0) {
        PyObject* curr_task = Py_None;
        info->paused = 1;
        for (size_t i = 0; i < sizeof(curr_task_getters)/sizeof(curr_task_getters[0]); i++) {
            if (curr_task_getters[i] != NULL) {
                curr_task = PyObject_CallObject(curr_task_getters[i], NULL);
                if (!curr_task) {
                    PyErr_Clear();  // RuntimeError, probably
                    curr_task = Py_None;
                } else if (curr_task != Py_None) {
                    break;  // got a valid task
                }
            }
        }
        info->paused = 0;
        info->curr_task = Py_NewRef(curr_task);
        info->curr_task_frame = (PyFrameObject*)Py_NewRef(frame);
    }

    // If it's a call, we need a new node, and we need to update the stack
    if (!info->stack_top->next) {
        info->stack_top->next = (struct FunctionNode*) PyMem_Calloc(1, sizeof(struct FunctionNode));
        info->stack_top->next->prev = info->stack_top;
    }
    info->stack_top = info->stack_top->next;
    info->stack_top->ts = get_ts(info);
    info->stack_top->func = Py_NewRef(code);
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_FUNCTION_ARGS)) {
        log_func_args(info->stack_top, frame, self->log_func_repr);
    }

cleanup:

    Py_XDECREF(code);

    return 0;
}

int
tracer_ccall_callback(TracerObject* self, PyFrameObject* frame, struct ThreadInfo* info, PyObject* arg)
{
    PyCFunctionObject* cfunc = (PyCFunctionObject*) arg;

    if (cfunc->m_self == (PyObject*)self) {
        info->ignore_stack_depth += 1;
        return 0;
    }

    // If it's a call, we need a new node, and we need to update the stack
    if (!info->stack_top->next) {
        info->stack_top->next = (struct FunctionNode*) PyMem_Calloc(1, sizeof(struct FunctionNode));
        info->stack_top->next->prev = info->stack_top;
    }
    info->stack_top = info->stack_top->next;
    info->stack_top->ts = get_ts(info);
    info->stack_top->func = Py_NewRef(arg);
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_FUNCTION_ARGS)) {
        log_func_args(info->stack_top, frame, self->log_func_repr);
    }

    return 0;
}

int
tracer_pyreturn_callback(TracerObject* self, PyFrameObject* frame, struct ThreadInfo* info, PyObject* arg)
{
    struct FunctionNode* stack_top = info->stack_top;
    if (stack_top->prev) {
        // if stack_top has prev, it's not the fake node so it's at least root
        int64_t dur = get_ts(info) - info->stack_top->ts;
        int log_this_entry = self->min_duration == 0 || dur_ts_to_ns(dur) >= self->min_duration;

        if (log_this_entry) {
            PyCodeObject* code = (PyCodeObject*) stack_top->func;

            if (!PyCode_Check(code)) {
                self->collecting = 0;
                PyErr_SetString(PyExc_RuntimeError, "VizTracer: Unexpected type. Might be an event mismatch.");
                return -1;
            }

            struct EventNode* node = get_next_node(self);

            node->ntype = FEE_NODE;
            node->ts = info->stack_top->ts;
            node->data.fee.dur = dur;
            node->tid = info->tid;
            node->data.fee.type = PyTrace_RETURN;
            node->data.fee.code = (PyCodeObject*)Py_NewRef(code);
            // steal the reference when return
            node->data.fee.args = Py_XNewRef(stack_top->args);
            if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_RETURN_VALUE)) {
                PyObject* repr = NULL;
                if (self->log_func_repr) {
                    repr = PyObject_CallOneArg(self->log_func_repr, arg);
                } else {
                    repr = PyObject_Repr(arg);
                }
                if (!repr) {
                    repr = PyUnicode_FromString("Not Displayable");
                    PyErr_Clear();
                }
                node->data.fee.retval = repr;
            }

            if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
                node->data.fee.asyncio_task = Py_XNewRef(info->curr_task);
            }
        }
        // Finish return whether to log the data
        info->stack_top = info->stack_top->prev;

        Py_CLEAR(stack_top->args);
        Py_CLEAR(stack_top->func);

        if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC) &&
                info->curr_task &&
                frame == info->curr_task_frame) {
            Py_CLEAR(info->curr_task);
            Py_CLEAR(info->curr_task_frame);
        }
    }

    return 0;
}

int
tracer_creturn_callback(TracerObject* self, PyFrameObject* frame, struct ThreadInfo* info, PyObject* arg)
{
    struct FunctionNode* stack_top = info->stack_top;
    if (stack_top->prev) {
        // if stack_top has prev, it's not the fake node so it's at least root
        int64_t dur = get_ts(info) - info->stack_top->ts;
        int log_this_entry = self->min_duration == 0 || dur_ts_to_ns(dur) >= self->min_duration;

        if (log_this_entry) {
            PyCFunctionObject* cfunc = (PyCFunctionObject*) stack_top->func;

            if (!PyCFunction_Check(cfunc)) {
                self->collecting = 0;
                PyErr_SetString(PyExc_RuntimeError, "VizTracer: Unexpected type. Might be an event mismatch.");
                return -1;
            }

            struct EventNode* node = get_next_node(self);

            node->ntype = FEE_NODE;
            node->ts = info->stack_top->ts;
            node->data.fee.dur = dur;
            node->tid = info->tid;
            node->data.fee.type = PyTrace_C_RETURN;
            node->data.fee.ml_name = cfunc->m_ml->ml_name;
            if (cfunc->m_module) {
                // The function belongs to a module
                node->data.fee.m_module = Py_NewRef(cfunc->m_module);
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

            if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
                node->data.fee.asyncio_task = Py_XNewRef(info->curr_task);
            }
        }
        // Finish return whether to log the data
        info->stack_top = info->stack_top->prev;

        Py_CLEAR(stack_top->args);
        Py_CLEAR(stack_top->func);
    }

    return 0;
}

int
tracer_tracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg)
{
    TracerObject* self = (TracerObject*) obj;
    int ret = 0;

    if (!self->collecting) {
        return 0;
    }
    
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_IGNORE_C_FUNCTION) &&
            (what == PyTrace_C_CALL || what == PyTrace_C_RETURN || what == PyTrace_C_EXCEPTION)) {
        return 0;
    }

    struct ThreadInfo* info = get_thread_info(self);

    if (!info) {
        self->collecting = 0;
        PyErr_SetString(PyExc_RuntimeError, "VizTracer: Thread info not found. This should not happen.");
        return -1;
    }

    // This is a crazy hack for
    // is_call == (what == PyTrace_CALL || what == PyTrace_C_CALL)
    // Because PyTrace_CALL == 0 and PyTrace_C_CALL == 4
    int is_call = !(what & 0x3);

    if (info->paused) {
        return 0;
    }

    if (info->ignore_stack_depth > 0) {
        if (is_call) {
            info->ignore_stack_depth += 1;
            return 0;
        } else {
            info->ignore_stack_depth -= 1;
            return 0;
        }
    }

    if (CHECK_FLAG(self->check_flags, SNAPTRACE_MAX_STACK_DEPTH)) {
        if (is_call) {
            if (info->curr_stack_depth >= self->max_stack_depth) {
                info->curr_stack_depth += 1;
                return 0;
            }
        } else {
            if (info->curr_stack_depth > 0) {
                if (info->curr_stack_depth > self->max_stack_depth) {
                    info->curr_stack_depth -= 1;
                    return 0;
                }
            }
        }
    }

    switch (what) {
    case PyTrace_CALL:
        info->curr_stack_depth += 1;
        ret = tracer_pycall_callback(self, frame, info);
        break;
    case PyTrace_C_CALL:
        info->curr_stack_depth += 1;
        ret = tracer_ccall_callback(self, frame, info, arg);
        break;
    case PyTrace_RETURN:
        ret = tracer_pyreturn_callback(self, frame, info, arg);
        if (info->curr_stack_depth > 0) {
            info->curr_stack_depth -= 1;
        }
        break;
    case PyTrace_C_RETURN:
    case PyTrace_C_EXCEPTION:
        ret = tracer_creturn_callback(self, frame, info, arg);
        if (info->curr_stack_depth > 0) {
            info->curr_stack_depth -= 1;
        }
        break;
    default:
        return 0;
    }

    return ret;
}

static PyObject*
tracer_threadtracefunc(PyObject* obj, PyObject* args) 
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
    PyEval_SetProfile(tracer_tracefunc, obj);
    if (!strcmp(event, "call")) {
        what = PyTrace_CALL;
    } else if (!strcmp(event, "c_call")) {
        what = PyTrace_C_CALL;
    } else if (!strcmp(event, "return")) {
        what = PyTrace_RETURN;
    } else if (!strcmp(event, "c_return")) {
        what = PyTrace_C_RETURN;
    } else if (!strcmp(event, "c_exception")) {
        what = PyTrace_C_EXCEPTION;
    } else {
        printf("Unexpected event type: %s\n", event);
    }
    tracer_tracefunc(obj, frame, what, trace_args);
    Py_RETURN_NONE;
}

// =============================================================================
// snaptrace.Tracer methods
// =============================================================================

static void
tracer__flush_unfinished(TracerObject* self, int flush_as_finish)
{
    SNAPTRACE_THREAD_PROTECT_START(self);

    struct MetadataNode* meta_node = self->metadata_head;
    while(meta_node) {
        struct ThreadInfo* info = meta_node->thread_info;

        if (info == NULL) {
            meta_node = meta_node->next;
            continue;
        }

        struct FunctionNode* func_node = info->stack_top;

        while (func_node->prev && info->curr_stack_depth > 0) {
            // Fake a FEE node to get the name
            struct EventNode* fee_node = get_next_node(self);

            fee_node->ntype = FEE_NODE;
            fee_node->ts = func_node->ts;
            fee_node->tid = meta_node->tid;

            if (flush_as_finish) {
                fee_node->data.fee.dur = get_ts(info) - func_node->ts;
            } else {
                fee_node->data.fee.dur = 0;
            }

            if (PyCode_Check(func_node->func)) {
                PyCodeObject* code = (PyCodeObject*) func_node->func;
                if (flush_as_finish) {
                    fee_node->data.fee.type = PyTrace_RETURN;
                } else {
                    fee_node->data.fee.type = PyTrace_CALL;
                }
                fee_node->data.fee.code = (PyCodeObject*)Py_NewRef(code);
            } else if (PyCFunction_Check(func_node->func)) {
                PyCFunctionObject* cfunc = (PyCFunctionObject*) func_node->func;
                if (flush_as_finish) {
                    fee_node->data.fee.type = PyTrace_C_RETURN;
                } else {
                    fee_node->data.fee.type = PyTrace_C_CALL;
                }
                fee_node->data.fee.ml_name = cfunc->m_ml->ml_name;
                if (cfunc->m_module) {
                    // The function belongs to a module
                    fee_node->data.fee.m_module = Py_NewRef(cfunc->m_module);
                } else {
                    // The function is a class method
                    fee_node->data.fee.m_module = NULL;
                    if (cfunc->m_self) {
                        // It's not a static method, has __self__
                        fee_node->data.fee.tp_name = cfunc->m_self->ob_type->tp_name;
                    } else {
                        // It's a static method, does not have __self__
                        fee_node->data.fee.tp_name = NULL;
                    }
                }
            }

            // Clean up the node
            Py_CLEAR(func_node->args);
            Py_CLEAR(func_node->func);

            func_node = func_node->prev;
            info->curr_stack_depth -= 1;
        }
        info->stack_top = func_node;
        meta_node = meta_node->next;
    }

    SNAPTRACE_THREAD_PROTECT_END(self);
}

static PyObject*
tracer_start(TracerObject* self, PyObject* Py_UNUSED(unused))
{
    if (curr_tracer) {
        printf("Warning! Overwrite tracer! You should not have two VizTracer recording at the same time!\n");
    } else {
        curr_tracer = self;
    }

    self->collecting = 1;
    PyEval_SetProfile(tracer_tracefunc, (PyObject*) self);

    Py_RETURN_NONE;
}

static PyObject*
tracer_stop(TracerObject* self, PyObject* stop_option)
{
    if (self) {
        struct ThreadInfo* info = get_thread_info(self);
        self->collecting = 0;

        if (PyUnicode_CheckExact(stop_option) &&
                strcmp(PyUnicode_AsUTF8(stop_option), "flush_as_finish") == 0) {
            tracer__flush_unfinished(self, 1);
        } else {
            tracer__flush_unfinished(self, 0);
        }
        info->curr_stack_depth = 0;
        info->ignore_stack_depth = 0;
        info->paused = 0;
    }

    curr_tracer = NULL;
    PyEval_SetProfile(NULL, NULL);

    Py_RETURN_NONE;
}

static PyObject*
tracer_pause(TracerObject* self, PyObject* Py_UNUSED(unused))
{
    if (self->collecting) {
        PyGILState_STATE state = PyGILState_Ensure();
        struct ThreadInfo* info = get_thread_info((TracerObject*)self);

        if (!info->paused) {
            PyEval_SetProfile(NULL, NULL);
            // When we enter this function, tracer.pause has been called.
            // We need to reduce the ignore_stack_depth to simulate the
            // returns from these two functions
            info->ignore_stack_depth -= 1;
            info->paused = 1;
        }
        PyGILState_Release(state);
    }

    Py_RETURN_NONE;
}

static PyObject*
tracer_resume(TracerObject* self, PyObject* Py_UNUSED(unused))
{
    if (self->collecting) {
        PyGILState_STATE state = PyGILState_Ensure();
        struct ThreadInfo* info = get_thread_info(self);

        if (info->paused) {
            PyEval_SetProfile(tracer_tracefunc, (PyObject*)self);
            info->paused = 0;
        }
        PyGILState_Release(state);
    }

    Py_RETURN_NONE;
}

static PyObject*
tracer_load(TracerObject* self, PyObject* Py_UNUSED(unused))
{
    PyObject* lst = PyList_New(0);

    SNAPTRACE_THREAD_PROTECT_START(self);
    struct EventNode* curr = self->buffer + self->buffer_head_idx;
    PyObject* pid = NULL;
    PyObject* cat_fee = PyUnicode_FromString("FEE");
    PyObject* cat_instant = PyUnicode_FromString("INSTANT");
    PyObject* ph_B = PyUnicode_FromString("B");
    PyObject* ph_i = PyUnicode_FromString("i");
    PyObject* ph_X = PyUnicode_FromString("X");
    PyObject* ph_C = PyUnicode_FromString("C");
    PyObject* ph_M = PyUnicode_FromString("M");
    unsigned long counter = 0;
    unsigned long prev_counter = 0;
    struct MetadataNode* metadata_node = NULL;
    PyObject* task_dict = NULL;
    PyObject* func_name_dict = PyDict_New();

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
        PyObject* process_name = NULL;

        if (self->process_name) {
            process_name = Py_NewRef(self->process_name);
        } else {
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
            process_name = PyObject_GetAttrString(current_process, "name");
            Py_DECREF(current_process_method);
            Py_DECREF(current_process);
        }
        
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

    // Task Name if using LOG_ASYNC
    // We need to make up some thread id for the task
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
        task_dict = PyDict_New();
    }

    while (curr != self->buffer + self->buffer_tail_idx) {
        struct EventNode* node = curr;
        PyObject* dict = PyDict_New();
        PyObject* name = NULL;
        PyObject* tid = PyLong_FromLong(node->tid);
        PyObject* ts = PyFloat_FromDouble(system_ts_to_us(node->ts));

        PyDict_SetItemString(dict, "pid", pid);
        if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
            if (curr->data.fee.asyncio_task == NULL) {
                PyDict_SetItemString(dict, "tid", tid);
            } else {
                PyObject* task_id = PyLong_FromUnsignedLongLong(((uintptr_t)curr->data.fee.asyncio_task) & 0xffffff);
                PyDict_SetItemString(dict, "tid", task_id);
                if (!PyDict_Contains(task_dict, task_id)) {
                    PyObject* task_name = NULL;
                    if (PyObject_HasAttrString(curr->data.fee.asyncio_task, "get_name")) {
                        PyObject* task_name_method = PyObject_GetAttrString(curr->data.fee.asyncio_task, "get_name");
                        task_name = PyObject_CallObject(task_name_method, NULL);
                        Py_DECREF(task_name_method);
                    } else if (PyObject_HasAttrString(curr->data.fee.asyncio_task, "name")) {
                        task_name = PyObject_GetAttrString(curr->data.fee.asyncio_task, "name");
                    } else {
                        task_name = PyUnicode_FromString("Task");
                    }
                    PyDict_SetItem(task_dict, task_id, task_name);
                    Py_DECREF(task_name);
                }
                Py_DECREF(task_id);
            }
        } else {
            PyDict_SetItemString(dict, "tid", tid);
        }
        Py_DECREF(tid);
        PyDict_SetItemString(dict, "ts", ts);
        Py_DECREF(ts);

        switch (node->ntype) {
        case FEE_NODE:
            name = get_name_from_fee_node(node, func_name_dict);

            if (node->data.fee.type == PyTrace_CALL || node->data.fee.type == PyTrace_C_CALL) {
                PyDict_SetItemString(dict, "ph", ph_B);
            } else {
                PyDict_SetItemString(dict, "ph", ph_X);
                PyObject* dur = PyFloat_FromDouble(dur_ts_to_us(node->data.fee.dur));
                PyDict_SetItemString(dict, "dur", dur);
                Py_DECREF(dur);
            }
            PyDict_SetItemString(dict, "name", name);
            Py_DECREF(name);

            PyObject* arg_dict = Py_XNewRef(node->data.fee.args);
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

            PyDict_SetItemString(dict, "cat", cat_fee);
            break;
        case INSTANT_NODE:
            PyDict_SetItemString(dict, "ph", ph_i);
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
        Py_DECREF(dict);
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

    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
        Py_ssize_t pos = 0;
        PyObject* key = NULL;
        PyObject* value = NULL;
        while (PyDict_Next(task_dict, &pos, &key, &value)) {
            PyObject* dict = PyDict_New();
            PyObject* args = PyDict_New();
            PyObject* tid = key;
            PyObject* thread_name_string = PyUnicode_FromString("thread_name");

            PyDict_SetItemString(dict, "ph", ph_M);
            PyDict_SetItemString(dict, "pid", pid);
            PyDict_SetItemString(dict, "tid", tid);
            PyDict_SetItemString(dict, "name", thread_name_string);
            Py_DECREF(thread_name_string);
            PyDict_SetItemString(args, "name", value);
            PyDict_SetItemString(dict, "args", args);
            Py_DECREF(args);
            PyList_Append(lst, dict);
        }
    }

    verbose_printf(self, 1, "Loading finish                                        \n");
    Py_DECREF(pid);
    Py_DECREF(cat_fee);
    Py_DECREF(cat_instant);
    Py_DECREF(ph_B);
    Py_DECREF(ph_i);
    Py_DECREF(ph_X);
    Py_DECREF(ph_C);
    Py_DECREF(ph_M);
    Py_DECREF(func_name_dict);
    self->buffer_tail_idx = self->buffer_head_idx;
    SNAPTRACE_THREAD_PROTECT_END(self);
    return lst;
}

static PyObject*
tracer_dump(TracerObject* self, PyObject* args, PyObject* kw)
{
    const char* filename = NULL;
    int sanitize_function_name = 0;
    static char* kwlist[] = {"filename", "sanitize_function_name", NULL};
    FILE* fptr = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kw, "s|p", kwlist,
                                     &filename, &sanitize_function_name)) {
        return NULL;
    }
    fptr = fopen(filename, "w");
    if (!fptr) {
        PyErr_Format(PyExc_ValueError, "Can't open file %s to write", filename);
        return NULL;
    }

    fprintf(fptr, "{\"traceEvents\":[");

    SNAPTRACE_THREAD_PROTECT_START(self);
    struct EventNode* curr = self->buffer + self->buffer_head_idx;
    unsigned long pid = 0;
    uint8_t overflowed = ((self->buffer_tail_idx + 1) % self->buffer_size) == self->buffer_head_idx;
    struct MetadataNode* metadata_node = NULL;
    PyObject* task_dict = NULL;

    if (self->fix_pid > 0) {
        pid = self->fix_pid;
    } else {
#if _WIN32
        pid = GetCurrentProcessId();
#else
        pid = getpid();
#endif
    }

    // == Load the metadata first ==
    //    Process Name
    {
        PyObject* process_name = NULL;
        if (self->process_name) {
            process_name = Py_NewRef(self->process_name);
        } else {
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
            process_name = PyObject_GetAttrString(current_process, "name");
            Py_DECREF(current_process_method);
            Py_DECREF(current_process);
        }

        fprintf(fptr, "{\"ph\":\"M\",\"pid\":%lu,\"tid\":%lu,\"name\":\"process_name\",\"args\":{\"name\":\"",
                pid, pid);
        fprint_escape(fptr, PyUnicode_AsUTF8(process_name));
        fprintf(fptr, "\"}},");
        Py_DECREF(process_name);
    }

    //    Thread Name
    metadata_node = self->metadata_head;
    while (metadata_node) {
        fprintf(fptr, "{\"ph\":\"M\",\"pid\":%lu,\"tid\":%lu,\"name\":\"thread_name\",\"args\":{\"name\":\"",
                pid, metadata_node->tid);
        fprint_escape(fptr, PyUnicode_AsUTF8(metadata_node->name));
        fprintf(fptr, "\"}},");
        metadata_node = metadata_node->next;
    }

    // Task Name if using LOG_ASYNC
    // We need to make up some thread id for the task
    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
        task_dict = PyDict_New();
    }

    while (curr != self->buffer + self->buffer_tail_idx) {
        struct EventNode* node = curr;
        long long ts_long = system_ts_to_ns(node->ts);
        unsigned long tid = node->tid;

        if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
            if (curr->data.fee.asyncio_task != NULL) {
                tid = (unsigned long)(((uintptr_t)curr->data.fee.asyncio_task) & 0xffffff);
                PyObject* task_id = PyLong_FromLong(tid);
                if (!PyDict_Contains(task_dict, task_id)) {
                    PyObject* task_name = NULL;
                    if (PyObject_HasAttrString(curr->data.fee.asyncio_task, "get_name")) {
                        PyObject* task_name_method = PyObject_GetAttrString(curr->data.fee.asyncio_task, "get_name");
                        task_name = PyObject_CallObject(task_name_method, NULL);
                        Py_DECREF(task_name_method);
                    } else if (PyObject_HasAttrString(curr->data.fee.asyncio_task, "name")) {
                        task_name = PyObject_GetAttrString(curr->data.fee.asyncio_task, "name");
                    } else {
                        task_name = PyUnicode_FromString("Task");
                    }
                    PyDict_SetItem(task_dict, task_id, task_name);
                    Py_DECREF(task_name);
                }
                Py_DECREF(task_id);
            }
        }
        if (node->ntype != RAW_NODE) {
            // printf("%f") is about 10x slower than print("%d")
            fprintf(fptr, "{\"pid\":%lu,\"tid\":%lu,\"ts\":%lld.%03lld,", pid, tid, ts_long / 1000, ts_long % 1000);
        }

        switch (node->ntype) {
        case FEE_NODE:
            ;
            long long dur_long = dur_ts_to_ns(node->data.fee.dur);
            char ph = 'X';
            if (node->data.fee.type == PyTrace_CALL || node->data.fee.type == PyTrace_C_CALL) {
                ph = 'B';
            }
            fprintf(fptr, "\"ph\":\"%c\",\"cat\":\"fee\",\"dur\":%lld.%03lld,\"name\":\"", ph, dur_long / 1000, dur_long % 1000);
            fprintfeename(fptr, node, sanitize_function_name);
            fputc('\"', fptr);

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
                fprintf(fptr, ",\"args\":");
                fprintjson(fptr, arg_dict);
                Py_DECREF(arg_dict);
            }
            break;
        case INSTANT_NODE:
            fprintf(fptr, "\"ph\":\"i\",\"cat\":\"instant\",\"name\":\"");
            fprint_escape(fptr, PyUnicode_AsUTF8(node->data.instant.name));
            if (node->data.instant.args == Py_None) {
                fprintf(fptr, "\",\"s\":\"%s\"", PyUnicode_AsUTF8(node->data.instant.scope));
            } else {
                fprintf(fptr, "\",\"s\":\"%s\",\"args\":", PyUnicode_AsUTF8(node->data.instant.scope));
                fprintjson(fptr, node->data.instant.args);
            }
            break;
        case COUNTER_NODE:
            fprintf(fptr, "\"ph\":\"C\",\"name\":\"");
            fprint_escape(fptr, PyUnicode_AsUTF8(node->data.counter.name));
            fprintf(fptr, "\",\"args\":");
            fprintjson(fptr, node->data.counter.args);
            break;
        case OBJECT_NODE:
            fprintf(fptr, "\"ph\":\"%s\",\"id\":\"%s\",\"name\":\"",
                    PyUnicode_AsUTF8(node->data.object.ph), PyUnicode_AsUTF8(node->data.object.id));
            fprint_escape(fptr, PyUnicode_AsUTF8(node->data.object.name));
            fputc('\"', fptr);
            if (!(node->data.object.args == Py_None)) {
                fprintf(fptr, ",\"args\":");
                fprintjson(fptr, node->data.object.args);
            }
            break;
        case RAW_NODE:
            // We still need to tid from node and we need the pid
            ;
            PyObject* py_pid = PyLong_FromLong(pid);
            PyObject* py_tid = PyLong_FromLong(node->tid);
            PyObject* dict = node->data.raw;

            PyDict_SetItemString(dict, "pid", py_pid);
            PyDict_SetItemString(dict, "tid", py_tid);
            fprintjson(fptr, dict);
            fputc(',', fptr);
            Py_DECREF(py_pid);
            Py_DECREF(py_tid);
            break;
        default:
            printf("Unknown Node Type!\n");
            exit(1);
        }
        if (node->ntype != RAW_NODE) {
            fputs("},", fptr);
        }
        clear_node(node);
        curr = curr + 1;
        if (curr == self->buffer + self->buffer_size) {
            curr = self->buffer;
        }
    }

    if (CHECK_FLAG(self->check_flags, SNAPTRACE_LOG_ASYNC)) {
        Py_ssize_t pos = 0;
        PyObject* key = NULL;
        PyObject* value = NULL;
        while (PyDict_Next(task_dict, &pos, &key, &value)) {
            PyObject* tid_repr = PyObject_Repr(key);
            fprintf(fptr, "{\"ph\":\"M\",\"pid\":%lu,\"tid\":%s,\"name\":\"thread_name\",\"args\":{\"name\":\"%s\"}},",
                    pid, PyUnicode_AsUTF8(tid_repr), PyUnicode_AsUTF8(value));
            Py_DECREF(tid_repr);
        }
        Py_DECREF(task_dict);
    }

    self->buffer_tail_idx = self->buffer_head_idx;
    fseek(fptr, -1, SEEK_CUR);
    fprintf(fptr, "], \"viztracer_metadata\": {\"overflow\":%s}}", overflowed? "true": "false");
    fclose(fptr);
    SNAPTRACE_THREAD_PROTECT_END(self);
    Py_RETURN_NONE;
}

static PyObject*
tracer_clear(TracerObject* self, PyObject* Py_UNUSED(unused))
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
tracer_setpid(TracerObject* self, PyObject* args)
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
tracer_getts(TracerObject* self, PyObject* Py_UNUSED(unused))
{
    struct ThreadInfo* info = get_thread_info(self);
    int64_t ts = get_ts(info);
    double us = system_ts_to_us(ts);

    return PyFloat_FromDouble(us);
}

static PyObject*
tracer_getbasetime(TracerObject* self, PyObject* Py_UNUSED(unused))
{
    return PyLong_FromLongLong(get_base_time_ns());
}

static PyObject*
tracer_setcurrstack(TracerObject* self, PyObject* stack_depth)
{
    struct ThreadInfo* info = get_thread_info(self);

    if (!PyLong_Check(stack_depth)) {
        PyErr_SetString(PyExc_TypeError, "stack_depth must be an integer");
        return NULL;
    }

    info->curr_stack_depth = PyLong_AsLong(stack_depth);

    Py_RETURN_NONE;
}

static PyObject*
tracer_addinstant(TracerObject* self, PyObject* args, PyObject* kw)
{
    PyObject* name = NULL;
    PyObject* instant_args = NULL;
    PyObject* scope = NULL;
    struct ThreadInfo* info = get_thread_info(self);
    struct EventNode* node = NULL;
    static char* kwlist[] = {"name", "args", "scope", NULL};
    const char* allowed_scope[] = {"g", "p", "t"};

    if (!self->collecting) {
        Py_RETURN_NONE;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kw, "O|OO", kwlist,
                                     &name, &instant_args, &scope)) {
        return NULL;
    }

    if (!instant_args) {
        instant_args = Py_None;
    }

    if (!scope) {
        scope = PyUnicode_FromString("g");
    } else {
        if (!PyUnicode_CheckExact(scope)) {
            PyErr_SetString(PyExc_TypeError, "Scope must be a string");
            return NULL;
        }
        for (int i = 0; i < 3; i++) {
            if (strcmp(PyUnicode_AsUTF8(scope), allowed_scope[i]) == 0) {
                break;
            }
            if (i == 2) {
                PyErr_SetString(PyExc_ValueError, "Scope must be one of 'g', 'p', 't'");
                return NULL;
            }
        }
        Py_INCREF(scope);
    }

    node = get_next_node(self);
    node->ntype = INSTANT_NODE;
    node->tid = info->tid;
    node->ts = get_ts(info);
    node->data.instant.name = Py_NewRef(name);
    node->data.instant.args = Py_NewRef(instant_args);
    node->data.instant.scope = scope;

    Py_RETURN_NONE;
}

static PyObject*
tracer_addfunctionarg(TracerObject* self, PyObject* args, PyObject* kw)
{
    PyObject* key = NULL;
    PyObject* value = NULL;
    static char* kwlist[] = {"key", "value", NULL};
    struct ThreadInfo* info = get_thread_info(self);

    if (!self->collecting) {
        Py_RETURN_NONE;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kw, "OO", kwlist, &key, &value)) {
        return NULL;
    }

    struct FunctionNode* fnode = info->stack_top;
    if (!fnode->args) {
        fnode->args = PyDict_New();
    }

    PyDict_SetItem(fnode->args, key, value);

    Py_RETURN_NONE;
}

static PyObject*
tracer_addcounter(TracerObject* self, PyObject* args, PyObject* kw)
{
    PyObject* name = NULL;
    PyObject* counter_args = NULL;
    static char* kwlist[] = {"name", "args", NULL};
    struct ThreadInfo* info = get_thread_info(self);
    struct EventNode* node = NULL;

    if (!self->collecting) {
        Py_RETURN_NONE;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kw, "OO", kwlist,
                                     &name, &counter_args)) {
        return NULL;
    }

    node = get_next_node(self);
    node->ntype = COUNTER_NODE;
    node->tid = info->tid;
    node->ts = get_ts(info);
    node->data.counter.name = Py_NewRef(name);
    node->data.counter.args = Py_NewRef(counter_args);

    Py_RETURN_NONE;
}

static PyObject*
tracer_addobject(TracerObject* self, PyObject* args, PyObject* kw)
{
    PyObject* ph = NULL;
    PyObject* id = NULL;
    PyObject* name = NULL;
    PyObject* object_args = NULL;
    static char* kwlist[] = {"ph", "obj_id", "name", "args", NULL};
    struct ThreadInfo* info = get_thread_info(self);
    struct EventNode* node = NULL;

    if (!self->collecting) {
        Py_RETURN_NONE;
    }

    if (!PyArg_ParseTupleAndKeywords(args, kw, "OOO|O", kwlist,
                                     &ph, &id, &name, &object_args)) {
        return NULL;
    }

    if (!object_args) {
        object_args = Py_None;
    }

    node = get_next_node(self);
    node->ntype = OBJECT_NODE;
    node->tid = info->tid;
    node->ts = get_ts(info);
    node->data.object.ph = Py_NewRef(ph);
    node->data.object.id = Py_NewRef(id);
    node->data.object.name = Py_NewRef(name);
    node->data.object.args = Py_NewRef(object_args);

    Py_RETURN_NONE;
}

static PyObject*
tracer_addraw(TracerObject* self, PyObject* args, PyObject* kw)
{
    PyObject* raw = NULL;
    static char* kwlist[] = {"raw", NULL};
    struct ThreadInfo* info = get_thread_info(self);
    struct EventNode* node = NULL;

    if (!PyArg_ParseTupleAndKeywords(args, kw, "O", kwlist, &raw)) {
        return NULL;
    }

    node = get_next_node(self);
    node->tid = info->tid;
    node->ntype = RAW_NODE;
    node->data.raw = Py_NewRef(raw);

    Py_RETURN_NONE;
}

static PyObject*
tracer_setignorestackcounter(TracerObject* self, PyObject* value)
{
    int current_value = 0;
    struct ThreadInfo* info = get_thread_info(self);

    if (!PyLong_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "value must be an integer");
        return NULL;
    }

    current_value = info->ignore_stack_depth;
    // +1 to compensate for this call so when it returns, the value is correct
    info->ignore_stack_depth = PyLong_AsLong(value) + 1;

    // -1 is the actual ignore stack depth before this call
    return Py_BuildValue("i", current_value - 1);
}

static PyObject*
tracer_getfunctionarg(TracerObject* self, PyObject* Py_UNUSED(unused))
{
    struct ThreadInfo* info = get_thread_info(self);

    struct FunctionNode* fnode = info->stack_top;
    if (!fnode->args) {
        Py_RETURN_NONE;
    }

    return Py_NewRef(fnode->args);
}

static PyMethodDef Tracer_methods[] = {
    {"threadtracefunc", (PyCFunction)tracer_threadtracefunc, METH_VARARGS, "trace function"},
    {"start", (PyCFunction)tracer_start, METH_NOARGS, "start profiling"},
    {"stop", (PyCFunction)tracer_stop, METH_O, "stop profiling"},
    {"load", (PyCFunction)tracer_load, METH_NOARGS, "load buffer"},
    {"dump", (PyCFunction)tracer_dump, METH_VARARGS|METH_KEYWORDS, "dump buffer to file"},
    {"clear", (PyCFunction)tracer_clear, METH_NOARGS, "clear buffer"},
    {"setpid", (PyCFunction)tracer_setpid, METH_VARARGS, "set fixed pid"},
    {"add_instant", (PyCFunction)tracer_addinstant, METH_VARARGS|METH_KEYWORDS, "add instant event"},
    {"add_counter", (PyCFunction)tracer_addcounter, METH_VARARGS|METH_KEYWORDS, "add counter event"},
    {"add_object", (PyCFunction)tracer_addobject, METH_VARARGS|METH_KEYWORDS, "add object event"},
    {"add_raw", (PyCFunction)tracer_addraw, METH_VARARGS|METH_KEYWORDS, "add raw event"},
    {"add_func_args", (PyCFunction)tracer_addfunctionarg, METH_VARARGS|METH_KEYWORDS, "add function arg"},
    {"get_func_args", (PyCFunction)tracer_getfunctionarg, METH_NOARGS, "get current function arg"},
    {"getts", (PyCFunction)tracer_getts, METH_NOARGS, "get timestamp"},
    {"get_base_time", (PyCFunction)tracer_getbasetime, METH_NOARGS, "get base time in nanoseconds"},
    {"_set_curr_stack_depth", (PyCFunction)tracer_setcurrstack, METH_O, "set current stack depth"},
    {"pause", (PyCFunction)tracer_pause, METH_NOARGS, "pause profiling"},
    {"resume", (PyCFunction)tracer_resume, METH_NOARGS, "resume profiling"},
    {"setignorestackcounter", (PyCFunction)tracer_setignorestackcounter, METH_O, "reset ignore stack depth"},
    {NULL, NULL, 0, NULL}
};

// ===========================================================================
// snaptrace.Tracer internals
// ===========================================================================

static PyObject* 
Tracer_New(PyTypeObject* type, PyObject* args, PyObject* kwargs)
{
    TracerObject* self = (TracerObject*) type->tp_alloc(type, 0);
    if (self) {
        self->collecting = 0;
        self->fix_pid = 0;
        self->total_entries = 0;
        self->check_flags = 0;
        self->verbose = 0;
        self->lib_file_path = NULL;
        self->max_stack_depth = 0;
        self->include_files = NULL;
        self->exclude_files = NULL;
        self->min_duration = 0;
        self->buffer = NULL;
        self->buffer_head_idx = 0;
        self->buffer_tail_idx = 0;
        self->metadata_head = NULL;
    }

    return (PyObject*) self;
}

static int
Tracer_Init(TracerObject* self, PyObject* args, PyObject* kwargs)
{
    if (!PyArg_ParseTuple(args, "l", &self->buffer_size)) {
        PyErr_SetString(PyExc_TypeError, "You need to specify buffer size when initializing Tracer");
        return -1;
    }

    // We need an extra slot for circular buffer
    self->buffer_size += 1;
    self->buffer = (struct EventNode*) PyMem_Calloc(self->buffer_size, sizeof(struct EventNode));
    if (!self->buffer) {
        PyErr_NoMemory();
        return -1;
    }

#if _WIN32
    if ((self->dwTlsIndex = TlsAlloc()) == TLS_OUT_OF_INDEXES) {
        printf("Error on TLS!\n");
        exit(-1);
    }
#else
    if (pthread_key_create(&self->thread_key, snaptrace_threaddestructor)) {
        perror("Failed to create Tss_Key");
        exit(-1);
    }
#endif

    snaptrace_createthreadinfo(self);
    // Python: threading.setprofile(tracefunc)
    {
        PyObject* handler = PyCFunction_New(&Tracer_methods[0], (PyObject*)self);

        if (PyObject_CallMethod(threading_module, "setprofile", "N", handler) == NULL) {
            perror("Failed to call threading.setprofile() properly");
            exit(-1);
        }
    }

    PyEval_SetProfile(tracer_tracefunc, (PyObject*)self);

    return 0;
}

static void
Tracer_dealloc(TracerObject* self)
{
    tracer_clear(self, NULL);
    if (self->lib_file_path) {
        PyMem_FREE(self->lib_file_path);
    }
    Py_XDECREF(self->include_files);
    Py_XDECREF(self->exclude_files);
    PyMem_FREE(self->buffer);

    struct MetadataNode* node = self->metadata_head;
    struct MetadataNode* prev = NULL;
    while (node) {
        prev = node;
        Py_CLEAR(node->name);
        node = node->next;
        PyMem_FREE(prev);
    }

    // threading.setprofile(None)
    // It's possible that during deallocation phase threading module has released setprofile
    // and we should be okay with that.
    PyObject* result = PyObject_CallMethod(threading_module, "setprofile", "O", Py_None);
    if (result != NULL) {
        Py_DECREF(result);
    }

    Py_TYPE(self)->tp_free((PyObject*) self);
}

// ================================================================
// snaptrace.Tracer Definition
// ================================================================

// We define getsetters in another file
extern PyGetSetDef Tracer_getsetters[];

static PyTypeObject TracerType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "snaptrace.Tracer",
    .tp_doc = "Tracer",
    .tp_basicsize = sizeof(TracerObject),
    .tp_itemsize = 0,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = Tracer_New,
    .tp_init = (initproc) Tracer_Init,
    .tp_dealloc = (destructor) Tracer_dealloc,
    .tp_methods = Tracer_methods,
    .tp_getset = Tracer_getsetters,
};

// ================================================================
// snaptrace Module Functions
// ================================================================

void
snaptrace_free(void* Py_UNUSED(unused)) {
    quicktime_free();
    Py_CLEAR(threading_module);
    Py_CLEAR(multiprocessing_module);
    Py_CLEAR(asyncio_module);
    Py_CLEAR(asyncio_tasks_module);
    Py_CLEAR(curr_task_getters[0]);
    Py_CLEAR(trio_lowlevel_module);
    Py_CLEAR(curr_task_getters[1]);
    Py_CLEAR(json_module);
}

// ================================================================
// snaptrace Module Definition
// ================================================================

static struct PyModuleDef snaptracemodule = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "viztracer.snaptrace",
    .m_size = -1,
    .m_free = snaptrace_free,
};

// ================================================================
// Python Interface
// ================================================================

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

#ifdef Py_GIL_DISABLED
    PyUnstable_Module_SetGIL(m, Py_MOD_GIL_NOT_USED);
#endif

    Py_INCREF(&TracerType);
    if (PyModule_AddObject(m, "Tracer", (PyObject*) &TracerType) < 0) {
        Py_DECREF(&TracerType);
        Py_DECREF(m);
        return NULL;
    }

    threading_module = PyImport_ImportModule("threading");
    multiprocessing_module = PyImport_ImportModule("multiprocessing");
    asyncio_module = PyImport_ImportModule("asyncio");
    asyncio_tasks_module = PyImport_AddModule("asyncio.tasks");
    if (PyObject_HasAttrString(asyncio_tasks_module, "current_task")) {
        curr_task_getters[0] = PyObject_GetAttrString(asyncio_tasks_module, "current_task");
    }
    if ((trio_module = PyImport_ImportModule("trio"))) {
        trio_lowlevel_module = PyImport_AddModule("trio.lowlevel");
        curr_task_getters[1] = PyObject_GetAttrString(trio_lowlevel_module, "current_task");
    } else {
        PyErr_Clear();
    }
    json_module = PyImport_ImportModule("json");

    quicktime_init();

    return m;
}
