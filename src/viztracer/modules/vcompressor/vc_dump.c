// Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
// For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

#include <Python.h>
#include "vcompressor.h"
#include "vc_dump.h"
#include "zlib.h"

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
            default:
                // printf("wrong header %d\n", header);
                // load file info after this
                fseek(fptr, -1, SEEK_CUR);
                goto clean_exit;
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
    PyObject* files = PyDict_GetItemString(file_info, "files");
    PyObject* funtions = PyDict_GetItemString(file_info, "functions");
    uint64_t file_count = PyDict_Size(files);
    uint64_t function_count = PyDict_Size(funtions);
    Py_ssize_t ppos = 0;
    PyObject* key   = NULL;
    PyObject* value = NULL;

    fputc(VC_HEADER_FILE_INFO, fptr);
    fwrite(&file_count, sizeof(uint64_t), 1, fptr);
    fwrite(&function_count, sizeof(uint64_t), 1, fptr);
    // dump files
    while (PyDict_Next(files, &ppos, &key, &value)) {
        const char * file_name = PyUnicode_AsUTF8(key);
        const char * file_content = PyUnicode_AsUTF8(PyList_GET_ITEM(value, 0));
        uint64_t line_count = PyLong_AsLong(PyList_GET_ITEM(value, 1));
        uint64_t content_length = strlen(file_content) + 1;
        // compress file data
        uint64_t compression_length = compressBound(content_length);
        unsigned char* buffer = (unsigned char*)malloc(sizeof(unsigned char) * compression_length);
        compress(buffer, &compression_length, (unsigned char*)file_content, content_length);
        // write data
        fputc(VC_HEADER_FILE_NAME, fptr);
        fwritestr(file_name, fptr);
        fwrite(&line_count, sizeof(uint64_t), 1, fptr);
        fwrite(&compression_length, sizeof(uint64_t), 1, fptr);
        fwrite(&content_length, sizeof(uint64_t), 1, fptr);
        fwrite(buffer, sizeof(char), compression_length, fptr);
        free(buffer);
    }

    // dump functions
    ppos = 0;
    while (PyDict_Next(funtions, &ppos, &key, &value)) {
        const char * func_name = PyUnicode_AsUTF8(key);
        fputc(VC_HEADER_FUNCTION_NAME, fptr);
        fwritestr(func_name, fptr);
        uint64_t lineno = PyLong_AsLong(PyList_GET_ITEM(value, 1));
        const char * file_name = PyUnicode_AsUTF8(PyList_GET_ITEM(value, 0));
        fwritestr(file_name, fptr);
        fwrite(&lineno, sizeof(uint64_t), 1, fptr);
    }

    return 0;
}


PyObject*
load_file_info(FILE* fptr){
    PyObject* file_info = PyDict_New();
    PyObject* files = PyDict_New();
    PyObject* functions = PyDict_New();
    PyObject* file_name = NULL;
    PyObject* file_content = NULL;
    PyObject* file_line_count = NULL;
    PyObject* file_info_list = NULL;
    PyObject* function_name = NULL;
    PyObject* function_file_name = NULL;
    PyObject* function_position = NULL;
    PyObject* function_info_list = NULL;

    char buffer[STRING_BUFFER_SIZE] = {0};

    uint8_t header = 0;
    uint64_t function_count = 0;
    uint64_t file_count = 0;
    uint64_t read_function_count = 0;
    uint64_t read_file_count = 0;
    uint64_t line_count = 0;
    uint64_t compression_length = 0;
    uint64_t content_length = 0;
    uint64_t position_line = 0;

    PyDict_SetItemString(file_info, "files", files);
    PyDict_SetItemString(file_info, "functions", functions);
    Py_DECREF(files);
    Py_DECREF(functions);

    while (fread(&header, sizeof(uint8_t), 1, fptr)){
        switch (header){
            case VC_HEADER_FILE_INFO:
                READ_DATA(&file_count, uint64_t, fptr);
                READ_DATA(&function_count, uint64_t, fptr);
                break;
            case VC_HEADER_FILE_NAME:
                freadstrn(buffer, STRING_BUFFER_SIZE - 1, fptr);
                file_name = PyUnicode_FromString(buffer);
                READ_DATA(&line_count, uint64_t, fptr);
                READ_DATA(&compression_length, uint64_t, fptr);
                READ_DATA(&content_length, uint64_t, fptr);
                // decompress file content
                unsigned char* compression_buffer = (unsigned char*)malloc(sizeof(unsigned char) * compression_length);
                unsigned char* content_buffer = (unsigned char*)malloc(sizeof(unsigned char) * content_length);
                fread(compression_buffer, sizeof(char), compression_length, fptr);
                uncompress(content_buffer, &content_length, compression_buffer, compression_length);
                file_content = PyUnicode_FromString((const char *)content_buffer);
                file_info_list = PyList_New(0);
                file_line_count = PyLong_FromLong(line_count);
                PyList_Append(file_info_list, file_content);
                PyList_Append(file_info_list, file_line_count);
                PyDict_SetItem(files, file_name, file_info_list);
                free(compression_buffer);
                free(content_buffer);
                Py_DECREF(file_name);
                Py_DECREF(file_content);
                Py_DECREF(file_info_list);
                Py_DECREF(file_line_count);
                read_file_count++;
                break;
            case VC_HEADER_FUNCTION_NAME:
                freadstrn(buffer, STRING_BUFFER_SIZE - 1, fptr);
                function_name = PyUnicode_FromString(buffer);
                freadstrn(buffer, STRING_BUFFER_SIZE - 1, fptr);
                function_file_name = PyUnicode_FromString(buffer);
                READ_DATA(&position_line, uint64_t, fptr);
                function_position = PyLong_FromLong(position_line);
                function_info_list = PyList_New(0);
                PyList_Append(function_info_list, function_file_name);
                PyList_Append(function_info_list, function_position);
                PyDict_SetItem(functions, function_name, function_info_list);
                Py_DECREF(function_name);
                Py_DECREF(function_file_name);
                Py_DECREF(function_position);
                Py_DECREF(function_info_list);
                read_function_count++;
                break;
            default:
                printf("wrong header %d\n", header);
                break;
        }
        if(file_count != 0 && file_count == read_file_count && function_count == read_function_count){
            break;
        }
    }
    clean_exit:
        if (PyErr_Occurred()) {
            Py_DECREF(file_info);
            return NULL;
        }
        return file_info;
}