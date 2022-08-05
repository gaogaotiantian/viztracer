# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


class VCompressor:
    def compress(self, filename) -> dict:
        ...

    def decompress(self, filename) -> dict:
        ...
