#ifndef __VCOMPRESSOR_H__
#define __VCOMPRESSOR_H__

#include <Python.h>

#define VCOMPRESSOR_VERSION 1

typedef struct {
    PyObject_HEAD
} VcompressorObject;

extern PyObject* json_module;
extern PyObject* zlib_module;

#endif
