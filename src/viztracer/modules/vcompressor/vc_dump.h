#ifndef __VC_DUMP_H__
#define __VC_DUMP_H__

#include <Python.h>

#define VC_HEADER_RESERVED 0x00
#define VC_HEADER_FEE 0x01
#define VC_HEADER_PROCESS_NAME 0x02
#define VC_HEADER_THREAD_NAME 0x03
#define VC_HEADER_FILE_INFO 0x11
#define VC_HEADER_FILE_NAME 0x12
#define VC_HEADER_FUNCTION_NAME 0x13

int dump_metadata(FILE* fptr);

int dump_parsed_trace_events(PyObject* trace_events, FILE* fptr);

int dump_file_info(PyObject* file_info, FILE* fptr);

PyObject* load_events_from_file(FILE* fptr);

PyObject* load_file_info(FILE* fptr);

#endif
