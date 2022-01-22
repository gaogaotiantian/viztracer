# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import os
import sys
import subprocess

from .package_env import package_matrix
from .util import get_json_file_path, adapt_json_file, generate_json
from .base_tmpl import BaseTmpl


adapt_json_file("vdb_basic.json")
vdb_basic = get_json_file_path("vdb_basic.json")
adapt_json_file("fib.json")
vdb_fib = get_json_file_path("fib.json")
adapt_json_file("old.json")
vdb_old = get_json_file_path("old.json")
generate_json("vdb_multithread.py")
vdb_multithread = get_json_file_path("vdb_multithread.json")


class SimInterface:
    def __init__(self, json_path, vdb_cmd=["vdb", "--no_clear", "--extra_newline"], expect_fail=False):
        commands = vdb_cmd + [json_path]
        if os.getenv("COVERAGE_RUN"):
            commands = ["coverage", "run", "--source", "viztracer", "--parallel-mode",
                        "-m", "viztracer.simulator"] + commands[1:]
        self.sim_process = subprocess.Popen(commands,
                                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)
        if expect_fail:
            self.sim_process.wait(timeout=3)
            self.sim_process.stdout.close()
            self.sim_process.stdin.close()
            self.returncode = self.sim_process.returncode
            return
        self.sim_process.stdin.write('\n')
        self.sim_process.stdin.flush()

        while True:
            if self.sim_process.poll() is not None:
                raise Exception("vdb unexpected closed")
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
                if self.sim_process.poll() is not None:
                    raise Exception("vdb unexpected closed")
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


class TestSimulator(BaseTmpl):
    def get_func_stack(self, result):
        line = result.replace("\r\n", "").replace("\n", "").replace("> ", " ")
        return [s for s in line.split() if ':' not in s]

    def test_module_run(self):
        sim = SimInterface(vdb_fib)
        result = sim.command("s")
        self.assertGreater(len(result), 10)
        result = sim.command("s")
        self.assertGreater(len(result), 2)
        sim.close()

    def test_old(self):
        sim = SimInterface(vdb_old, expect_fail=True)
        self.assertNotEqual(sim.returncode, 0)

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
        result = sim.command("t -1")
        result = sim.command("t")
        self.assertAlmostEqual(float(result), 0.6, places=4)
        sim.command("t 40")
        result1 = sim.command("w")
        self.assertEqual(self.get_func_stack(result1), ['t', 'f', 'g', 'h'])
        sim.command("t 74.2")
        result1 = sim.command("w")
        self.assertEqual(self.get_func_stack(result1), ['t', 'f'])
        sim.command("s")
        sim.command("u")
        result = sim.command("t")
        self.assertAlmostEqual(float(result), 74.5, places=4)
        sim.command("s")
        result = sim.command("t")
        self.assertAlmostEqual(float(result), 105.9, places=4)
        result = sim.command("t 1 1")
        self.assertIn("argument", result)
        sim.close()

    @package_matrix(["~rich", "rich"])
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
        result = sim.command("tid 1000")
        self.assertTrue("def" not in result)
        result = sim.command("pid 1000")
        self.assertTrue("def" not in result)
        result = sim.command("tid 10.5")
        self.assertTrue("def" not in result)
        result = sim.command("pid hello")
        self.assertTrue("def" not in result)
        result = sim.command("tid 1000 3218")
        self.assertTrue("def" not in result)
        result = sim.command("pid 3218 1000")
        self.assertTrue("def" not in result)
        sim.close()

        sim = SimInterface(vdb_multithread)
        for _ in range(100):
            sim.command("n")
        result = sim.command("w")
        for _ in range(101):
            sim.command("nb")
        result = sim.command("w")
        result1 = sim.command("tid")
        self.assertEqual(len(result1.strip().split()), 6)
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

    @package_matrix(["~rich", "rich"])
    def test_up_down(self):
        sim = SimInterface(vdb_basic)
        result1 = sim.command("s")
        result3 = sim.command("s")
        result2 = sim.command("u")
        result4 = sim.command("d")
        self.assertEqual(result1, result2)
        self.assertEqual(result3, result4)
        # Make sure boundary won't break the code
        for _ in range(5):
            sim.command("u")
        for _ in range(5):
            sim.command("d")
        sim.close()

    def test_edge(self):
        # Behaviors on the beginning/end of the program
        sim = SimInterface(vdb_basic)
        result1 = sim.command("sb")
        self.assertTrue("def" not in result1)
        result1 = sim.command("nb")
        self.assertTrue("def" not in result1)
        result1 = sim.command("rb")
        self.assertTrue("def" not in result1)
        sim.command("n")
        sim.command("n")
        sim.command("n")
        result1 = sim.command("s")
        self.assertTrue("def" not in result1)
        result1 = sim.command("n")
        self.assertTrue("def" not in result1)
        result1 = sim.command("r")
        self.assertTrue("def" not in result1)
        sim.close()

    def test_clear(self):
        sim = SimInterface(vdb_basic, vdb_cmd=["vdb", "--extra_newline"])
        sim.command("s")
        sim.close()

    def test_close(self):
        if sys.platform in ["linux", "linux2", "darwin"]:
            if os.getenv("COVERAGE_RUN"):
                commands = f"coverage run --source viztracer --parallel-mode -m viztracer.simulator {vdb_basic} < /dev/null"
            else:
                commands = f"vdb {vdb_basic} < /dev/null"

            sim_process = subprocess.Popen([commands],
                                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, shell=True)
            sim_process.wait()
            self.assertEqual(sim_process.returncode, 0)
