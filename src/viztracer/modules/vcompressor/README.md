# VizTracer log compressor/decompressor

## Format

### Data Type

#### header

A one-byte header indicating the following data type

0x00 - Reserved
0x01 - FEE
0x02 - Process name
0x03 - Thread name
0x04 - Instant event
0x11 - File info

#### str

A null-ended cstring encoded in utf8

#### pid/tid

uint64

#### ts

A variant length variable for the timestamp.

### Process/Thread name

header(header) - pid(pid) - tid(tid) - name(str)

### FEE

header(header) - pid(pid) - tid(tid) - name(str) - count(uint64) - [start(ts) - dur(ts)]*

### Instant event

header(header) - pid(pid) - tid(tid) - name(str) - scopes(str) - count(uint64) - [start(ts)-args(str)]*

### File info

header(header) - compressed size(uint64) - uncompressed size(uint64) - compressed content

