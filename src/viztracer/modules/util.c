// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#include <Python.h>
#include <time.h>
#include "snaptrace.h"


// Utility functions

void
Print_Py(PyObject* o)
{
    PyObject* repr = PyObject_Repr(o);
    printf("%s\n", PyUnicode_AsUTF8(repr));
    Py_DECREF(repr);
}

void
fprintjson(FILE* fptr, PyObject* obj)
{
    if (orjson_module != NULL) {
      PyObject* orjson_dumps = PyObject_GetAttrString(orjson_module, "dumps");
      PyObject* args_bytes = PyObject_CallOneArg(orjson_dumps, obj);
      char* data;
      Py_ssize_t size;
      if (PyBytes_AsStringAndSize(args_bytes, &data, &size) == 0) {
          fwrite(data, 1, size, fptr);
      }
      Py_DECREF(args_bytes);
      Py_DECREF(orjson_dumps);
    } else {
      PyObject* json_dumps = PyObject_GetAttrString(json_module, "dumps");
      PyObject* args_str = PyObject_CallOneArg(json_dumps, obj);
      Py_ssize_t size;
      const char* utf8_data = PyUnicode_AsUTF8AndSize(args_str, &size);
      if (utf8_data) {
        fwrite(utf8_data, 1, size, fptr);
      }
      Py_DECREF(args_str);
      Py_DECREF(json_dumps);
    }
}

void
fprint_escape(FILE *fptr, const char *s)
{
    while (*s != 0) {
        switch (*s) {
            case '\\': fputc('\\', fptr); fputc(*s, fptr); break;
            case '"':  fputc('\\', fptr); fputc(*s, fptr); break;
            case '\b': fputc('\\', fptr); fputc('b', fptr); break;
            case '\f': fputc('\\', fptr); fputc('f', fptr); break;
            case '\n': fputc('\\', fptr); fputc('n', fptr); break;
            case '\r': fputc('\\', fptr); fputc('r', fptr); break;
            case '\t': fputc('\\', fptr); fputc('t', fptr); break;
            default: fputc(*s, fptr);
        }
        s++;
    }
}
