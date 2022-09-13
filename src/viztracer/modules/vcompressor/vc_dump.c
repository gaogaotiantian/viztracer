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
    PyObject* process_names = PyDict_GetItemString(trace_events, "process_names");
    PyObject* thread_names  = PyDict_GetItemString(trace_events, "thread_names");
    PyObject* fee_events    = PyDict_GetItemString(trace_events, "fee_events");
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
        fputc(VC_HEADER_FEE, fptr);
        fwrite(&pid, sizeof(uint64_t), 1, fptr);
        fwrite(&tid, sizeof(uint64_t), 1, fptr);
        fwritestr(name, fptr);
        fwrite(&ts_size, sizeof(uint64_t), 1, fptr);
        for (Py_ssize_t idx = 0; idx < (Py_ssize_t)ts_size; idx++) {
            double ts = PyFloat_AsDouble(PyList_GET_ITEM(value, idx));
            int64_t ts64 = ts * 1000;
            fwrite(&ts64, sizeof(int64_t), 1, fptr);
        }
    }

    return 0;
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
    uint64_t pid = 0;
    uint64_t tid = 0;
    uint64_t count = 0;
    uint64_t ts = 0;
    uint64_t dur = 0;
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
                for (uint64_t i = 0; i < count / 2; i++) {
                    READ_DATA(&ts, uint64_t, fptr);
                    READ_DATA(&dur, uint64_t, fptr);
                    event = PyDict_New();
                    PyDict_SetItemString(event, "ph", unicode_X);
                    PyDict_SetItemString(event, "name", name);
                    PyDict_SetItemString(event, "cat", unicode_FEE);
                    PyDict_SetItemStringULL(event, "pid", pid);
                    PyDict_SetItemStringULL(event, "tid", tid);
                    PyDict_SetItemStringDouble(event, "ts", (double)ts / 1000);
                    PyDict_SetItemStringDouble(event, "dur", (double)dur / 1000);
                    PyList_Append(trace_events, event);
                    Py_DECREF(event);
                }
                Py_DECREF(name);
                break;
            case VC_HEADER_FILE_INFO:
                file_info = load_file_info(fptr);
                PyDict_SetItemString(parsed_events, "file_info", file_info);
                Py_DECREF(file_info);
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


int dump_file_info(PyObject* file_info, FILE* fptr){
    const char * buffer = NULL;
    uint64_t content_length = 0;
    uint64_t compression_length = 0;
    PyObject* json_ret = NULL;
    PyObject* zlib_ret = NULL;
    PyObject* bytes_data = NULL;
    PyObject* dumps_func = PyObject_GetAttrString(json_module, "dumps");
    PyObject* json_args = PyTuple_New(1);
    PyObject* compress_func = PyObject_GetAttrString(zlib_module, "compress");
    PyObject* zlib_args = PyTuple_New(1);

    if (!dumps_func) {
        perror("Failed to access json.dumps()");
        exit(-1);
    }

    if (!compress_func) {
        perror("Failed to access zlib.compress()");
        exit(-1);
    }
    
    // json dumps file_info
    PyTuple_SetItem(json_args, 0, file_info);
    Py_INCREF(file_info); 
    json_ret = PyObject_CallObject(dumps_func, json_args);

    // convert string to bytes
    bytes_data = PyObject_CallMethod(json_ret, "encode", NULL);
    content_length = PyBytes_Size(bytes_data);

    // compress bytes data
    PyTuple_SetItem(zlib_args, 0, bytes_data);
    zlib_ret = PyObject_CallObject(compress_func, zlib_args);
    compression_length = PyBytes_Size(zlib_ret);
    buffer = PyBytes_AsString(zlib_ret);

    // write data
    fputc(VC_HEADER_FILE_INFO, fptr);
    fwrite(&compression_length, sizeof(uint64_t), 1, fptr);
    fwrite(&content_length, sizeof(uint64_t), 1, fptr);
    fwrite(buffer, sizeof(char), compression_length, fptr);

    Py_DECREF(zlib_ret);
    Py_DECREF(bytes_data);
    Py_DECREF(dumps_func);
    Py_DECREF(json_args);
    Py_DECREF(compress_func);
    Py_DECREF(zlib_args);

    return 0;
}

PyObject*
load_file_info(FILE* fptr){
    unsigned char* compression_buffer = NULL;
    uint64_t compression_length = 0;
    uint64_t content_length = 0;
    PyObject* file_info = NULL;
    PyObject* zlib_ret = NULL;
    PyObject* bytes_data = NULL;
    PyObject* string_data = NULL;
    PyObject* loads_func = PyObject_GetAttrString(json_module, "loads");
    PyObject* json_args = PyTuple_New(1);
    PyObject* decompress_func = PyObject_GetAttrString(zlib_module, "decompress");
    PyObject* zlib_args = PyTuple_New(1);

    if (!loads_func) {
        perror("Failed to access json.loads()");
        exit(-1);
    }

    if (!decompress_func) {
        perror("Failed to access zlib.decompress()");
        exit(-1);
    }

    READ_DATA(&compression_length, uint64_t, fptr);
    READ_DATA(&content_length, uint64_t, fptr);

    // read compressed data
    compression_buffer = (unsigned char*)malloc(sizeof(char) * compression_length);
    if(compression_buffer == NULL){
        goto clean_exit;
    }
    fread(compression_buffer, sizeof(char), compression_length, fptr);
    bytes_data = PyBytes_FromStringAndSize((const char *)compression_buffer, compression_length);

    // decompress data
    PyTuple_SetItem(zlib_args, 0, bytes_data);
    zlib_ret = PyObject_CallObject(decompress_func, zlib_args);

    // convert depressed bytes to json
    string_data = PyObject_CallMethod(zlib_ret, "decode", NULL);
    PyTuple_SetItem(json_args, 0, string_data);
    file_info = PyObject_CallObject(loads_func, json_args);
    Py_DECREF(zlib_ret);
    free(compression_buffer);

clean_exit:
    Py_DECREF(loads_func);
    Py_DECREF(zlib_args);
    Py_DECREF(json_args);
    Py_DECREF(decompress_func);

    if (PyErr_Occurred()) {
        Py_DECREF(file_info);
        return NULL;
    }

    return file_info;
}
