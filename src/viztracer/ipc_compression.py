# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import zlib

_ZSTD_MAGIC = b"zstd"

try:
    # `compression.zstd` is available on Python 3.14+ when
    # compiled in to the build.
    from compression import zstd  # type: ignore

    def ipc_compress(data: bytes | bytearray) -> bytes:
        return _ZSTD_MAGIC + zstd.compress(data)

    def ipc_decompress(data: bytes | bytearray) -> bytes:
        if data.startswith(_ZSTD_MAGIC):
            return zstd.decompress(data[4:])
        # Fallback for data compressed by an older viztracer (zlib)
        return zlib.decompress(data)

except ImportError:

    def ipc_compress(data: bytes | bytearray) -> bytes:
        return zlib.compress(data, level=1)  # Cheap compression level

    def ipc_decompress(data: bytes | bytearray) -> bytes:
        return zlib.decompress(data)
