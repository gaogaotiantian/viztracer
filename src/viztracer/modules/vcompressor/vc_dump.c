// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#include <Python.h>
#include "vcompressor.h"
#include "vc_dump.h"

#define STRING_BUFFER_SIZE 512

#define READ_DATA(ptr, type, fptr)                                           \
{                                                                            \
    size_t s = fread(ptr, sizeof(type), 1, fptr);                            \
    if (s != 1) {                                                            \
        PyErr_SetString(PyExc_ValueError, "file is corrupted");              \
        goto clean_exit;                                                     \
    }                                                                        \
}

#define PyDict_SetItemStringULL(dct, key, val)                               \
{                                                                            \
    PyObject* o = PyLong_FromUnsignedLongLong(val);                          \
    PyDict_SetItemString(dct, key, o);                                       \
    Py_DECREF(o);                                                            \
}

#define PyDict_SetItemStringDouble(dct, key, val)                            \
{                                                                            \
    PyObject* o = PyFloat_FromDouble(val);                                   \
    PyDict_SetItemString(dct, key, o);                                       \
    Py_DECREF(o);                                                            \
}

// The input line has to be null-terminated
// This function will write the line and append a null terminator after it
#define fwritestr(line, fptr)                                                \
{                                                                            \
    fwrite(line, sizeof(char), strlen(line), fptr);                          \
    fputc('\0', fptr);                                                       \
}

#define GET_JSON_DUMPS_FUNC(func)                                            \
{                                                                            \
    if (!json_dumps_func) {                                                  \
        json_dumps_func = PyObject_GetAttrString(json_module, "dumps");      \
        func = json_dumps_func;                                              \
    } else {                                                                 \
        func = json_dumps_func;                                              \
        Py_INCREF(func);                                                     \
    }                                                                        \
}                                                                            \


#define GET_JSON_LOADS_FUNC(func)                                            \
{                                                                            \
    if (!json_loads_func) {                                                  \
        json_loads_func = PyObject_GetAttrString(json_module, "loads");      \
        func = json_loads_func;                                              \
    } else {                                                                 \
        func = json_loads_func;                                              \
        Py_INCREF(func);                                                     \
    }                                                                        \
}                                                                            \


#define PEEK_DATA(ptr, type, fptr)                                           \
{                                                                            \
    size_t s = fread(ptr, sizeof(type), 1, fptr);                            \
    if (s != 1) {                                                            \
        PyErr_SetString(PyExc_ValueError, "file is corrupted");              \
        goto clean_exit;                                                     \
    } else {                                                                 \
        fseek(fptr, -sizeof(type), SEEK_CUR);                                \
    }                                                                        \
}

/*
 * The write_encoded_int and read_encoded_int functions are used to compress
 * and decompress timestamp. For a trace file, most of the data are ts and dur.
 * So we sort the timestamp and only record diff of two between two contiguous
 * timestamp. 
 * 
 * We use a 2-bit flag to indicate how many bytes can uint64_t data be fit in.
 * For Windows, Mac and most of the Linux, the byte order is little-endian, 
 * which means if we want to record 0X12345678. The data in file would be:
 * 78 56 34 12
 * To make it simple, we just move the data left 2 bits and put the flag at 
 * the lowest position of the timestamp.
 * 
 * And the parsed timestamp is always less than 0x3FFFFFFFFFFFFFFF
*/
static inline void write_encoded_int(uint64_t num, FILE* fptr)
{
    if (num == (num & 0x3F)) {
        uint8_t encoded_num = (num << 2) | TS_6_BIT;
        fwrite(&encoded_num, sizeof(uint8_t), 1, fptr);
    } else if (num == (num & 0x3FFF)) {
        uint16_t encoded_num = (num << 2) | TS_14_BIT;
        fwrite(&encoded_num, sizeof(uint16_t), 1, fptr);
    } else if (num == (num & 0x3FFFFFFF)) {
        uint32_t encoded_num = (num << 2) | TS_30_BIT;
        fwrite(&encoded_num, sizeof(uint32_t), 1, fptr);
    } else {
        uint64_t encoded_num = (num << 2) | TS_62_BIT;
        fwrite(&encoded_num, sizeof(uint64_t), 1, fptr);
    }
}

static inline int read_encoded_int(uint64_t *num, FILE* fptr)
{
    uint8_t flag;
    uint8_t encoded_num_8_bit = 0;
    uint16_t encoded_num_16_bit = 0;
    uint32_t encoded_num_32_bit = 0;
    uint64_t encoded_num_64_bit = 0;
    PEEK_DATA(&flag, uint8_t, fptr)
    switch (flag & 0x03)
    {
        case TS_6_BIT:
            READ_DATA(&encoded_num_8_bit, uint8_t, fptr)
            (*num) = encoded_num_8_bit >> 2;
            break;
        case TS_14_BIT:
            READ_DATA(&encoded_num_16_bit, uint16_t, fptr)
            (*num) = encoded_num_16_bit >> 2;
            break;        
        case TS_30_BIT:
            READ_DATA(&encoded_num_32_bit, uint32_t, fptr)
            (*num) = encoded_num_32_bit >> 2;
            break;
        case TS_62_BIT:
            READ_DATA(&encoded_num_64_bit, uint64_t, fptr)
            (*num) = encoded_num_64_bit >> 2;
            break;
        default:
            break;
    }
clean_exit:
    if (PyErr_Occurred()) {
        return 1;
    }
    return 0;
}


int freadstrn(char* buffer, int n, FILE* fptr) 
{
    int c;
    int idx = 0;
    while (1) {
        c = fgetc(fptr);
        if (c == EOF || c == '\0') {
            buffer[idx++] = '\0';
            break;
        } else {
            buffer[idx++] = c;
        }
        if (idx == n) {
            break;
        }
    }
    return idx;
}

char* freadstr(FILE* fptr)
{
    char* str = NULL;
    int c = 0;
    size_t len = 256;
    size_t idx = 0;
    str = malloc(len * sizeof(char));
    if (str == NULL) {
        return NULL;
    }
    while ((c = fgetc(fptr)) != EOF && c != '\0') {
        str[idx++] = c;
        if (idx == len) {
            len *= 2;
            str = realloc(str, len * sizeof(char));
            if (str == NULL) {
                return NULL;
            }
        }
    }
    str[idx++] = '\0';
    return str;
}

int dump_metadata(FILE* fptr)
{
    uint64_t version = VCOMPRESSOR_VERSION;
    if (!fptr) {
        return -1;
    }

    fwrite(&version, 1, sizeof(uint64_t), fptr);

    return 0;
}

int dump_parsed_trace_events(PyObject* trace_events, FILE* fptr)
{
    // Dump process and thread names
    PyObject* process_names  = PyDict_GetItemString(trace_events, "process_names");
    PyObject* thread_names   = PyDict_GetItemString(trace_events, "thread_names");
    PyObject* fee_events     = PyDict_GetItemString(trace_events, "fee_events");
    PyObject* counter_events = PyDict_GetItemString(trace_events, "counter_events");
    PyObject* instant_events = PyDict_GetItemString(trace_events, "instant_events");
    Py_ssize_t ppos = 0;
    PyObject* key   = NULL;
    PyObject* value = NULL;

    // Iterate through process names
    ppos = 0;
    while (PyDict_Next(process_names, &ppos, &key, &value)) {
        uint64_t pid = PyLong_AsLong(PyTuple_GetItem(key, 0));
        uint64_t tid = PyLong_AsLong(PyTuple_GetItem(key, 1));
        const char* name = PyUnicode_AsUTF8(value);
        fputc(VC_HEADER_PROCESS_NAME, fptr);
        fwrite(&pid, sizeof(uint64_t), 1, fptr);
        fwrite(&tid, sizeof(uint64_t), 1, fptr);
        fwritestr(name, fptr);
    }

    // Iterate through thread names
    ppos = 0;
    while (PyDict_Next(thread_names, &ppos, &key, &value)) {
        uint64_t pid = PyLong_AsLong(PyTuple_GetItem(key, 0));
        uint64_t tid = PyLong_AsLong(PyTuple_GetItem(key, 1));
        const char* name = PyUnicode_AsUTF8(value);
        fputc(VC_HEADER_THREAD_NAME, fptr);
        fwrite(&pid, sizeof(uint64_t), 1, fptr);
        fwrite(&tid, sizeof(uint64_t), 1, fptr);
        fwritestr(name, fptr);
    }

    // Iterate through fee events
    ppos = 0;
    while (PyDict_Next(fee_events, &ppos, &key, &value)) {
        uint64_t pid = PyLong_AsLong(PyTuple_GetItem(key, 0));
        uint64_t tid = PyLong_AsLong(PyTuple_GetItem(key, 1));
        const char* name = PyUnicode_AsUTF8(PyTuple_GetItem(key, 2));
        uint64_t ts_size = PyList_GET_SIZE(value);
        int64_t last_ts = 0;
        fputc(VC_HEADER_FEE, fptr);
        fwrite(&pid, sizeof(uint64_t), 1, fptr);
        fwrite(&tid, sizeof(uint64_t), 1, fptr);
        fwritestr(name, fptr);
        fwrite(&ts_size, sizeof(uint64_t), 1, fptr);
        if (!PyObject_CallMethod(value, "sort", NULL)) {
            goto clean_exit;
        }
        for (Py_ssize_t idx = 0; idx < (Py_ssize_t)ts_size; idx++) {
            PyObject * event_ts_tuple = PyList_GET_ITEM(value, idx);
            double ts = PyFloat_AsDouble(PyTuple_GET_ITEM(event_ts_tuple, 0));
            double dur = PyFloat_AsDouble(PyTuple_GET_ITEM(event_ts_tuple, 1));
            int64_t ts64 = ts * 100;
            uint64_t dur64 = dur * 100;
            uint64_t delta_ts = ts64 - last_ts;
            last_ts = ts64;
            if (idx == 0) {
                // write the first timestamp as int64_t, for timestamp on windows may be negative
                fwrite(&ts64, sizeof(int64_t), 1, fptr);
            } else {
                write_encoded_int(delta_ts, fptr);
            }
            write_encoded_int(dur64, fptr);
        }
    }

    // Iterate through counter events
    ppos = 0;
    while (PyDict_Next(counter_events, &ppos, &key, &value)) {
        uint64_t pid = PyLong_AsLong(PyTuple_GetItem(key, 0));
        uint64_t tid = PyLong_AsLong(PyTuple_GetItem(key, 1));
        const char* name = PyUnicode_AsUTF8(PyTuple_GetItem(key, 2));
        fputc(VC_HEADER_COUNTER_EVENTS, fptr);
        fwrite(&pid, sizeof(uint64_t), 1, fptr);
        fwrite(&tid, sizeof(uint64_t), 1, fptr);
        fwritestr(name, fptr);
        if (diff_and_write_counter_args(value, fptr) != 0) {
            goto clean_exit;
        }
    }

    // Iterate through instant events
    ppos = 0;
    while (PyDict_Next(instant_events, &ppos, &key, &value)) {
        uint64_t pid = PyLong_AsLong(PyTuple_GetItem(key, 0));
        uint64_t tid = PyLong_AsLong(PyTuple_GetItem(key, 1));
        const char* name = PyUnicode_AsUTF8(PyTuple_GetItem(key, 2));
        char scope = PyUnicode_AsUTF8(PyTuple_GetItem(key, 3))[0];
        fputc(VC_HEADER_INSTANT_EVENTS, fptr);
        fwrite(&pid, sizeof(uint64_t), 1, fptr);
        fwrite(&tid, sizeof(uint64_t), 1, fptr);
        fwritestr(name, fptr);
        fputc(scope, fptr);
        if (write_instant_args(value, fptr) != 0) {
            goto clean_exit;
        }
    }
clean_exit:
    if (PyErr_Occurred()) {
        return 1;
    }

    return 0;
}

int write_instant_args(PyObject* instant_args, FILE* fptr) {
    PyObject * dumps_func = NULL;
    PyObject * key        = NULL;
    PyObject * value      = NULL;
    PyObject * value_str  = NULL;
    PyObject * dumps_arg  = NULL;
    Py_ssize_t ppos   = 0;
    uint64_t ts_count = 0;
    uint64_t ts_64    = 0;

    dumps_func = PyObject_GetAttrString(json_module, "dumps");
    if (!dumps_func) {
        goto clean_exit;
    }
    ts_count = PyDict_Size(instant_args);
    fwrite(&ts_count, sizeof(uint64_t), 1, fptr);
    while (PyDict_Next(instant_args, &ppos, &key, &value)) {
        dumps_arg = PyTuple_New(1);
        PyTuple_SetItem(dumps_arg, 0, value);
        Py_INCREF(value);
        value_str = PyObject_CallObject(dumps_func, dumps_arg);
        Py_DECREF(dumps_arg);
        if (!value_str) {
            goto clean_exit;
        }
        ts_64 = PyFloat_AsDouble(key) * 1000;
        fwrite(&ts_64, sizeof(uint64_t), 1, fptr);
        fwritestr(PyUnicode_AsUTF8(value_str), fptr);
        Py_DECREF(value_str);
    }

clean_exit:
    Py_XDECREF(dumps_func);

    if (PyErr_Occurred()) {
        return 1;
    }

    return 0;
}

PyObject *
load_instant_event(FILE* fptr) {
    PyObject* instant_events_list = PyList_New(0);
    PyObject* instant_cat    = PyUnicode_FromString("INSTANT");
    PyObject* instant_ph     = PyUnicode_FromString("i");
    PyObject* scope_t        = PyUnicode_FromString("t");
    PyObject* scope_p        = PyUnicode_FromString("p");
    PyObject* scope_g        = PyUnicode_FromString("g");
    PyObject* instant_scope  = NULL;
    PyObject* instant_tid    = NULL;
    PyObject* instant_pid    = NULL;
    PyObject* instant_name   = NULL;
    PyObject* instant_arg    = NULL;
    PyObject* instant_event  = NULL;
    PyObject* loads_func     = NULL;
    PyObject* loads_arg      = NULL;
    uint64_t pid = 0;
    uint64_t tid = 0;
    uint64_t arg_count = 0;
    uint64_t ts_64 = 0;
    char* name = NULL;
    char* arg_string = NULL;
    char scope = 't';

    loads_func = PyObject_GetAttrString(json_module, "loads");
    if (!loads_func) {
        goto clean_exit;
    }

    READ_DATA(&pid, uint64_t, fptr);
    READ_DATA(&tid, uint64_t, fptr);
    name = freadstr(fptr);
    READ_DATA(&scope, char, fptr);
    instant_name = PyUnicode_FromString(name);
    instant_pid = PyLong_FromUnsignedLongLong(pid);
    instant_tid = PyLong_FromUnsignedLongLong(tid); 
    free(name);
    switch (scope)
    {
        case 't':
            instant_scope = scope_t;
            break;
        case 'p':
            instant_scope = scope_p;
            break;
        case 'g':
            instant_scope = scope_g;
            break;
        default:
            PyErr_SetString(PyExc_RuntimeError, "invalid scope");
            goto clean_exit;
    }
    READ_DATA(&arg_count, uint64_t, fptr);
    for (uint64_t i = 0; i < arg_count; i++) {
        instant_event = PyDict_New();
        READ_DATA(&ts_64, uint64_t, fptr);
        PyDict_SetItemStringDouble(instant_event, "ts", (double)ts_64 / 1000);
        arg_string = freadstr(fptr);
        loads_arg = PyTuple_New(1);
        PyTuple_SetItem(loads_arg, 0, PyUnicode_FromString(arg_string));
        free(arg_string);
        instant_arg = PyObject_CallObject(loads_func, loads_arg);
        Py_DECREF(loads_arg);
        if (!instant_arg) {
            goto clean_exit;
        }
        PyDict_SetItemString(instant_event, "args", instant_arg);
        Py_DECREF(instant_arg);
        PyDict_SetItemString(instant_event, "s", instant_scope);
        PyDict_SetItemString(instant_event, "name", instant_name);
        PyDict_SetItemString(instant_event, "pid", instant_pid);
        PyDict_SetItemString(instant_event, "tid", instant_tid);
        PyDict_SetItemString(instant_event, "cat", instant_cat);
        PyDict_SetItemString(instant_event, "ph", instant_ph);
        PyList_Append(instant_events_list, instant_event);
        Py_DECREF(instant_event);
    }

clean_exit:
    Py_XDECREF(instant_pid);
    Py_XDECREF(instant_tid);
    Py_XDECREF(instant_name);
    Py_XDECREF(loads_func);
    Py_DECREF(instant_cat);
    Py_DECREF(instant_ph);
    Py_DECREF(scope_t);
    Py_DECREF(scope_p);
    Py_DECREF(scope_g);

    if (PyErr_Occurred()) {
        Py_DECREF(instant_events_list);
        return NULL;
    }

    return instant_events_list;
}

int diff_and_write_counter_args(PyObject* counter_args, FILE* fptr) {
    /* there may be several args in a counter, log them all may take more spaces
    *  so this step is to do diffing between two contiguous timestamp
    *  and finally we only log those changed args
    *  Here's a counter_args example that we parsed
    *  {
    *      1.1: {"a": 20, "b": 10}
    *      2.2: {"a": 30, "b": 10}
    *  }
    *  In this case, "b" value is not changed, so we only need to log
    *  {
    *      1.1: {"a": 20, "b": 10}
    *      2.2: {"a": 30}
    *  }
    */
    PyObject* cached_args_dict = PyDict_New();
    PyObject* diffed_args = PyDict_New();
    PyObject* ts_keys = PyDict_Keys(counter_args);
    PyObject* ts = NULL;
    PyObject* cur_diffed_arg = NULL;
    PyObject* cur_counter_arg = NULL;
    PyObject* arg_key_list = NULL;
    PyObject* counter_arg_key = NULL;
    PyObject* counter_arg_value = NULL;
    PyObject* cached_arg_value = NULL;
    PyObject* overflowed_num_string = NULL;
    Py_ssize_t ppos = 0;
    uint64_t ts_key_count = 0;
    uint64_t arg_nums = 0;
    // sort the args by timestamp so we can diff
    if (!ts_keys || !PyList_Check(ts_keys)) {
        PyErr_SetString(PyExc_ValueError, "failed to get timestamp list");
        goto clean_exit;
    }
    ts_key_count = PyList_GET_SIZE(ts_keys);
    if (PyList_Sort(ts_keys) == -1) {
        goto clean_exit;
    }
    /* Do diffing between two timestamps and store the result.
    *  In this for loop, we iterate all the counter_args by the sort of timestamp.
    *  And we mainly have three variables used to do the diffing:
    *      cur_counter_arg: the full args of this timestamp
    *      cached_args_dict: the full args of last timestamp
    *      cur_diffed_arg: diffed result between cached_args_dict and cur_counter_arg
    */
    for (uint64_t i = 0; i < ts_key_count; i++) {
        ts = PyList_GET_ITEM(ts_keys, i);
        cur_counter_arg = PyDict_GetItem(counter_args, ts);
        cur_diffed_arg = PyDict_New();
        ppos = 0;
        /*  This while statement is to find the different arg between cur_counter_arg and cached_args_dict.
        *   It will iterate the arg value of cur_counter_arg, and compare with the value in cached_args_dict.
        *   If the value is same, just ignore this value
        *   If the value is different, then store it in cur_diffed_arg and update it in cached_args_dict.
        */
        while (PyDict_Next(cur_counter_arg, &ppos, &counter_arg_key, &counter_arg_value)) {
            cached_arg_value = PyDict_GetItem(cached_args_dict, counter_arg_key);
            if (!cached_arg_value) {
                PyDict_SetItem(cached_args_dict, counter_arg_key, counter_arg_value);
                PyDict_SetItem(cur_diffed_arg, counter_arg_key, counter_arg_value);
            } else {
                int compare_result = PyObject_RichCompareBool(cached_arg_value, counter_arg_value, Py_EQ);
                if (compare_result == -1) {
                    // compare error 
                    goto clean_exit;
                } else if (compare_result == 0) {
                    // if value is not equal in last timestamp, store the newest value
                    PyDict_SetItem(cached_args_dict, counter_arg_key, counter_arg_value);
                    PyDict_SetItem(cur_diffed_arg, counter_arg_key, counter_arg_value);
                }
            }
        }
        ppos = 0;
        /*  This while statement is to find the arg that is in cached_args_dict but not in cur_counter_arg.
        *   Considering the situation that an arg is deleted at some timestamp, for example:
        *      {
        *          1.1: {"a": 20, "b": 10}
        *          2.2: {"a": 20}
        *      }
        *   In this case, we need to mark b value as UNKNOWN at timestamp 2.2
        *   This step is to iterate arg in cached_args_dict and determine if the arg is in cur_counter_arg
        *   Normally, the value of counter_arg is always numeric
        *   So we use Py_None to mark the value as UNKNOWN
        */
        while (PyDict_Next(cached_args_dict, &ppos, &counter_arg_key, &cached_arg_value)) {
            counter_arg_value = PyDict_GetItem(cur_counter_arg, counter_arg_key);
            if (!counter_arg_value && cached_arg_value != Py_None) {
                PyDict_SetItem(cached_args_dict, counter_arg_key, Py_None);
                PyDict_SetItem(cur_diffed_arg, counter_arg_key, Py_None);
            }
        }
        PyDict_SetItem(diffed_args, ts, cur_diffed_arg);
        Py_DECREF(cur_diffed_arg);
    }
    // write all the arg keys
    // write the number of timestamp of this counter
    arg_nums = PyDict_Size(cached_args_dict);
    fwrite(&arg_nums, sizeof(uint64_t), 1, fptr);
    arg_key_list = PyDict_Keys(cached_args_dict);
    if (!arg_key_list) {
        PyErr_SetString(PyExc_ValueError, "failed to get arg name list");
        goto clean_exit;
    }
    // write all the name for all arguments appeared
    for (uint64_t i = 0; i < arg_nums; i++) {
        const char * key_name = NULL;
        counter_arg_key = PyList_GetItem(arg_key_list, i);
        key_name = PyUnicode_AsUTF8(counter_arg_key);
        fwritestr(key_name, fptr);
    }
    // write [timestamp - values] * ts_key_count
    fwrite(&ts_key_count, sizeof(uint64_t), 1, fptr);
    for (uint64_t i = 0; i < ts_key_count; i++) {
        double ts_double = 0;
        int64_t ts_64 = 0;
        ts = PyList_GET_ITEM(ts_keys, i);
        cur_diffed_arg = PyDict_GetItem(diffed_args, ts);
        ts_double = PyFloat_AsDouble(ts);
        ts_64 = ts_double * 1000;
        fwrite(&ts_64, sizeof(int64_t), 1, fptr);
        for (uint64_t j = 0; j < arg_nums; j++) {
            counter_arg_value = PyDict_GetItem(cur_diffed_arg, PyList_GET_ITEM(arg_key_list, j));
            if (!counter_arg_value) {
                fputc(VC_HEADER_COUNTER_ARG_SAME, fptr);
            } else if (PyLong_CheckExact(counter_arg_value)) {
                // if PyLongObject is overflowed, just store the string 
                int overflow = 0;
                int64_t counter_value_int64 = PyLong_AsLongLongAndOverflow(counter_arg_value, &overflow);
                if (overflow == 0) {
                    fputc(VC_HEADER_COUNTER_ARG_LONG, fptr);
                    fwrite(&counter_value_int64, sizeof(int64_t), 1, fptr);
                } else {
                    const char * num_string = NULL;
                    overflowed_num_string = PyObject_Repr(counter_arg_value);
                    num_string = PyUnicode_AsUTF8(overflowed_num_string);
                    fputc(VC_HEADER_COUNTER_ARG_LONG_STRING, fptr);
                    fwritestr(num_string, fptr);
                    Py_DECREF(overflowed_num_string);
                }
            } else if (PyFloat_CheckExact(counter_arg_value)) {
                double counter_value_double = PyFloat_AsDouble(counter_arg_value);
                fputc(VC_HEADER_COUNTER_ARG_FLOAT, fptr);
                fwrite(&counter_value_double, sizeof(double), 1, fptr);
            } else if (counter_arg_value == Py_None) {
                fputc(VC_HEADER_COUNTER_ARG_UNKNOWN, fptr);
            } else {
                PyErr_SetString(PyExc_ValueError, "Counter can only take numeric values");
                goto clean_exit;
            }
        }
    }

clean_exit:
    Py_XDECREF(arg_key_list);
    Py_XDECREF(ts_keys);
    Py_DECREF(cached_args_dict);
    Py_DECREF(diffed_args);

    if (PyErr_Occurred()) {
        return 1;
    }

    return 0;
}

PyObject*
load_counter_event(FILE* fptr)
{
    PyObject* counter_events_list = PyList_New(0);
    PyObject* arg_key_list = PyList_New(0);
    PyObject* cached_args = PyDict_New();
    PyObject* counter_ph = PyUnicode_FromString("C");
    PyObject* counter_event = NULL;
    PyObject* current_arg = NULL;
    PyObject* counter_arg_key = NULL;
    PyObject* counter_arg_value = NULL;
    PyObject* counter_name = NULL;
    PyObject* counter_pid = NULL;
    PyObject* counter_tid = NULL;
    uint64_t pid = 0;
    uint64_t tid = 0;
    uint64_t arg_key_count = 0;
    uint64_t counter_event_count = 0;
    uint64_t ts_64 = 0;
    uint8_t header = 0;
    int64_t value_longlong = 0;
    double value_double = 0;
    char buffer[STRING_BUFFER_SIZE] = {0};
    char* string_value = NULL;
    char* name = NULL;

    // read pid, tid, name and keys
    READ_DATA(&pid, uint64_t, fptr);
    READ_DATA(&tid, uint64_t, fptr);
    name = freadstr(fptr);
    READ_DATA(&arg_key_count, uint64_t, fptr);
    counter_name = PyUnicode_FromString(name);
    free(name);
    counter_pid = PyLong_FromUnsignedLongLong(pid);
    counter_tid = PyLong_FromUnsignedLongLong(tid);
    for (uint64_t i = 0; i < arg_key_count; i++) {
        freadstrn(buffer, STRING_BUFFER_SIZE - 1, fptr);
        counter_arg_key = PyUnicode_FromString(buffer);
        PyList_Append(arg_key_list, counter_arg_key);
        Py_DECREF(counter_arg_key);
    }

    // read counter events
    // cached_args stores the newest value
    // current_arg stores the counter arg of current timestamp
    READ_DATA(&counter_event_count, uint64_t, fptr);
    for (uint64_t i = 0; i < counter_event_count; i++) {
        current_arg = PyDict_New();
        READ_DATA(&ts_64, uint64_t, fptr);
        for (uint64_t j = 0; j < arg_key_count; j++) {
            READ_DATA(&header, uint8_t, fptr);
            counter_arg_key = PyList_GetItem(arg_key_list, j);
            // counter arg not change means current value is same with it in last arg
            // so we need to read it from cached_args 
            // other state means current value is different from it in last arg
            // so we need to read it from file and save it in cached_args
            switch (header)
            {
                case VC_HEADER_COUNTER_ARG_UNKNOWN:
                    PyDict_SetItem(cached_args, counter_arg_key, Py_None);
                    break;
                case VC_HEADER_COUNTER_ARG_SAME:
                    counter_arg_value = PyDict_GetItem(cached_args, counter_arg_key);
                    if (counter_arg_value && counter_arg_value != Py_None) {
                        PyDict_SetItem(current_arg, counter_arg_key, counter_arg_value);
                    }
                    break;
                case VC_HEADER_COUNTER_ARG_LONG:
                    READ_DATA(&value_longlong, int64_t, fptr);
                    counter_arg_value = PyLong_FromLongLong(value_longlong);
                    PyDict_SetItem(current_arg, counter_arg_key, counter_arg_value);
                    PyDict_SetItem(cached_args, counter_arg_key, counter_arg_value);
                    Py_DECREF(counter_arg_value);
                    break;
                case VC_HEADER_COUNTER_ARG_FLOAT:
                    READ_DATA(&value_double, double, fptr);
                    counter_arg_value = PyFloat_FromDouble(value_double);
                    PyDict_SetItem(current_arg, counter_arg_key, counter_arg_value);
                    PyDict_SetItem(cached_args, counter_arg_key, counter_arg_value);
                    Py_DECREF(counter_arg_value);
                    break;
                case VC_HEADER_COUNTER_ARG_LONG_STRING:
                    string_value = freadstr(fptr);
                    counter_arg_value = PyLong_FromString(string_value, NULL, 0);
                    free(string_value);
                    PyDict_SetItem(current_arg, counter_arg_key, counter_arg_value);
                    PyDict_SetItem(cached_args, counter_arg_key, counter_arg_value);
                    Py_DECREF(counter_arg_value);
                    break;
                default:
                    PyErr_SetString(PyExc_ValueError, "counter arg header error!");
                    goto clean_exit;
            }
        }
        counter_event = PyDict_New();
        PyList_Append(counter_events_list, counter_event);
        Py_DECREF(counter_event);
        PyDict_SetItemString(counter_event, "name", counter_name);
        PyDict_SetItemString(counter_event, "pid", counter_pid);
        PyDict_SetItemString(counter_event, "tid", counter_tid);
        PyDict_SetItemString(counter_event, "ph", counter_ph);
        PyDict_SetItemString(counter_event, "args", current_arg);
        Py_DECREF(current_arg);
        PyDict_SetItemStringDouble(counter_event, "ts", (double)ts_64 / 1000);
    }

clean_exit:
    if (counter_name) {
        Py_DECREF(counter_name);
    }
    if (counter_pid) {
        Py_DECREF(counter_pid);
    }
    if (counter_tid) {
        Py_DECREF(counter_tid);
    }
    
    Py_DECREF(counter_ph);
    Py_DECREF(arg_key_list);
    Py_DECREF(cached_args);

    if (PyErr_Occurred()) {
        Py_DECREF(counter_events_list);
        return NULL; 
    }

    return counter_events_list;
}

PyObject*
load_events_from_file(FILE* fptr)
{
    uint64_t version = 0;
    uint8_t header = 0;
    PyObject* parsed_events = PyDict_New();
    PyObject* trace_events = PyList_New(0);
    PyObject* file_info = NULL;
    PyObject* name = NULL;
    PyObject* event = NULL;
    PyObject* counter_events = NULL;
    PyObject* instant_events = NULL;
    uint64_t pid = 0;
    uint64_t tid = 0;
    uint64_t count = 0;
    uint64_t ts = 0;
    uint64_t dur = 0;
    int64_t last_ts = 0;
    PyObject* args = NULL;
    PyObject* unicode_X = PyUnicode_FromString("X");
    PyObject* unicode_M = PyUnicode_FromString("M");
    PyObject* unicode_FEE = PyUnicode_FromString("FEE");
    PyObject* unicode_process_name = PyUnicode_FromString("process_name");
    PyObject* unicode_thread_name = PyUnicode_FromString("thread_name");

    char buffer[STRING_BUFFER_SIZE] = {0};

    READ_DATA(&version, uint64_t, fptr);

    PyDict_SetItemString(parsed_events, "traceEvents", trace_events);
    Py_DECREF(trace_events);

    while (fread(&header, sizeof(uint8_t), 1, fptr)) {
        switch (header) {
            case VC_HEADER_PROCESS_NAME:
                event = PyDict_New();
                READ_DATA(&pid, uint64_t, fptr);
                READ_DATA(&tid, uint64_t, fptr);
                freadstrn(buffer, STRING_BUFFER_SIZE - 1, fptr);
                name = PyUnicode_FromString(buffer);
                event = PyDict_New();
                args = PyDict_New();
                PyDict_SetItemString(event, "ph", unicode_M);
                PyDict_SetItemString(event, "name", unicode_process_name);
                PyDict_SetItemStringULL(event, "pid", pid);
                PyDict_SetItemStringULL(event, "tid", tid);
                PyDict_SetItemString(event, "args", args);
                PyDict_SetItemString(args, "name", name);
                PyList_Append(trace_events, event);
                Py_DECREF(name);
                Py_DECREF(event);
                Py_DECREF(args);
                break;
            case VC_HEADER_THREAD_NAME:
                event = PyDict_New();
                READ_DATA(&pid, uint64_t, fptr);
                READ_DATA(&tid, uint64_t, fptr);
                freadstrn(buffer, STRING_BUFFER_SIZE - 1, fptr);
                name = PyUnicode_FromString(buffer);
                event = PyDict_New();
                args = PyDict_New();
                PyDict_SetItemString(event, "ph", unicode_M);
                PyDict_SetItemString(event, "name", unicode_thread_name);
                PyDict_SetItemStringULL(event, "pid", pid);
                PyDict_SetItemStringULL(event, "tid", tid);
                PyDict_SetItemString(event, "args", args);
                PyDict_SetItemString(args, "name", name);
                PyList_Append(trace_events, event);
                Py_DECREF(name);
                Py_DECREF(event);
                Py_DECREF(args);
                break;
            case VC_HEADER_FEE:
                READ_DATA(&pid, uint64_t, fptr);
                READ_DATA(&tid, uint64_t, fptr);
                freadstrn(buffer, STRING_BUFFER_SIZE - 1, fptr);
                READ_DATA(&count, uint64_t, fptr);
                name = PyUnicode_FromString(buffer);
                last_ts = 0;
                for (uint64_t i = 0; i < count; i++) {
                    if (i == 0) {
                        READ_DATA(&ts, int64_t, fptr);
                    } else {
                        if (read_encoded_int(&ts, fptr) != 0) {
                            goto clean_exit;
                        }
                    }
                    if (read_encoded_int(&dur, fptr) != 0) {
                        goto clean_exit;
                    }
                    event = PyDict_New();
                    PyDict_SetItemString(event, "ph", unicode_X);
                    PyDict_SetItemString(event, "name", name);
                    PyDict_SetItemString(event, "cat", unicode_FEE);
                    PyDict_SetItemStringULL(event, "pid", pid);
                    PyDict_SetItemStringULL(event, "tid", tid);
                    last_ts = ts + last_ts;
                    PyDict_SetItemStringDouble(event, "ts", (double)last_ts / 100);
                    PyDict_SetItemStringDouble(event, "dur", (double)dur / 100);
                    PyList_Append(trace_events, event);
                    Py_DECREF(event);
                }
                Py_DECREF(name);
                break;
            case VC_HEADER_FILE_INFO:
                file_info = load_file_info(fptr);
                if (!file_info) {
                    goto clean_exit;
                }
                PyDict_SetItemString(parsed_events, "file_info", file_info);
                Py_DECREF(file_info);
                break;
            case VC_HEADER_COUNTER_EVENTS:
                counter_events = load_counter_event(fptr);
                if (!counter_events) {
                    goto clean_exit;
                }
                PyObject_CallMethod(trace_events, "extend", "O", counter_events);
                Py_DECREF(counter_events);
                if (PyErr_Occurred()) {
                    goto clean_exit;
                }
                break;
            case VC_HEADER_INSTANT_EVENTS:
                instant_events = load_instant_event(fptr);
                if (!instant_events) {
                    goto clean_exit;
                }
                PyObject_CallMethod(trace_events, "extend", "O", instant_events);
                Py_DECREF(instant_events);
                if (PyErr_Occurred()) {
                    goto clean_exit;
                }
                break;
            default:
                printf("wrong header %d\n", header);
        }
    }

clean_exit:
    Py_DECREF(unicode_X);
    Py_DECREF(unicode_M);
    Py_DECREF(unicode_FEE);
    Py_DECREF(unicode_process_name);
    Py_DECREF(unicode_thread_name);

    if (PyErr_Occurred()) {
        Py_DECREF(parsed_events);
        return NULL;
    }
    return parsed_events;

}


int dump_file_info(PyObject* file_info, FILE* fptr)
{
    const char * buffer = NULL;
    uint64_t content_length = 0;
    uint64_t compression_length = 0;
    PyObject* json_ret = NULL;    
    PyObject* zlib_ret = NULL;
    PyObject* bytes_data = NULL;
    PyObject* dumps_func = NULL;
    PyObject* compress_func = NULL;
    PyObject* json_args = NULL;
    PyObject* zlib_args = NULL;
    
    dumps_func = PyObject_GetAttrString(json_module, "dumps");
    if (!dumps_func) {
        goto clean_exit;
    }

    compress_func = PyObject_GetAttrString(zlib_module, "compress");
    if (!compress_func) {
        goto clean_exit;
    }

    // json dumps file_info
    json_args = PyTuple_New(1);
    // file_info points to the file_info in json object we compress
    // PyTuple_SetItem steals the reference, but we don't want to release file_info here
    // So we need to call Py_INCREF here
    PyTuple_SetItem(json_args, 0, file_info);
    Py_INCREF(file_info); 
    json_ret = PyObject_CallObject(dumps_func, json_args);
    Py_DECREF(json_args);
    if (!json_ret) {
        goto clean_exit;
    }

    // convert string to bytes
    bytes_data = PyObject_CallMethod(json_ret, "encode", NULL);
    Py_DECREF(json_ret);
    if (!bytes_data) {
        goto clean_exit;
    }
    // Make sure that PyBytes_Size succeed
    if (!PyBytes_Check(bytes_data)) {
        // need to release bytes_data here, bytes_data will not release after clean_exit
        Py_DECREF(bytes_data);
        PyErr_SetString(PyExc_ValueError, "Failed to convert string to bytes");
        goto clean_exit;
    }

    // compress bytes data
    zlib_args = PyTuple_New(1);
    content_length = PyBytes_Size(bytes_data);
    PyTuple_SetItem(zlib_args, 0, bytes_data);
    zlib_ret = PyObject_CallObject(compress_func, zlib_args);
    // zlib_args steals bytes_data, so release zlib_args will release bytes_data
    Py_DECREF(zlib_args);
    if (!zlib_ret) {
        goto clean_exit;
    }
    if (!PyBytes_Check(zlib_ret)) {
        Py_DECREF(zlib_ret);
        PyErr_SetString(PyExc_ValueError, "zlib.compress() returns a none bytes object");
        goto clean_exit;
    }
    compression_length = PyBytes_Size(zlib_ret);
    buffer = PyBytes_AsString(zlib_ret);

    // write data
    fputc(VC_HEADER_FILE_INFO, fptr);
    fwrite(&compression_length, sizeof(uint64_t), 1, fptr);
    fwrite(&content_length, sizeof(uint64_t), 1, fptr);
    fwrite(buffer, sizeof(char), compression_length, fptr);
    // release zlib_ret after write, buffer points to zlib_ret->ob_sval;
    Py_DECREF(zlib_ret);

clean_exit:
    if (dumps_func) {
        Py_DECREF(dumps_func);
    }
    if (compress_func) {
        Py_DECREF(compress_func);
    }

    if (PyErr_Occurred()) {
        return 1;
    }

    return 0;
}

PyObject*
load_file_info(FILE* fptr)
{
    unsigned char* compression_buffer = NULL;
    uint64_t compression_length = 0;
    uint64_t content_length = 0;
    size_t read_length = 0;
    PyObject* file_info = NULL;
    PyObject* zlib_ret = NULL;
    PyObject* bytes_data = NULL;
    PyObject* string_data = NULL;
    PyObject* loads_func = NULL;
    PyObject* json_args = NULL;
    PyObject* decompress_func = NULL;
    PyObject* zlib_args = NULL;
    READ_DATA(&compression_length, uint64_t, fptr);
    READ_DATA(&content_length, uint64_t, fptr);

    decompress_func = PyObject_GetAttrString(zlib_module, "decompress");
    if (!decompress_func) {
        goto clean_exit;
    }

    loads_func = PyObject_GetAttrString(json_module, "loads");
    if (!loads_func) {
        goto clean_exit;
    }

    // read compressed data
    compression_buffer = (unsigned char*)malloc(sizeof(char) * compression_length);
    if (compression_buffer == NULL) {
        PyErr_Format(PyExc_RuntimeError, "Failed to malloc memory size %lld", compression_length);
        goto clean_exit;
    }
    read_length = fread(compression_buffer, sizeof(char), compression_length, fptr);
    if (read_length != compression_length) {
        PyErr_SetString(PyExc_ValueError, "file is corrupted");
        goto clean_exit;
    }         
    bytes_data = PyBytes_FromStringAndSize((const char *)compression_buffer, compression_length);
    free(compression_buffer);
    if (!bytes_data) {
        // There's error handling in PyBytes_FromStringAndSize
        goto clean_exit;
    }

    // decompress data
    zlib_args = PyTuple_New(1);
    PyTuple_SetItem(zlib_args, 0, bytes_data);
    zlib_ret = PyObject_CallObject(decompress_func, zlib_args);
    Py_DECREF(zlib_args);
    if (!zlib_ret) {
        goto clean_exit;
    }
    if (!PyBytes_Check(zlib_ret)) {
        Py_DECREF(zlib_ret);
        PyErr_SetString(PyExc_ValueError, "zlib.decompress() returns a none bytes object");
        goto clean_exit;
    }
    if ((uint64_t)PyBytes_Size(zlib_ret) != content_length) {
        Py_DECREF(zlib_ret);
        PyErr_SetString(PyExc_ValueError, "Decompressed content length doesn't match, file may be corrupted");
        goto clean_exit;
    }

    // decode depressed bytes to string
    string_data = PyObject_CallMethod(zlib_ret, "decode", NULL);
    Py_DECREF(zlib_ret);
    if (!string_data) {
        goto clean_exit;
    }

    // convert string to json
    json_args = PyTuple_New(1);
    PyTuple_SetItem(json_args, 0, string_data);
    file_info = PyObject_CallObject(loads_func, json_args);
    Py_DECREF(json_args);
    if (!file_info) {
        goto clean_exit;
    }

clean_exit:
    if (loads_func) {
        Py_DECREF(loads_func);
    }
    if (decompress_func) {
        Py_DECREF(decompress_func);
    }

    if (PyErr_Occurred()) {
        return NULL;
    }

    return file_info;
}
