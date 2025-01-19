// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#ifndef __SNAPTRACE_H__
#define __SNAPTRACE_H__

#include <Python.h>
#include <frameobject.h>
#if _WIN32
#include <windows.h>
#else
#include <pthread.h>
#endif

#ifdef Py_GIL_DISABLED
// The free threading implementation of SNAPTRACE_THREAD_PROTECT_START/END uses
// a per-tracer mutex. The mutex is acquired in SNAPTRACE_THREAD_PROTECT_START
// and released in SNAPTRACE_THREAD_PROTECT_END.
// NOTE: these macros delimit a C scope so any variables accessed after
// a SNAPTRACE_THREAD_PROTECT_END need to be declared before
// SNAPTRACE_THREAD_PROTECT_START.
#define SNAPTRACE_THREAD_PROTECT_START(self) Py_BEGIN_CRITICAL_SECTION(self)
#define SNAPTRACE_THREAD_PROTECT_END(self) Py_END_CRITICAL_SECTION()
#else
// The default implementation is a no-op.
#define SNAPTRACE_THREAD_PROTECT_START(self)
#define SNAPTRACE_THREAD_PROTECT_END(self)
#endif

#ifndef Py_MONITORING_H
// monitoring.h is only available after 3.13, this is a fix
// to support the following events on 3.12 
#define PY_MONITORING_EVENT_PY_START 0
#define PY_MONITORING_EVENT_PY_RESUME 1
#define PY_MONITORING_EVENT_PY_RETURN 2
#define PY_MONITORING_EVENT_PY_YIELD 3
#define PY_MONITORING_EVENT_CALL 4
#define PY_MONITORING_EVENT_LINE 5
#define PY_MONITORING_EVENT_INSTRUCTION 6
#define PY_MONITORING_EVENT_JUMP 7
#define PY_MONITORING_EVENT_BRANCH 8
#define PY_MONITORING_EVENT_STOP_ITERATION 9
#define PY_MONITORING_EVENT_RAISE 10
#define PY_MONITORING_EVENT_EXCEPTION_HANDLED 11
#define PY_MONITORING_EVENT_PY_UNWIND 12
#define PY_MONITORING_EVENT_PY_THROW 13
#define PY_MONITORING_EVENT_RERAISE 14
#define PY_MONITORING_EVENT_C_RETURN 15
#define PY_MONITORING_EVENT_C_RAISE 16
#endif


#define SNAPTRACE_MAX_STACK_DEPTH (1 << 0)
#define SNAPTRACE_INCLUDE_FILES (1 << 1)
#define SNAPTRACE_EXCLUDE_FILES (1 << 2)
#define SNAPTRACE_IGNORE_C_FUNCTION (1 << 3)
#define SNAPTRACE_LOG_RETURN_VALUE (1 << 4)
#define SNAPTRACE_LOG_FUNCTION_ARGS (1 << 6)
#define SNAPTRACE_IGNORE_FROZEN (1 << 7)
#define SNAPTRACE_LOG_ASYNC (1 << 8)
#define SNAPTRACE_TRACE_SELF (1 << 9)

#define SET_FLAG(reg, flag) ((reg) |= (flag))
#define UNSET_FLAG(reg, flag) ((reg) &= (~(flag)))

#define CHECK_FLAG(reg, flag) (((reg) & (flag)) != 0) 

#define SNAPTRACE_TOOL_ID 2

struct FunctionNode {
    struct FunctionNode* next;
    struct FunctionNode* prev;
    int64_t ts;
    PyObject* args;
    // PyCodeObject* for Python function, PyCFunctionObject* for C function
    PyObject* func;
};

struct ThreadInfo {
    int paused;
    int curr_stack_depth;
    int ignore_stack_depth;
    unsigned long tid;
    struct FunctionNode* stack_top;
    PyObject* curr_task;
    PyFrameObject* curr_task_frame;
    struct MetadataNode* metadata_node;
};

struct MetadataNode {
    struct MetadataNode* next;
    unsigned long tid;
    PyObject* name;
    struct ThreadInfo* thread_info;
};

typedef struct {
    PyObject_HEAD
#if _WIN32
    DWORD dwTlsIndex;
#else
    pthread_key_t thread_key;
#endif
    int collecting;
    // When we do fork_save(), we want to keep the pid. This is a 
    // mechanism for child process to keep the parent's pid. If 
    // this value is 0, then the program gets pid before parsing,
    // otherwise it uses this pid
    long fix_pid;
    unsigned long total_entries;
    unsigned int check_flags;
    int verbose;
    char* lib_file_path;
    int max_stack_depth;
    PyObject* process_name;
    PyObject* include_files;
    PyObject* exclude_files;
    PyObject* log_func_repr;
    double min_duration;
    struct EventNode* buffer;
    long buffer_size;
    long buffer_head_idx;
    long buffer_tail_idx;
    int64_t sync_marker;
    struct MetadataNode* metadata_head;
} TracerObject;

extern PyObject* threading_module;
extern PyObject* multiprocessing_module;
extern PyObject* json_module;
extern PyObject* asyncio_module;
extern PyObject* asyncio_tasks_module;

#endif
