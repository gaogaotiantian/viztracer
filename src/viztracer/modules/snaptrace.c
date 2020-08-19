#define PY_SSIZE_T_CLEAN
#include <stdlib.h>
#include <Python.h>
#include <frameobject.h>
#include <time.h>
#include <pthread.h>
#include "snaptrace.h"

// Function declarations

int snaptrace_tracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg);
static PyObject* snaptrace_threadtracefunc(PyObject* obj, PyObject* args);
static PyObject* snaptrace_start(PyObject* self, PyObject* args);
static PyObject* snaptrace_stop(PyObject* self, PyObject* args);
static PyObject* snaptrace_pause(PyObject* self, PyObject* args);
static PyObject* snaptrace_resume(PyObject* self, PyObject* args);
static PyObject* snaptrace_load(PyObject* self, PyObject* args);
static PyObject* snaptrace_clear(PyObject* self, PyObject* args);
static PyObject* snaptrace_cleanup(PyObject* self, PyObject* args);
static PyObject* snaptrace_config(PyObject* self, PyObject* args, PyObject* kw);
static PyObject* snaptrace_addinstant(PyObject* self, PyObject* args);
static void snaptrace_threaddestructor(void* key);
static struct ThreadInfo* snaptrace_createthreadinfo(void);

// the key is used to locate thread specific info
static pthread_key_t thread_key = 0;
// We need to ignore the first events until we get an entry
int collecting = 0;
unsigned long total_entries = 0;
unsigned int check_flags = 0;

int verbose = 0;
char* lib_file_path = NULL;
int max_stack_depth = -1;
PyObject* include_files = NULL;
PyObject* exclude_files = NULL;

PyObject* thread_module = NULL;

enum NodeType {
    EVENT_NODE = 0,
    FEE_NODE = 1,
    INSTANT_NODE = 2
};

struct FEEData {
    PyObject* file_name;
    PyObject* class_name;
    PyObject* func_name;
    int type;
    long tid;
    double dur;
    struct EventNode* parent;
};

struct InstantData {
    PyObject* name;
    PyObject* args;
    PyObject* scope;
};

struct EventNode {
    int ntype;
    struct EventNode* next;
    struct EventNode* prev;
    double ts;
    union {
        struct FEEData fee;
        struct InstantData instant;
    } data;
} *buffer_head, *buffer_tail;


struct ThreadInfo {
    int paused;
    int curr_stack_depth;
    int ignore_stack_depth;
    struct EventNode* stack_top;
};

// Utility functions

static void Print_Py(PyObject* o)
{
    printf("%s\n", PyUnicode_AsUTF8(PyObject_Repr(o)));
}

static inline double get_ts()
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return ((double)t.tv_sec * 1e9 + t.tv_nsec);
}

static inline struct EventNode* get_next_node()
{
    struct EventNode* node = NULL;

    if (buffer_tail->next) {
        node = buffer_tail->next;
    } else {
        node = (struct EventNode*)PyMem_Calloc(1, sizeof(struct EventNode));
        node->next = NULL;
        buffer_tail->next = node;
        node->prev = buffer_tail;
    }
    buffer_tail = node;

    return node;
}

static void verbose_printf(int v, const char* fmt, ...)
{
    va_list args;
    if (verbose >= v) {
        va_start(args, fmt);
        vprintf(fmt, args);
        va_end(args);
        fflush(stdout);
    }
}

// target and prefix has to be NULL-terminated
static int startswith(const char* target, const char* prefix)
{
    while(*target != 0 && *prefix != 0) {
        if (*target != *prefix) {
            return 0;
        }
        target++;
        prefix++;
    }

    return (*prefix) == 0;
}

// ================================================================
// Python interface
// ================================================================

static PyMethodDef SnaptraceMethods[] = {
    {"threadtracefunc", snaptrace_threadtracefunc, METH_VARARGS, "trace function"},
    {"start", snaptrace_start, METH_VARARGS, "start profiling"},
    {"stop", snaptrace_stop, METH_VARARGS, "stop profiling"},
    {"pause", snaptrace_pause, METH_VARARGS, "pause profiling"},
    {"resume", snaptrace_resume, METH_VARARGS, "resume profiling"},
    {"load", snaptrace_load, METH_VARARGS, "load buffer"},
    {"clear", snaptrace_clear, METH_VARARGS, "clear buffer"},
    {"cleanup", snaptrace_cleanup, METH_VARARGS, "free the memory allocated"},
    {"config", (PyCFunction)snaptrace_config, METH_VARARGS|METH_KEYWORDS, "config the snaptrace module"},
    {"addinstant", snaptrace_addinstant, METH_VARARGS, "add instant event"},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef snaptracemodule = {
    PyModuleDef_HEAD_INIT,
    "viztracer.snaptrace",
    NULL,
    -1,
    SnaptraceMethods
};

// =============================================================================
// Tracing function, triggered when FEE
// =============================================================================

int
snaptrace_tracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg)
{
    if (what == PyTrace_CALL || what == PyTrace_RETURN || 
            (!CHECK_FLAG(check_flags, SNAPTRACE_IGNORE_C_FUNCTION) && (what == PyTrace_C_CALL || what == PyTrace_C_RETURN || what == PyTrace_C_EXCEPTION))) {
        struct EventNode* node = NULL;
        struct ThreadInfo* info = pthread_getspecific(thread_key);

        if (info->paused) {
            return 0;
        }

        if (!info->stack_top && (what == PyTrace_C_RETURN || what == PyTrace_RETURN || what == PyTrace_C_EXCEPTION)) {
            return 0;
        }

        // Check max stack depth
        if (CHECK_FLAG(check_flags, SNAPTRACE_MAX_STACK_DEPTH)) {
            if (what == PyTrace_CALL || what == PyTrace_C_CALL) {
                info->curr_stack_depth += 1;
                if (info->curr_stack_depth > max_stack_depth) {
                    return 0;
                }
            } else if (what == PyTrace_RETURN || what == PyTrace_C_RETURN || what == PyTrace_C_EXCEPTION) {
                info->curr_stack_depth -= 1;
                if (info->curr_stack_depth + 1 > max_stack_depth) {
                    return 0;
                }
            }
        }

        // Check include/exclude files
        if (CHECK_FLAG(check_flags, SNAPTRACE_INCLUDE_FILES | SNAPTRACE_EXCLUDE_FILES)) {
            if (what == PyTrace_CALL && info->ignore_stack_depth > 0) {
                info->ignore_stack_depth += 1;
                return 0;
            } else if (what == PyTrace_RETURN && info->ignore_stack_depth > 0) {
                info->ignore_stack_depth -= 1;
                return 0;
            }
            if (info->ignore_stack_depth == 0) {
                PyObject* files = NULL;
                int record = 0;
                int is_include = CHECK_FLAG(check_flags, SNAPTRACE_INCLUDE_FILES);
                if (is_include) {
                    files = include_files;
                    record = 0;
                } else {
                    files = exclude_files;
                    record = 1;
                }
                Py_ssize_t length = PyList_GET_SIZE(files);
                PyObject* name = frame->f_code->co_filename;
                char* path = realpath(PyUnicode_AsUTF8(name), NULL);
                if (path) {
                    for (int i = 0; i < length; i++) {
                        PyObject* f = PyList_GET_ITEM(files, i);
                        if (startswith(path, PyUnicode_AsUTF8(f))) {
                            record = 1 - record;
                            break;
                        }
                    }
                    free(path);
                }
                if (record == 0) {
                    info->ignore_stack_depth += 1;
                    return 0;
                }
            } else {
                return 0;
            }
        }

        // Exclude Self
        if (what == PyTrace_C_CALL || what == PyTrace_C_RETURN || what == PyTrace_C_EXCEPTION) {
            PyCFunctionObject* func = (PyCFunctionObject*) arg;
            if (func->m_module) {
                if (strcmp(PyUnicode_AsUTF8(func->m_module), snaptracemodule.m_name) == 0) {
                    return 0;
                }
            }
        } else if (what == PyTrace_CALL || what == PyTrace_RETURN) {
            PyObject* file_name = frame->f_code->co_filename;
            if (lib_file_path && startswith(PyUnicode_AsUTF8(file_name), lib_file_path)) {
                return 0;
            }
        }

        if (what == PyTrace_CALL || what == PyTrace_C_CALL) {
            // If it's a call, we need a new node, and we need to update the stack
            node = get_next_node();
            node->ntype = FEE_NODE;
            node->ts = get_ts();
            node->data.fee.dur = 0;
            node->data.fee.parent = info->stack_top;
            info->stack_top = node;
            node->data.fee.type = what;
            node->data.fee.tid = pthread_self();
            if (what == PyTrace_CALL) {
                node->data.fee.file_name = frame->f_code->co_filename;
                Py_INCREF(node->data.fee.file_name);
                node->data.fee.class_name = Py_None;
                Py_INCREF(Py_None);
                for (int i = 0; i < frame->f_code->co_nlocals; i++) {
                    PyObject* name = PyTuple_GET_ITEM(frame->f_code->co_varnames, i);
                    if (strcmp("self", PyUnicode_AsUTF8(name)) == 0) {
                        // When self object is just created in __new__, it's possible that the value is NULL
                        if (frame->f_localsplus[i]) {
                            node->data.fee.class_name = PyUnicode_FromString(frame->f_localsplus[i]->ob_type->tp_name);
                            Py_DECREF(Py_None);
                        }
                        break;
                    }
                }
                node->data.fee.func_name = frame->f_code->co_name;
                Py_INCREF(node->data.fee.func_name);
            } else if (what == PyTrace_C_CALL) {
                PyCFunctionObject* func = (PyCFunctionObject*) arg;
                node->data.fee.func_name = PyUnicode_FromString(func->m_ml->ml_name);
                if (func->m_module) {
                    node->data.fee.class_name = func->m_module;
                } else {
                    node->data.fee.class_name = PyUnicode_FromString(func->m_self->ob_type->tp_name);
                }
            } 
        } else if (what == PyTrace_RETURN || PyTrace_C_EXCEPTION || PyTrace_C_RETURN) {
            struct EventNode* stack_top = info->stack_top;
            if (stack_top) {
                stack_top->data.fee.dur = get_ts() - stack_top->ts;
                info->stack_top = stack_top->data.fee.parent;
            } else {
                printf("return out of stack\n");
            }
            return 0;
        } else {
            printf("Unexpected event!\n");
        }
        total_entries += 1;
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
    snaptrace_createthreadinfo();
    PyEval_SetProfile(snaptrace_tracefunc, NULL);
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
snaptrace_start(PyObject* self, PyObject* args)
{
    snaptrace_createthreadinfo();
    // Python: threading.setprofile(tracefunc)
    {
        PyObject* threading = PyImport_ImportModule("threading");
        assert(threading != NULL);
        PyObject* setprofile = PyObject_GetAttrString(threading, "setprofile");

        PyObject* handler = PyCFunction_New(&SnaptraceMethods[0], NULL);
        PyObject* callback = Py_BuildValue("(O)", handler);

        if (PyObject_CallObject(setprofile, callback) == NULL) {
            perror("Failed to call threading.setprofile() properly");
            exit(-1);
        }
    }
    PyEval_SetProfile(snaptrace_tracefunc, NULL);

    collecting = 1;

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_stop(PyObject* self, PyObject* args)
{
    PyEval_SetProfile(NULL, NULL);
    if (collecting == 1) {
        // If we are collecting, throw away the last event if it's a call
        // if it's an entry. because it's entry of stop() function
        struct EventNode* node = buffer_tail;
        if (node->ntype == FEE_NODE && node->data.fee.type == PyTrace_CALL) {
            Py_DECREF(node->data.fee.file_name);
            Py_DECREF(node->data.fee.class_name);
            Py_DECREF(node->data.fee.func_name);
            buffer_tail = buffer_tail->prev;
            collecting = 0;
        }
        struct ThreadInfo* info = pthread_getspecific(thread_key);
        snaptrace_threaddestructor(info);
    }
    
    Py_RETURN_NONE;
}

static PyObject*
snaptrace_pause(PyObject* self, PyObject* args)
{
    if (collecting) {
        struct ThreadInfo* info = pthread_getspecific(thread_key);
        if (info) {
            info->paused += 1;
        }
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_resume(PyObject* self, PyObject* args)
{
    if (collecting) {
        struct ThreadInfo* info = pthread_getspecific(thread_key);
        if (info && info->paused > 0) {
            info->paused -= 1;
        }
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_load(PyObject* self, PyObject* args)
{
    PyObject* lst = PyList_New(0);
    struct EventNode* curr = buffer_head;
    PyObject* pid = PyLong_FromLong(getpid());
    PyObject* cat_fee = PyUnicode_FromString("FEE");
    PyObject* cat_instant = PyUnicode_FromString("INSTANT");
    PyObject* ph_B = PyUnicode_FromString("B");
    PyObject* ph_E = PyUnicode_FromString("E");
    PyObject* ph_I = PyUnicode_FromString("I");
    PyObject* ph_X = PyUnicode_FromString("X");
    unsigned long counter = 0;
    unsigned long prev_counter = 0;
    PyObject* prev_dict = NULL;
    while (curr != buffer_tail && curr->next) {
        struct EventNode* node = curr->next;
        PyObject* dict = PyDict_New();
        PyObject* name = NULL;
        PyObject* tid = PyLong_FromLong(node->data.fee.tid);
        PyObject* ts = PyFloat_FromDouble(node->ts);
        PyObject* dur = PyFloat_FromDouble(node->data.fee.dur);

        PyDict_SetItemString(dict, "pid", pid);
        PyDict_SetItemString(dict, "tid", tid);
        Py_DECREF(tid);
        PyDict_SetItemString(dict, "ts", ts);
        Py_DECREF(ts);
        PyDict_SetItemString(dict, "dur", dur);
        Py_DECREF(dur);

        switch (node->ntype) {
        case FEE_NODE:
            if (node->data.fee.type == PyTrace_CALL || node->data.fee.type == PyTrace_RETURN) {
                    if (node->data.fee.class_name == Py_None) {
                        name = PyUnicode_FromFormat("%s.%s", 
                                PyUnicode_AsUTF8(node->data.fee.file_name), 
                                PyUnicode_AsUTF8(node->data.fee.func_name));
                    } else {
                        name = PyUnicode_FromFormat("%s.%s.%s", 
                                PyUnicode_AsUTF8(node->data.fee.file_name), 
                                PyUnicode_AsUTF8(node->data.fee.class_name), 
                                PyUnicode_AsUTF8(node->data.fee.func_name));
                    }
            } else {
                name = node->data.fee.func_name;
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
            PyDict_SetItemString(dict, "name", name);
            Py_DECREF(name);
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
        default:
            printf("Unknown Node Type!\n");
            exit(1);
        }
        PyList_Append(lst, dict);
        prev_dict = dict;
        curr = curr->next;

        counter += 1;
        if (counter - prev_counter > 10000 && (counter - prev_counter) / ((1 + total_entries)/100) > 0) {
            verbose_printf(1, "Loading data, %lu / %lu\r", counter, total_entries);
            prev_counter = counter;
        }
    }
    verbose_printf(1, "Loading finish                                        \n");
    Py_DECREF(pid);
    Py_DECREF(cat_fee);
    Py_DECREF(cat_instant);
    Py_DECREF(ph_B);
    Py_DECREF(ph_E);
    Py_DECREF(ph_I);
    Py_DECREF(ph_X);
    buffer_tail = buffer_head;
    return lst;
}

static PyObject*
snaptrace_clear(PyObject* self, PyObject* args)
{
    struct EventNode* curr = buffer_head;
    while (curr != buffer_tail && curr->next) {
        struct EventNode* node = curr->next;
        switch (node->ntype) {
        case FEE_NODE:
            Py_DECREF(node->data.fee.file_name);
            Py_DECREF(node->data.fee.class_name);
            Py_DECREF(node->data.fee.func_name);
            break;
        default:
            printf("Unknown Node Type!\n");
            exit(1);
        }
        curr = curr->next;
    }
    buffer_tail = buffer_head;

    Py_RETURN_NONE;
}

static PyObject* 
snaptrace_cleanup(PyObject* self, PyObject* args)
{
    snaptrace_clear(self, args);
    while (buffer_head->next) {
        struct EventNode* node = buffer_head->next;
        buffer_head->next = node->next;
        PyMem_FREE(node);
    } 
    Py_RETURN_NONE;
}

static PyObject*
snaptrace_config(PyObject* self, PyObject* args, PyObject* kw)
{
    static char* kwlist[] = {"verbose", "lib_file_path", "max_stack_depth", 
            "include_files", "exclude_files", "ignore_c_function", NULL};
    int kw_verbose = -1;
    int kw_max_stack_depth = 0;
    char* kw_lib_file_path = NULL;
    PyObject* kw_include_files = NULL;
    PyObject* kw_exclude_files = NULL;
    int kw_ignore_c_function = -1;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "|isiOOp", kwlist, 
            &kw_verbose,
            &kw_lib_file_path,
            &kw_max_stack_depth,
            &kw_include_files,
            &kw_exclude_files,
            &kw_ignore_c_function)) {
        return NULL;
    }

    check_flags = 0;

    if (kw_verbose >= 0) {
        verbose = kw_verbose;
    }

    if (kw_lib_file_path) {
        // Obviously we need to copy the string here or it would fail on
        // MacOS + python3.8
        // The documentation did not say whether the value persists on "s"
        // so we should copy it anyway. 
        lib_file_path = PyMem_Calloc((strlen(kw_lib_file_path) + 1), sizeof(char));
        strcpy(lib_file_path, kw_lib_file_path);
    }

    if (kw_ignore_c_function == 1) {
        SET_FLAG(check_flags, SNAPTRACE_IGNORE_C_FUNCTION);
    } else if (kw_ignore_c_function == 0) {
        UNSET_FLAG(check_flags, SNAPTRACE_IGNORE_C_FUNCTION);
    }

    if (kw_max_stack_depth >= 0) {
        SET_FLAG(check_flags, SNAPTRACE_MAX_STACK_DEPTH);       
        max_stack_depth = kw_max_stack_depth;
    } else {
        UNSET_FLAG(check_flags, SNAPTRACE_MAX_STACK_DEPTH);
    }

    if (kw_include_files && kw_include_files != Py_None) {
        if (include_files) {
            Py_DECREF(include_files);
        }
        include_files = kw_include_files;
        Py_INCREF(include_files);
        SET_FLAG(check_flags, SNAPTRACE_INCLUDE_FILES);
    } else {
        UNSET_FLAG(check_flags, SNAPTRACE_INCLUDE_FILES);
    }

    if (kw_exclude_files && kw_exclude_files != Py_None) {
        if (exclude_files) {
            Py_DECREF(exclude_files);
        }
        exclude_files = kw_exclude_files;
        Py_INCREF(exclude_files);
        SET_FLAG(check_flags, SNAPTRACE_EXCLUDE_FILES);
    } else {
        UNSET_FLAG(check_flags, SNAPTRACE_EXCLUDE_FILES);
    }

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_addinstant(PyObject* self, PyObject* args)
{
    PyObject* name = NULL;
    PyObject* instant_args = NULL;
    PyObject* scope = NULL;
    struct EventNode* node = NULL;
    if (!PyArg_ParseTuple(args, "OOO", &name, &instant_args, &scope)) {
        printf("Error when parsing arguments!\n");
        exit(1);
    }

    node = get_next_node();
    node->ntype = INSTANT_NODE;
    node->ts = get_ts();
    node->data.instant.name = name;
    node->data.instant.args = instant_args;
    node->data.instant.scope = scope;
    Py_INCREF(name);
    Py_INCREF(args);
    Py_INCREF(scope);

    Py_RETURN_NONE;
}

static struct ThreadInfo* snaptrace_createthreadinfo(void) {
    struct ThreadInfo* info = calloc(1, sizeof(struct ThreadInfo));

    pthread_setspecific(thread_key, info);

    return info;
}

static void snaptrace_threaddestructor(void* key) {
    struct ThreadInfo* info = key;
    if (info) {
        info->paused = 0;
        info->curr_stack_depth = 0;
        info->ignore_stack_depth = 0;
        info->stack_top = NULL;
    }
}

PyMODINIT_FUNC
PyInit_snaptrace(void) 
{
    buffer_head = (struct EventNode*) PyMem_Malloc (sizeof(struct EventNode));
    buffer_head->ntype = EVENT_NODE;
    buffer_head->next = NULL;
    buffer_head->prev = NULL;
    buffer_tail = buffer_head; 
    collecting = 0;
    if (pthread_key_create(&thread_key, snaptrace_threaddestructor)) {
        perror("Failed to create Tss_Key");
        exit(-1);
    }

    thread_module = PyImport_ImportModule("threading");
    return PyModule_Create(&snaptracemodule);
}