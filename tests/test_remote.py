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
    def test_attach_installed(self):
        file_to_attach = textwrap.dedent("""
            from viztracer import VizTracer
            import time
            tracer = VizTracer(output_file='remote.json')
            tracer.install()
            while True:
                time.sleep(0.5)
        """)
        if os.getenv("COVERAGE_RUN"):
            attach_installed_cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m",
                                    "viztracer", "--attach_installed"]
            attach_cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m",
                          "viztracer", "-o", "remote.json", "--attach"]
        else:
            attach_installed_cmd = ["viztracer", "--attach_installed"]
            attach_cmd = ["viztracer", "-o", "remote.json", "--attach"]

        output_file = "remote.json"

        self.attach_check(file_to_attach, attach_cmd, output_file)
        self.attach_check(file_to_attach, attach_installed_cmd, output_file)

    def test_attach(self):
        file_to_attach = textwrap.dedent("""
            import time
            while True:
                time.sleep(0.5)
        """)
        if os.getenv("COVERAGE_RUN"):
            attach_cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "-m",
                          "viztracer", "-o", "remote.json", "--attach"]
        else:
            attach_cmd = ["viztracer", "-o", "remote.json", "--attach"]

        output_file = "remote.json"

        self.attach_check(file_to_attach, attach_cmd, output_file)

        file_to_attach_tracing = textwrap.dedent("""
            import time
            import viztracer
            tracer = viztracer.VizTracer(tracer_entries=1000)
            tracer.start()
            while True:
                time.sleep(0.5)
        """)

        self.attach_check(file_to_attach_tracing, attach_cmd, output_file, file_should_exist=False)

    def attach_check(self, file_to_attach, attach_cmd, output_file, file_should_exist=True):
        with open("attached_script.py", "w") as f:
            f.write(file_to_attach)

        # Run the process to attach first
        if os.getenv("COVERAGE_RUN"):
            script_cmd = ["coverage", "run", "--source", "viztracer", "--parallel-mode", "attached_script.py"]
        else:
            script_cmd = ["python", "attached_script.py"]
        p_script = subprocess.Popen(script_cmd)
        try:
            pid_to_attach = p_script.pid
            attach_cmd = attach_cmd + [str(pid_to_attach)]

            # Give it some time for viztracer to install
            time.sleep(1)

            # Test attach feature
            attach_cmd_with_t = attach_cmd + ["-t", "0.5"]
            p_attach = subprocess.Popen(attach_cmd_with_t, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_attach.wait()
            self.assertTrue(p_attach.returncode == 0, msg=f"attach failed\n{p_attach.stdout}\n{p_attach.stderr}\n")
            if file_should_exist:
                self.assertFileExists(output_file, 20)
                os.remove(output_file)
            else:
                self.assertFileNotExist(output_file)

            p_attach = subprocess.Popen(attach_cmd)
            time.sleep(1.5)
            p_attach.send_signal(signal.SIGINT)
            p_attach.wait()
            self.assertTrue(p_attach.returncode == 0)
            time.sleep(0.5)

            if file_should_exist:
                self.assertFileExists(output_file, 20)
                os.remove(output_file)
            else:
                self.assertFileNotExist(output_file)
            os.remove("attached_script.py")
        finally:
            p_script.terminate()
            p_script.wait()

        p_attach_invalid = subprocess.Popen(attach_cmd)
        p_attach_invalid.wait()
        self.assertTrue(p_attach_invalid.returncode != 0)

    @unittest.skipIf(sys.platform != "win32", "Only test Windows")
    def test_windows(self):
        tracer = VizTracer(output_file="remote.json")
        with self.assertRaises(SystemExit):
            tracer.install()

        self.template(["viztracer", "--attach", "1234"], success=False)
