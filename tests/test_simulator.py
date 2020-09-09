# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.tx

import os
import unittest
import subprocess
from .util import get_json_file_path, adapt_json_file


adapt_json_file("vdb_basic.json")
vdb_basic = get_json_file_path("vdb_basic.json")


class SimInterface:
    def __init__(self, json_path):
        commands = ["vdb", "--no_clear", "--extra_newline", json_path]
        if os.getenv("COVERAGE_RUN"):
            commands = ["coverage", "run", "--parallel-mode", "--pylib", "-m", "viztracer.simulator"] + commands[1:]
        self.sim_process = subprocess.Popen(commands,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        import time
        self.sim_process.stdin.write('\n')
        self.sim_process.stdin.flush()
        while True:
            line = self.sim_process.stdout.readline()
            if line.startswith(">>>"):
                break

    def command(self, cmd, block=True):
        self.sim_process.stdin.write(cmd + '\n')
        self.sim_process.stdin.flush()
        self.sim_process.stdin.write('\n')
        self.sim_process.stdin.flush()
        if block:
            ret = ""
            data = False
            while True:
                line = self.sim_process.stdout.readline()
                if line.startswith(">>>"):
                    if data:
                        break
                else:
                    data = True
                    ret += line
            return ret

    def close(self):
        if self.sim_process.poll() is None:
            try:
                self.command("q", False)
                self.sim_process.wait(timeout=3)
                self.sim_process.stdout.close()
                self.sim_process.stdin.close()
                if self.sim_process.returncode != 0:
                    raise Exception("error code {}".format(self.sim_process.returncode))
            except subprocess.TimeoutExpired:
                self.sim_process.terminate()

    def __del__(self):
        self.close()


class TestSimulator(unittest.TestCase):
    def get_func_stack(self, result):
        return [s.split('.')[-1] for s in result.split() if '.' in s]

    def test_step(self):
        sim = SimInterface(vdb_basic)
        result1 = sim.command("s")
        sim.command("sb")
        result2 = sim.command("s")
        self.assertEqual(result1, result2)
        sim.close()

    def test_next(self):
        sim = SimInterface(vdb_basic)
        result1 = sim.command("n")
        sim.command("nb")
        result2 = sim.command("n")
        self.assertEqual(result1, result2)
        sim.close()

    def test_return(self):
        sim = SimInterface(vdb_basic)
        result1 = sim.command("n")
        sim.command("sb")
        result2 = sim.command("r")
        self.assertEqual(result1, result2)
        sim.command("s")
        result3 = sim.command("rb")
        self.assertEqual(result2, result3)
        sim.close()

    def test_timestamp(self):
        sim = SimInterface(vdb_basic)
        result = sim.command("t")
        self.assertAlmostEqual(float(result), 0.6, places=4)
        sim.command("t 40")
        result1 = sim.command("w")
        self.assertEqual(self.get_func_stack(result1), ['t', 'f', 'g', 'h'])
        sim.close()
    
    def test_tid_pid(self):
        sim = SimInterface(vdb_basic)
        result = sim.command("tid")
        self.assertEqual(result.strip(), "> 3218")
        sim.command("tid 3218")
        result = sim.command("tid")
        self.assertEqual(result.strip(), "> 3218")
        result = sim.command("pid")
        self.assertEqual(result.strip(), "> 3218")
        sim.command("pid 3218")
        result = sim.command("pid")
        self.assertEqual(result.strip(), "> 3218")
        sim.close()

    def test_counter(self):
        sim = SimInterface(vdb_basic)
        result = sim.command("counter")
        self.assertEqual(result.strip(), "{}")
        sim.command("t 75")
        result = sim.command("counter")
        self.assertEqual(result.strip(), "{'a': 7}")
        sim.close()

    def test_object(self):
        sim = SimInterface(vdb_basic)
        sim.command("t 75")
        result = sim.command("object")
        self.assertEqual(result.split('\n')[1].strip(), "{'s': '5', 'b': 3}")
        sim.close()

    def test_args(self):
        # TODO: test real args
        sim = SimInterface(vdb_basic)
        sim.command("a")
        sim.command("arg")
        sim.command("args")
        sim.close()