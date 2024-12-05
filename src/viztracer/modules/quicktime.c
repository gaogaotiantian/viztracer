// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


#include <Python.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <time.h>

#include "quicktime.h"

#if _WIN32
#include <windows.h>
LARGE_INTEGER qpc_freq;
#elif defined(__APPLE__)
#include <mach/mach_time.h>
mach_timebase_info_data_t timebase_info;
#endif


#define CALIBRATE_SIZE 1000

double ts_to_ns_factor = 1.0;
int64_t system_base_time = 0;
int64_t system_base_ts = 0;
int64_t* start_ts = NULL;
int64_t* start_ns = NULL;
int64_t t0_ts = 0;
int64_t t0_ns = 0;
bool calibrated = false;

static int
compare_double(const void *a, const void *b)
{
    return (*(double *)a - *(double *)b);
}

static int
compare_int64(const void *a, const void *b)
{
    return (*(int64_t *)a - *(int64_t *)b);
}

static void
calibrate_quicktime()
{
    int64_t end_ts[CALIBRATE_SIZE] = {0};
    int64_t end_ns[CALIBRATE_SIZE] = {0};
    double factors[CALIBRATE_SIZE] = {0};

    for (int i = 0; i < CALIBRATE_SIZE; i++)
    {
        int64_t end_before = get_system_ts();
        end_ns[i] = get_system_ns();
        int64_t end_after = get_system_ts();
        end_ts[i] = end_before + (end_after - end_before) / 2;
    }

    for (int i = 0; i < CALIBRATE_SIZE; i++)
    {
        factors[i] = (double)(end_ns[i] - start_ns[i]) / (end_ts[i] - start_ts[i]);
    }

    qsort(factors, CALIBRATE_SIZE, sizeof(double), compare_double);

    ts_to_ns_factor = factors[CALIBRATE_SIZE / 2];
}

double
system_ts_to_us(int64_t ts)
{
    if (!calibrated)
    {
        calibrate_quicktime();
        calibrated = true;
    }
    return system_ts_to_ns(ts) / 1000.0;
}

int64_t
system_ts_to_ns(int64_t ts)
{
    if (!calibrated)
    {
        calibrate_quicktime();
        calibrated = true;
    }
    return t0_ns + (ts - t0_ts) * ts_to_ns_factor;
}

double
dur_ts_to_us(int64_t dur)
{
    if (!calibrated)
    {
        calibrate_quicktime();
        calibrated = true;
    }
    return (double)dur * ts_to_ns_factor / 1000;
}

int64_t
dur_ts_to_ns(int64_t dur)
{
    if (!calibrated)
    {
        calibrate_quicktime();
        calibrated = true;
    }
    return dur * ts_to_ns_factor;
}

void
quicktime_free()
{
    free(start_ts);
    free(start_ns);
}

void
quicktime_init()
{
#if _WIN32
    QueryPerformanceFrequency(&qpc_freq);
#elif defined(__APPLE__)
    mach_timebase_info(&timebase_info);
#endif

    start_ts = (int64_t*)malloc(sizeof(int64_t) * CALIBRATE_SIZE);
    start_ns = (int64_t*)malloc(sizeof(int64_t) * CALIBRATE_SIZE);

    int64_t diff_ns[CALIBRATE_SIZE] = {0};

    t0_ts = 0;
    t0_ns = 0;

    for (int i = 0; i < CALIBRATE_SIZE; i++)
    {
        int64_t start_before = get_system_ts();
        start_ns[i] = get_system_ns();
        int64_t start_after = get_system_ts();
        start_ts[i] = start_before + (start_after - start_before) / 2;
    }

    // Do the expensive average calculation outside the measurement loop
    int64_t ts_remainder = 0;
    int64_t ns_remainder = 0;
    for (int i = 0; i < CALIBRATE_SIZE; i++)
    {
        // Divide by CALIBRATE_SIZE at each step instead of accumulate-and-divide to avoid overflow
        t0_ts += start_ts[i] / CALIBRATE_SIZE;
        t0_ns += start_ns[i] / CALIBRATE_SIZE;

        // Also accumulate the remainders, which are unlikely to overflow
        ts_remainder += start_ts[i] % CALIBRATE_SIZE;
        ns_remainder += start_ns[i] % CALIBRATE_SIZE;
    }
    // Then finally add the average remainder
    t0_ts += ts_remainder / CALIBRATE_SIZE;
    t0_ns += ns_remainder / CALIBRATE_SIZE;

    // Now let's find the base time

    for (int i = 0; i < CALIBRATE_SIZE; i++)
    {
        int64_t start_before = get_system_ns();
        diff_ns[i] = get_system_epoch_ns();
        int64_t start_after = get_system_ns();
        diff_ns[i] -= start_before + (start_after - start_before) / 2;
    }

    qsort(diff_ns, CALIBRATE_SIZE, sizeof(int64_t), compare_int64);

    system_base_time = diff_ns[CALIBRATE_SIZE / 2];
}
