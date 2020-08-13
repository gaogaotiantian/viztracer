#define PY_SSIZE_T_CLEAN
#include <stdlib.h>
#include <Python.h>
#include <frameobject.h>
#include <time.h>
#include <pthread.h>
#include "snaptrace.h"

// Function declarations

int snaptrace_tracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg);
static PyObject* snaptrace_threadtracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg);
static PyObject* snaptrace_start(PyObject* self, PyObject* args);
static PyObject* snaptrace_stop(PyObject* self, PyObject* args);
static PyObject* snaptrace_load(PyObject* self, PyObject* args);
static PyObject* snaptrace_clear(PyObject* self, PyObject* args);
static PyObject* snaptrace_cleanup(PyObject* self, PyObject* args);
static PyObject* snaptrace_config(PyObject* self, PyObject* args, PyObject* kw);
static void snaptrace_threaddestructor(void* key);
static struct ThreadInfo* snaptrace_createthreadinfo(void);

// the key is used to locate thread specific info
static pthread_key_t thread_key = 0;
// We need to ignore the first event because it's return of start() function
int first_event = 1;
int collecting = 0;
unsigned long total_entries = 0;
unsigned int check_flags = 0;

int verbose = 0;
int max_stack_depth = -1;
PyObject* include_files = NULL;
PyObject* exclude_files = NULL;
PyObject* thread_module = NULL;

struct FEENode {
    PyObject* file_name;
    PyObject* class_name;
    PyObject* func_name;
    int type;
    long tid;
    double ts;
    struct FEENode* next;
    struct FEENode* prev;
} *buffer_head, *buffer_tail;

struct ThreadInfo {
    int curr_stack_depth;
    int ignore_stack_depth;
};

static void Print_Py(PyObject* o)
{
    printf("%s\n", PyUnicode_AsUTF8(PyObject_Repr(o)));
}

static void verbose_printf(int v, const char* fmt, ...)
{
    va_list args;
    if (verbose >= v) {
        va_start(args, fmt);
        vprintf(fmt, args);
        va_end(args);
    }
}

static PyMethodDef SnaptraceMethods[] = {
    {"threadtracefunc", (PyCFunction)snaptrace_threadtracefunc, METH_VARARGS, "trace function"},
    {"start", snaptrace_start, METH_VARARGS, "start profiling"},
    {"stop", snaptrace_stop, METH_VARARGS, "stop profiling"},
    {"load", snaptrace_load, METH_VARARGS, "load buffer"},
    {"clear", snaptrace_clear, METH_VARARGS, "clear buffer"},
    {"cleanup", snaptrace_cleanup, METH_VARARGS, "free the memory allocated"},
    {"config", (PyCFunction)snaptrace_config, METH_VARARGS|METH_KEYWORDS, "config the snaptrace module"}
};

static struct PyModuleDef snaptracemodule = {
    PyModuleDef_HEAD_INIT,
    "codesnap.snaptrace",
    NULL,
    -1,
    SnaptraceMethods
};

int
snaptrace_tracefunc(PyObject* obj, PyFrameObject* frame, int what, PyObject* arg)
{
    if (what == PyTrace_CALL || what == PyTrace_RETURN) {
        struct FEENode* node = NULL;
        struct timespec t;
        struct ThreadInfo* info = pthread_getspecific(thread_key);

        if (first_event) {
            first_event = 0;
            return 0;
        }

        // Check max stack depth
        if (CHECK_FLAG(check_flags, SNAPTRACE_MAX_STACK_DEPTH)) {
            if (what == PyTrace_CALL) {
                info->curr_stack_depth += 1;
                if (info->curr_stack_depth > max_stack_depth) {
                    return 0;
                }
            } else if (what == PyTrace_RETURN) {
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
                        if (strstr(path, PyUnicode_AsUTF8(f))) {
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

        clock_gettime(CLOCK_MONOTONIC, &t);
        if (buffer_tail->next) {
            node = buffer_tail->next;
        } else {
            node = (struct FEENode*)PyMem_Malloc(sizeof(struct FEENode));
            node->next = NULL;
            buffer_tail->next = node;
            node->prev = buffer_tail;
        }
        node->file_name = frame->f_code->co_filename;
        Py_INCREF(node->file_name);
        node->class_name = Py_None;
        Py_INCREF(Py_None);
        for (int i = 0; i < frame->f_code->co_nlocals; i++) {
            PyObject* name = PyTuple_GET_ITEM(frame->f_code->co_varnames, i);
            if (strcmp("self", PyUnicode_AsUTF8(name)) == 0) {
                // When self object is just created in __new__, it's possible that the value is NULL
                if (frame->f_localsplus[i]) {
                    node->class_name = PyUnicode_FromString(frame->f_localsplus[i]->ob_type->tp_name);
                    Py_DECREF(Py_None);
                }
                break;
            }
        }
        node->func_name = frame->f_code->co_name;
        Py_INCREF(node->func_name);
        node->type = what;
        node->ts = ((double)t.tv_sec * 1e9 + t.tv_nsec);
        node->tid = pthread_self();
        buffer_tail = node;
        total_entries += 1;
    }


    return 0;
}

static PyObject* snaptrace_threadtracefunc(PyObject* obj, PyFrameObject* frame,
    int what, PyObject* arg) {

    snaptrace_createthreadinfo();
    PyEval_SetProfile(snaptrace_tracefunc, NULL);
    snaptrace_tracefunc(obj, frame, what, arg);
    Py_RETURN_NONE;
}


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

    first_event = 1;
    collecting = 1;

    Py_RETURN_NONE;
}

static PyObject*
snaptrace_stop(PyObject* self, PyObject* args)
{
    PyEval_SetProfile(NULL, NULL);
    if (collecting == 1) {
        // If we are collecting, throw away the last event
        // if it's an entry. because it's entry of stop() function
        struct FEENode* node = buffer_tail;
        if (node->type == PyTrace_CALL) {
            Py_DECREF(node->file_name);
            Py_DECREF(node->class_name);
            Py_DECREF(node->func_name);
            buffer_tail = buffer_tail->prev;
            collecting = 0;
        }
        struct ThreadInfo* info = pthread_getspecific(thread_key);
        snaptrace_threaddestructor(info);
    }
    
    Py_RETURN_NONE;
}

static PyObject*
snaptrace_load(PyObject* self, PyObject* args)
{
    PyObject* lst = PyList_New(0);
    struct FEENode* curr = buffer_head;
    PyObject* pid = PyLong_FromLong(getpid());
    PyObject* cat = PyUnicode_FromString("FEE");
    PyObject* ph_B = PyUnicode_FromString("B");
    PyObject* ph_E = PyUnicode_FromString("E");
    unsigned long counter = 0;
    unsigned long prev_counter = 0;
    while (curr != buffer_tail && curr->next) {
        struct FEENode* node = curr->next;
        PyObject* dict = PyDict_New();
        PyObject* name = NULL;
        PyObject* tid = PyLong_FromLong(node->tid);
        PyObject* ts = PyFloat_FromDouble(node->ts);

        if (node->class_name == Py_None) {
            name = PyUnicode_FromFormat("%s.%s", 
                    PyUnicode_AsUTF8(node->file_name), 
                    PyUnicode_AsUTF8(node->func_name));
        } else {
            name = PyUnicode_FromFormat("%s.%s.%s", 
                    PyUnicode_AsUTF8(node->file_name), 
                    PyUnicode_AsUTF8(node->class_name), 
                    PyUnicode_AsUTF8(node->func_name));
        }

        switch (node->type) {
            case 0:
                // Entry
                PyDict_SetItemString(dict, "ph", ph_B);
                break;
            case 3:
                //Exit
                PyDict_SetItemString(dict, "ph", ph_E);
                break;
            default:
                printf("Unknown Type!\n");
                exit(1);
        }
        PyDict_SetItemString(dict, "name", name);
        Py_DECREF(name);
        PyDict_SetItemString(dict, "cat", cat);
        PyDict_SetItemString(dict, "pid", pid);
        PyDict_SetItemString(dict, "tid", tid);
        Py_DECREF(tid);
        PyDict_SetItemString(dict, "ts", ts);
        Py_DECREF(ts);
        PyList_Append(lst, dict);
        curr = curr->next;

        counter += 1;
        if (counter - prev_counter > 10000 && 100 * (counter - prev_counter) / (1 + total_entries) > 0) {
            verbose_printf(1, "Loading data, %lu / %lu\r", counter, total_entries);
            prev_counter = counter;
        }
    }
    verbose_printf(1, "Loading finish                                        \n");
    Py_DECREF(pid);
    Py_DECREF(cat);
    Py_DECREF(ph_B);
    Py_DECREF(ph_E);
    buffer_tail = buffer_head;
    return lst;
}

static PyObject*
snaptrace_clear(PyObject* self, PyObject* args)
{
    struct FEENode* curr = buffer_head;
    while (curr != buffer_tail && curr->next) {
        struct FEENode* node = curr->next;
        Py_DECREF(node->file_name);
        Py_DECREF(node->class_name);
        Py_DECREF(node->func_name);
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
        struct FEENode* node = buffer_head->next;
        buffer_head->next = node->next;
        PyMem_FREE(node);
    } 
    Py_RETURN_NONE;
}

static PyObject*
snaptrace_config(PyObject* self, PyObject* args, PyObject* kw)
{
    static char* kwlist[] = {"verbose", "max_stack_depth", "include_files", "exclude_files", NULL};
    int kw_verbose = -1;
    int kw_max_stack_depth = 0;
    PyObject* kw_include_files = NULL;
    PyObject* kw_exclude_files = NULL;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "|iiOO", kwlist, 
            &kw_verbose,
            &kw_max_stack_depth,
            &kw_include_files,
            &kw_exclude_files)) {
        return NULL;
    }

    check_flags = 0;

    if (kw_verbose >= 0) {
        verbose = kw_verbose;
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

static struct ThreadInfo* snaptrace_createthreadinfo(void) {
    struct ThreadInfo* info = calloc(1, sizeof(struct ThreadInfo));

    pthread_setspecific(thread_key, info);

    return info;
}

static void snaptrace_threaddestructor(void* key) {
    struct ThreadInfo* info = key;
    if (info) {
        info->curr_stack_depth = 0;
        info->ignore_stack_depth = 0;
    }
}

PyMODINIT_FUNC
PyInit_snaptrace(void) 
{
    buffer_head = (struct FEENode*) PyMem_Malloc (sizeof(struct FEENode));
    buffer_head->class_name = NULL;
    buffer_head->file_name = NULL;
    buffer_head->func_name = NULL;
    buffer_head->next = NULL;
    buffer_head->prev = NULL;
    buffer_head->type = -1;
    buffer_tail = buffer_head; 
    first_event = 1;
    collecting = 0;
    if (pthread_key_create(&thread_key, snaptrace_threaddestructor)) {
        perror("Failed to create Tss_Key");
        exit(-1);
    }

    thread_module = PyImport_ImportModule("threading");
    return PyModule_Create(&snaptracemodule);
}