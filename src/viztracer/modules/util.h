// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


#ifndef __SNAPTRACE_UTIL_H__
#define __SNAPTRACE_UTIL_H__

#include <Python.h>
#include <string.h>

void Print_Py(PyObject* o);
void fprintjson(FILE* fptr, PyObject* obj);
void fprint_escape(FILE *fptr, const char *s);

// target and prefix has to be NULL-terminated
inline int startswith(const char* target, const char* prefix)
{
    size_t len = strlen(prefix);
    return strncmp(target, prefix, len) == 0;
}

#endif
