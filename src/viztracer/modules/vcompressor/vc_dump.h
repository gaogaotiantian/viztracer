#ifndef __VC_DUMP_H__
#define __VC_DUMP_H__

#include <Python.h>

#define VC_HEADER_RESERVED 0x00
#define VC_HEADER_FEE 0x01
#define VC_HEADER_PROCESS_NAME 0x02
#define VC_HEADER_THREAD_NAME 0x03
#define VC_HEADER_COUNTER_EVENTS 0x04
#define VC_HEADER_OTHER_EVENTS 0x05
#define VC_HEADER_FILE_INFO 0x11
#define VC_HEADER_COUNTER_ARG_UNKNOWN 0x21
#define VC_HEADER_COUNTER_ARG_SAME 0x22
#define VC_HEADER_COUNTER_ARG_LONG 0x23
#define VC_HEADER_COUNTER_ARG_FLOAT 0x24
#define VC_HEADER_COUNTER_ARG_LONG_STRING 0x25

#define TS_6_BIT   0x00
#define TS_14_BIT  0x01
#define TS_30_BIT  0x02
#define TS_62_BIT  0x03

PyObject* decompress_bytes(PyObject* bytes_data);
PyObject* compress_bytes(PyObject* bytes_data);
PyObject* json_loads_from_bytes(PyObject* bytes_data);
PyObject* json_dumps_to_bytes(PyObject* json_data);
PyObject* json_loads_and_decompress_from_file(FILE* fptr);
int json_dumps_and_compress_to_file(PyObject* json_data, FILE* fptr);

int dump_metadata(FILE* fptr);

int dump_parsed_trace_events(PyObject* trace_events, FILE* fptr);

int dump_file_info(PyObject* file_info, FILE* fptr);

int diff_and_write_counter_args(PyObject* counter_args, FILE* fptr);

int write_fee_events(PyObject* fee_key, PyObject* fee_value, FILE* fptr);

PyObject* load_events_from_file(FILE* fptr);

PyObject* load_file_info(FILE* fptr);

PyObject* load_counter_event(FILE* fptr);

PyObject * load_fee_events(FILE* fptr);

#endif
