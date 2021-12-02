// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#ifndef __EVENTNODE_H__
#define __EVENTNODE_H__

#include <Python.h>

typedef enum _NodeType {
    EVENT_NODE = 0,
    FEE_NODE = 1,
    INSTANT_NODE = 2,
    COUNTER_NODE = 3,
    OBJECT_NODE = 4,
    RAW_NODE = 5
} NodeType;

struct FEEData {
    PyObject* args;
    PyObject* retval;
    union {
        struct {
            PyObject* m_module;
            const char* ml_name;
            const char* tp_name;
        };
        struct {
            PyObject* co_name;
            PyObject* co_filename;
            int co_firstlineno;
        };
    };
    int type;
    int caller_lineno;
    double dur;
    PyObject* asyncio_task;
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
        PyObject* raw;
    } data;
};

// ==== Functions ====

// Clear the node, release reference 
void clear_node(struct EventNode* node);

// get name from FEE node, passing in a dictionary for name cache
PyObject* get_name_from_fee_node(struct EventNode* node, PyObject* name_dict);
void fprintfeename(FILE*, struct EventNode* node);
#endif
