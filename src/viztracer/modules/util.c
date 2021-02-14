// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#if _WIN32
#include <windows.h>
#endif
#include <Python.h>
#include <time.h>


#if _WIN32
LARGE_INTEGER qpc_freq;
#endif

// Utility functions

void Print_Py(PyObject* o)
{
    PyObject* repr = PyObject_Repr(o);
    printf("%s\n", PyUnicode_AsUTF8(repr));
    Py_DECREF(repr);
}

// target and prefix has to be NULL-terminated
int startswith(const char* target, const char* prefix)
{
    while(*target != 0 && *prefix != 0) {
#if _WIN32
        // Windows path has double slashes and case-insensitive
        if (*prefix == '\\' && prefix[-1] == '\\') {
            prefix++;
        }
        if (*target == '\\' && target[-1] == '\\') {
            target++;
        }
        if (*target != *prefix && *target != *prefix - ('a'-'A') && *target != *prefix + ('a'-'A')) {
            return 0;
        }
#else
        if (*target != *prefix) {
            return 0;
        }
#endif
        target++;
        prefix++;
    }

    return (*prefix) == 0;
}


double get_ts(void)
{
    static double prev_ts = 0;
    double curr_ts = 0;

#if _WIN32
    LARGE_INTEGER counter = {0};
    QueryPerformanceCounter(&counter);
    counter.QuadPart *= 1000000000LL;
    counter.QuadPart /= qpc_freq.QuadPart;
    curr_ts = (double) counter.QuadPart;
#else
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    curr_ts = ((double)t.tv_sec * 1e9 + t.tv_nsec);
#endif
    if (curr_ts == prev_ts) {
        curr_ts += 20;
    }
    prev_ts = curr_ts;
    return curr_ts;
}
