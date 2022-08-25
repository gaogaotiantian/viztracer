# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


class VCompressor:
    def compress(self, raw_data: dict, filename: str) -> dict:
        ...

    def decompress(self, filename: str) -> dict:
        ...
