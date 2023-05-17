# VizTracer log compressor/decompressor

## Format

### Data Type

#### header

A one-byte header indicating the following data type

0x00 - Reserved
0x01 - FEE
0x02 - Process name
0x03 - Thread name
0x04 - count event
0x05 - non-frequent event
0x11 - File info
0x21 - counter arg unknown
0x22 - counter arg is the same with last timestamp
0x23 - counter arg is long type and not overflowed
0x24 - counter arg is float type
0x25 - counter arg is long type and overflowed


#### str

A null-ended cstring encoded in utf8

#### pid/tid

uint64

#### ts

A variant length variable for the timestamp.

### Process/Thread name

header(header) - pid(pid) - tid(tid) - name(str)

### FEE

header(header) - pid(pid) - tid(tid) - name(str) - count(uint64) - args offset - [start(ts) - dur(ts)]* - args list (if args offset is not 0)

### File info

header(header) - compressed size(uint64) - uncompressed size(uint64) - compressed content

### Count Event

header(header) - pid(pid) - tid(tid) - name(str) - key count - [ keys ]* - timestamp count -[ts - variables]*

#### variables
[header - value]*
the order of variables is corresponding to the order of keys.
if header means value didn't change compared to last timestamp, value will be null.
if header means long or float, the value is int64_t or double type
if header means a long and the value overflows, the value is string type

### Non-frequent Events

We just directly use json dumps and compress the data because they will be only a very small part of the trace. Except FEE, counter event, thread name, process name, the left events are treated as non-frequent events
