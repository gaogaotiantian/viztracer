// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#include <stdio.h>
#include "eventnode.h"

void clear_node(struct EventNode* node) {
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
        if (node->data.fee.asyncio_task != NULL) {
            Py_DECREF(node->data.fee.asyncio_task);
            node->data.fee.asyncio_task = NULL;
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

// This will return a PyUnicode object to the caller
// The caller is responsible to decrease the reference
//   name_set is an initialized set to keep
//   formatted names to save memory
PyObject* get_name_from_fee_node(struct EventNode* node, PyObject* name_dict)
{
    assert(PyDict_Check(name_dict));

    PyObject* name = NULL;
    PyObject* ret = NULL;

    // We create the name first. However, this name might already exists
    // before. To save memory usage, we check if this name exists in name_dict
    // If it does, we use the one in name_dict and delete this one.
    // This way, for entries that has the same name, we won't create multiple
    // string instances
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

    if (PyDict_Contains(name_dict, name)) {
        ret = PyDict_GetItem(name_dict, name);
        Py_DECREF(name);
        Py_INCREF(ret);
    } else {
        // return name, so don't DECREF it
        PyDict_SetItem(name_dict, name, name);
        ret = name;
    }

    return ret;
}

static void fputs_escape(const char* s, FILE* fptr)
{
    while (*s != 0) {
        if (*s == '\\' || *s == '\"') {
            fputc('\\', fptr);
        }
        fputc(*s, fptr);
        s++;
    }
}

void fprintfeename(FILE* fptr, struct EventNode* node)
{
    if (node->data.fee.type == PyTrace_CALL || node->data.fee.type == PyTrace_RETURN) {
        fputs(PyUnicode_AsUTF8(node->data.fee.co_name), fptr);
        fputs(" (", fptr);
        fputs_escape(PyUnicode_AsUTF8(node->data.fee.co_filename), fptr);
        fprintf(fptr, ":%d)", node->data.fee.co_firstlineno);
    } else {
        if (node->data.fee.m_module) {
            // The function belongs to a module
            fputs(PyUnicode_AsUTF8(node->data.fee.m_module), fptr);
            fputc('.', fptr);
            fputs(node->data.fee.ml_name, fptr);
        } else {
            // The function is a class method
            if (node->data.fee.tp_name) {
                // It's not a static method, has __self__
                fputs(node->data.fee.tp_name, fptr);
                fputc('.', fptr);
                fputs(node->data.fee.ml_name, fptr);
            } else {
                // It's a static method, does not have __self__
                fputs(node->data.fee.ml_name, fptr);
            }
        }
    }
}
