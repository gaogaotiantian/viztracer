# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/codesnap/blob/master/NOTICE.txt

from .tracer import CodeSnapTracer


# This is the interface of the package. Almost all user should use this
# class for the functions
class CodeSnap(CodeSnapTracer):
    def __init__(self, tracer="python"):
        super().__init__(tracer=tracer)

    def run(self, command, output_file="./result.html"):
        self.start()
        exec(command)
        self.stop()
        self.save()

    def save(self, output_file="./result.html"):
        if not self.parsed:
            self.parse()
        with open(output_file, "w") as f:
            f.write(self.generate_report())
