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

inline long long get_system_ts(void)
{
#if _WIN32
    LARGE_INTEGER counter = {0};
    QueryPerformanceCounter(&counter);
    return counter.QuadPart;
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (long long)(t.tv_sec * 1e9 + t.tv_nsec);
#endif
}

inline double system_ts_to_us(long long ts)
{
#if _WIN32
    return (double)ts * 1e6 / qpc_freq.QuadPart;
#else
    return (double)ts / 1e3;
#endif
}

inline long long system_ts_to_ns(long long ts)
{
#if _WIN32
    return ts * 1e9 / qpc_freq.QuadPart;
#else
    return ts;
#endif
}

#endif
