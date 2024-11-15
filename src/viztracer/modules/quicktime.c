// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
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

static int compare_double(const void *a, const void *b)
{
    return (*(double *)a - *(double *)b);
}

static int compare_int64(const void *a, const void *b)
{
    return (*(int64_t *)a - *(int64_t *)b);
}

static void calibrate_quicktime()
{
    int64_t start_ts[CALIBRATE_SIZE] = {0};
    int64_t start_ns[CALIBRATE_SIZE] = {0};
    int64_t end_ts[CALIBRATE_SIZE] = {0};
    int64_t end_ns[CALIBRATE_SIZE] = {0};
    double factors[CALIBRATE_SIZE] = {0};

    for (int i = 0; i < CALIBRATE_SIZE; i++)
    {
        int64_t start_before = get_system_ts();
        start_ns[i] = get_system_ns();
        int64_t start_after = get_system_ts();
        start_ts[i] = start_before + (start_after - start_before) / 2;
    }

#if _WIN32
    Sleep(100);
#else
    struct timespec t;
    t.tv_sec = 0;
    t.tv_nsec = 100000000;
    nanosleep(&t, NULL);
#endif

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

    // Now let's find the base time

    for (int i = 0; i < CALIBRATE_SIZE; i++)
    {
        int64_t start_before = get_system_ns();
        start_ns[i] = get_system_epoch_ns();
        int64_t start_after = get_system_ns();
        start_ns[i] -= start_before + (start_after - start_before) / 2;
    }

    qsort(start_ns, CALIBRATE_SIZE, sizeof(int64_t), compare_int64);

    system_base_time = start_ns[CALIBRATE_SIZE / 2];

    printf("Calibrated ts_to_ns_factor: %f\n", ts_to_ns_factor);
    printf("Calibrated system_base_time: %ld\n", system_base_time);
}

void quicktime_init()
{
#if _WIN32
    QueryPerformanceFrequency(&qpc_freq);
#elif defined(__APPLE__)
    mach_timebase_info(&timebase_info);
#endif
    calibrate_quicktime();
}
