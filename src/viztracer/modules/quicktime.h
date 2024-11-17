// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


#ifndef __SNAPTRACE_QUICKTIME_H__
#define __SNAPTRACE_QUICKTIME_H__

#include <Python.h>
#include <stdint.h>
#include <time.h>

#if _WIN32
#include <windows.h>
extern LARGE_INTEGER qpc_freq;
#elif defined(__APPLE__)
#include <mach/mach_time.h>
extern mach_timebase_info_data_t timebase_info;
#endif

#if defined(__i386__) || defined(__x86_64__) || defined(__amd64__)
#define QUICKTIME_RDTSC
#if defined(_MSC_VER)
#include <intrin.h>
#elif defined(__clang__)
// `__rdtsc` is available by default.
// NB: This has to be first, because Clang will also define `__GNUC__`
#elif defined(__GNUC__)
#include <x86intrin.h>
#else
#undef QUICKTIME_RDTSC
#endif
#endif

extern double ts_to_ns_factor;
extern int64_t system_base_time;

void quicktime_init();
void quicktime_free();
double system_ts_to_us(int64_t ts);
int64_t system_ts_to_ns(int64_t ts);
double dur_ts_to_us(int64_t dur);
int64_t dur_ts_to_ns(int64_t dur);

inline int64_t
get_base_time_ns(void)
{
    return system_base_time;
};

inline int64_t
get_system_ts(void)
{
#if defined(QUICKTIME_RDTSC)
    return __rdtsc();
#else
#if _WIN32
    LARGE_INTEGER counter = {0};
    QueryPerformanceCounter(&counter);
    return counter.QuadPart;
#elif defined(__APPLE__)
    return mach_absolute_time();
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (int64_t)(t.tv_sec * 1e9 + t.tv_nsec);
#endif
#endif
}

inline int64_t
get_system_ns(void)
{
#if _WIN32
    LARGE_INTEGER counter = {0};
    QueryPerformanceCounter(&counter);
    return counter.QuadPart * 1e9 / qpc_freq.QuadPart;
#elif defined(__APPLE__)
    return mach_absolute_time() * timebase_info.numer / timebase_info.denom;
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return (int64_t)(t.tv_sec * 1e9 + t.tv_nsec);
#endif
}


inline int64_t
get_system_epoch_ns(void)
{
#if _WIN32
    FILETIME ft;
    ULARGE_INTEGER ui;
    GetSystemTimePreciseAsFileTime(&ft);
    ui.LowPart = ft.dwLowDateTime;
    ui.HighPart = ft.dwHighDateTime;
    return (ui.QuadPart - 116444736000000000ULL) * 100;
#else
    struct timespec t;
    clock_gettime(CLOCK_REALTIME, &t);
    return (int64_t)t.tv_sec * 1e9 + t.tv_nsec;
#endif
}

#endif
