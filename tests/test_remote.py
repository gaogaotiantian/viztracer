# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from .cmdline_tmpl import CmdlineTmpl
from viztracer import VizTracer
import os
import signal
import sys
import time
import unittest
import textwrap
import subprocess


class TestRemote(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "win32", "Does not support on Windows")
    def test_install(self):
        tracer = VizTracer(output_file="remote.json")
        tracer.install()
        os.kill(os.getpid(), signal.SIGUSR1)
        time.sleep(0.1)
        os.kill(os.getpid(), signal.SIGUSR2)
        self.assertTrue(os.path.exists("remote.json"))
        os.remove("remote.json")

    @unittest.skipIf(sys.platform == "win32", "Does not support on Windows")
    def test_attach(self):
        file_attach = textwrap.dedent("""
            from viztracer import VizTracer
            import time
            tracer = VizTracer(output_file='remote.json')
            tracer.install()
            while True:
                time.sleep(0.5)
        """)
        with open("attached_script.py", "w") as f:
            f.write(file_attach)

        if os.getenv("COVERAGE_RUN"):
            script_cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "attached_script.py"]
        else:
            script_cmd = ["python", "attached_script.py"]
        p_script = subprocess.Popen(script_cmd)

        # Give it some time for viztracer to install
        time.sleep(1)

        # Test with -t
        if os.getenv("COVERAGE_RUN"):
            attach_cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m",
                          "viztracer", "--attach", str(p_script.pid), "-t", "0.5"]
        else:
            attach_cmd = ["viztracer", "--attach", str(p_script.pid), "-t", "0.5"]
        p_attach = subprocess.Popen(attach_cmd)
        p_attach.wait()
        self.assertTrue(p_attach.returncode == 0)
        self.assertFileExists("remote.json", 20)

        os.remove("remote.json")

        if os.getenv("COVERAGE_RUN"):
            attach_cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m",
                          "viztracer", "attach", "--attach", str(p_script.pid)]
        else:
            attach_cmd = ["viztracer", "attach", "--attach", str(p_script.pid)]
        p_attach = subprocess.Popen(attach_cmd)
        time.sleep(1.5)
        p_attach.send_signal(signal.SIGINT)
        p_attach.wait()
        self.assertTrue(p_attach.returncode == 0)
        time.sleep(0.5)
        p_script.terminate()
        p_script.wait()
        self.assertFileExists("remote.json", 20)
        os.remove("attached_script.py")
        os.remove("remote.json")

        if os.getenv("COVERAGE_RUN"):
            attach_cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m",
                          "viztracer", "attach", "--attach", str(p_script.pid)]
        else:
            attach_cmd = ["viztracer", "attach", "--attach", str(p_script.pid)]
        p_attach = subprocess.Popen(attach_cmd)
        p_attach.wait()
        self.assertTrue(p_attach.returncode != 0)

    @unittest.skipIf(sys.platform != "win32", "Only test Windows")
    def test_windows(self):
        tracer = VizTracer(output_file="remote.json")
        with self.assertRaises(SystemExit):
            tracer.install()

        self.template(["viztracer", "--attach", "1234"], success=False)
