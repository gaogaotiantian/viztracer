// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#include <Python.h>
#include <stdio.h>

#include "pythoncapi_compat.h"
#include "eventnode.h"

void
clear_node(struct EventNode* node) {
    switch (node->ntype) {
    case FEE_NODE:
        if (node->data.fee.type == PyTrace_CALL || node->data.fee.type == PyTrace_RETURN) {
            Py_CLEAR(node->data.fee.code);
            Py_CLEAR(node->data.fee.args);
            Py_CLEAR(node->data.fee.retval);
        } else {
            node->data.fee.ml_name = NULL;
            if (node->data.fee.m_module) {
                // The function belongs to a module
                Py_CLEAR(node->data.fee.m_module);
            } else {
                // The function is a class method
                if (node->data.fee.tp_name) {
                    // It's not a static method, has __self__
                    node->data.fee.tp_name = NULL;
                }
            }
        }
        Py_CLEAR(node->data.fee.asyncio_task);
        break;
    case INSTANT_NODE:
        Py_CLEAR(node->data.instant.name);
        Py_CLEAR(node->data.instant.args);
        Py_CLEAR(node->data.instant.scope);
        break;
    case COUNTER_NODE:
        Py_CLEAR(node->data.counter.name);
        Py_CLEAR(node->data.counter.args);
        break;
    case OBJECT_NODE:
        Py_CLEAR(node->data.object.ph);
        Py_CLEAR(node->data.object.id);
        Py_CLEAR(node->data.object.name);
        Py_CLEAR(node->data.object.args);
        break;
    case RAW_NODE:
        Py_CLEAR(node->data.raw);
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
PyObject*
get_name_from_fee_node(struct EventNode* node, PyObject* name_dict)
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
#if PY_VERSION_HEX >= 0x030B0000
               PyUnicode_AsUTF8(node->data.fee.code->co_qualname),
#else
               PyUnicode_AsUTF8(node->data.fee.code->co_name),
#endif
               PyUnicode_AsUTF8(node->data.fee.code->co_filename),
               node->data.fee.code->co_firstlineno);
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
        ret = Py_NewRef(PyDict_GetItem(name_dict, name));
        Py_DECREF(name);
    } else {
        // return name, so don't DECREF it
        PyDict_SetItem(name_dict, name, name);
        ret = name;
    }

    return ret;
}

static void
fputs_escape(const char* s, FILE* fptr)
{
    while (*s != 0) {
        if (*s == '\\' || *s == '\"') {
            fputc('\\', fptr);
        }
        fputc(*s, fptr);
        s++;
    }
}

void
fprintfeename(FILE* fptr, struct EventNode* node, uint8_t sanitize_function_name)
{
    if (node->data.fee.type == PyTrace_CALL || node->data.fee.type == PyTrace_RETURN) {
#if PY_VERSION_HEX >= 0x030B0000
    if (PyUnicode_Check(node->data.fee.code->co_qualname)) {
        fputs(PyUnicode_AsUTF8(node->data.fee.code->co_qualname), fptr);
    } else {
        fputs("<unknown>", fptr);
    }
#else
    if (PyUnicode_Check(node->data.fee.code->co_name)) {
        fputs(PyUnicode_AsUTF8(node->data.fee.code->co_name), fptr);
    } else {
        fputs("<unknown>", fptr);
    }
#endif
        fputs(" (", fptr);
        if (PyUnicode_Check(node->data.fee.code->co_filename)) {
            fputs_escape(PyUnicode_AsUTF8(node->data.fee.code->co_filename), fptr);
        } else {
            fputs("<unknown>", fptr);
        }
        fprintf(fptr, ":%d)", node->data.fee.code->co_firstlineno);
    } else {
        const char* ml_name = node->data.fee.ml_name;

        if (sanitize_function_name) {
            const char *c = ml_name;
            while (*c != '\0') {
                if(!Py_UNICODE_ISPRINTABLE(*c)) {
                    ml_name = NULL;
                    break;
                }
                c ++;
            }
        }
        if (node->data.fee.m_module) {
            // The function belongs to a module
            if (PyUnicode_Check(node->data.fee.m_module)) {
                fputs(PyUnicode_AsUTF8(node->data.fee.m_module), fptr);
            } else {
                fputs("<unknown>", fptr);
            }
            fputc('.', fptr);
        } else {
            // The function is a class method
            if (node->data.fee.tp_name) {
                // It's not a static method, has __self__
                fputs(node->data.fee.tp_name, fptr);
                fputc('.', fptr);
            } else {
                // It's a static method, does not have __self__
            }
        }
        // We will have to put ml_name at the end anyway.
        if (ml_name) {
            fputs(ml_name, fptr);
        }
    }
}
