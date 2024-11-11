// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


#ifndef __SNAPTRACE_UTIL_H__
#define __SNAPTRACE_UTIL_H__

#include <Python.h>
#include <string.h>

#if _WIN32
#include <windows.h>
extern LARGE_INTEGER qpc_freq;
#endif

void Print_Py(PyObject* o);
void fprintjson(FILE* fptr, PyObject* obj);
void fprint_escape(FILE *fptr, const char *s);

// target and prefix has to be NULL-terminated
inline int startswith(const char* target, const char* prefix)
{
    size_t len = strlen(prefix);
    return strncmp(target, prefix, len) == 0;
}

inline double get_system_ts(void)
{
#if _WIN32
    LARGE_INTEGER counter = {0};
    QueryPerformanceCounter(&counter);
    double curr_ts = (double) counter.QuadPart;
    curr_ts *= 1000000000LL;
    curr_ts /= qpc_freq.QuadPart;
    return curr_ts;
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return ((double)t.tv_sec * 1e9 + t.tv_nsec);
#endif
}

#endif
