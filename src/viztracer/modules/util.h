// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


#ifndef __SNAPTRACE_UTIL_H__
#define __SNAPTRACE_UTIL_H__

#include <Python.h>
#include <string.h>

#if _WIN32
#include <windows.h>
extern LARGE_INTEGER qpc_freq;
#elif defined(__APPLE__)
#include <mach/mach_time.h>
extern mach_timebase_info_data_t timebase_info;
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
#elif defined(__APPLE__)
    return mach_absolute_time();
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
#elif defined(__APPLE__)
    return (double)ts * timebase_info.numer / timebase_info.denom / 1e3;
#else
    return (double)ts / 1e3;
#endif
}

inline long long system_ts_to_ns(long long ts)
{
#if _WIN32
    return ts * 1e9 / qpc_freq.QuadPart;
#elif defined(__APPLE__)
    return ts * timebase_info.numer / timebase_info.denom;
#else
    return ts;
#endif
}

inline int64_t calc_base_time_ns(void)
{
#if _WIN32
    FILETIME ft;
    ULARGE_INTEGER ui;
    // get timestamps
    int64_t system_ts = get_system_ts();
    GetSystemTimeAsFileTime(&ft);

    int64_t sys_ns = system_ts_to_ns(system_ts);
    ui.LowPart = ft.dwLowDateTime;
    ui.HighPart = ft.dwHighDateTime;

    int64_t filetime_ns = (ui.QuadPart - 116444736000000000ULL) * 100;
    return filetime_ns - sys_ns;
#else
    struct timespec t;

    // get timestamps
    int64_t system_ts = get_system_ts();
    clock_gettime(CLOCK_REALTIME, &t);

    int64_t sys_ns = system_ts_to_ns(system_ts);
    int64_t realtime_ns = (int64_t)t.tv_sec * 1e9 + t.tv_nsec;

    return realtime_ns - sys_ns;
#endif
}

#endif
