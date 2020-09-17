// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#ifndef __SNAPTRACE_H__
#define __SNAPTRACE_H__

#define SNAPTRACE_MAX_STACK_DEPTH (1 << 0)
#define SNAPTRACE_INCLUDE_FILES (1 << 1)
#define SNAPTRACE_EXCLUDE_FILES (1 << 2)
#define SNAPTRACE_IGNORE_C_FUNCTION (1 << 3)
#define SNAPTRACE_LOG_RETURN_VALUE (1 << 4)
#define SNAPTRACE_NOVDB (1 << 5)
#define SNAPTRACE_LOG_FUNCTION_ARGS (1 << 6)
#define SNAPTRACE_IGNORE_NON_FILE (1 << 7)

#define SET_FLAG(reg, flag) ((reg) |= (flag))
#define UNSET_FLAG(reg, flag) ((reg) &= (~(flag)))

#define CHECK_FLAG(reg, flag) (((reg) & (flag)) != 0) 

typedef enum _NodeType {
    EVENT_NODE = 0,
    FEE_NODE = 1,
    INSTANT_NODE = 2,
    COUNTER_NODE = 3,
    OBJECT_NODE = 4
} NodeType;

struct FEEData {
    PyObject* args;
    PyObject* retval;
    PyCFunctionObject* cfunc;
    PyCodeObject* pycode;
    int type;
    int caller_lineno;
    double dur;
};

struct InstantData {
    PyObject* name;
    PyObject* args;
    PyObject* scope;
};

struct CounterData {
    PyObject* name;
    PyObject* args;
};

struct ObjectData {
    PyObject* name;
    PyObject* args;
    PyObject* id;
    PyObject* ph;
};

struct EventNode {
    NodeType ntype;
    double ts;
    unsigned long tid;
    union {
        struct FEEData fee;
        struct InstantData instant;
        struct CounterData counter;
        struct ObjectData object;
    } data;
};

struct FunctionNode {
    struct FunctionNode* next;
    struct FunctionNode* prev;
    double ts;
    PyObject* args;
};

struct ThreadInfo {
    int paused;
    int curr_stack_depth;
    int ignore_stack_depth;
    unsigned long tid;
    struct FunctionNode* stack_top;
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
    PyObject* include_files;
    PyObject* exclude_files;
    struct EventNode* buffer;
    long buffer_size;
    long buffer_head_idx;
    long buffer_tail_idx;
} TracerObject;

#endif