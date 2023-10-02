# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


import base64
import json
import os
import re
import signal
import subprocess
import sys
import textwrap
import time
import unittest

from viztracer import VizTracer
from viztracer.attach_process.add_code_to_python_process import run_python_code  # type: ignore
from viztracer.util import pid_exists

from .cmdline_tmpl import CmdlineTmpl
from .util import cmd_with_coverage


@unittest.skipIf(sys.platform == "darwin" and sys.version_info >= (3, 11), "Does not support 3.11+ on Mac")
class TestRemote(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "win32", "Does not support on Windows")
    def test_install(self):
        tracer = VizTracer(output_file="remote.json", verbose=0)
        tracer.install()
        os.kill(os.getpid(), signal.SIGUSR1)
        time.sleep(0.1)
        os.kill(os.getpid(), signal.SIGUSR2)
        self.assertFileExists("remote.json")
        os.remove("remote.json")

    @unittest.skipIf(sys.platform == "win32", "Does not support on Windows")
    def test_attach_installed(self):
        file_to_attach = textwrap.dedent("""
            from viztracer import VizTracer
            import time
            tracer = VizTracer(output_file='remote.json')
            tracer.install()
            print("Ready", flush=True)
            while True:
                time.sleep(0.5)
        """)
        attach_installed_cmd = cmd_with_coverage(["viztracer", "--attach_installed"])
        attach_cmd = cmd_with_coverage(["viztracer", "-o", "remote.json", "--attach"])

        output_file = "remote.json"

        self.attach_check(file_to_attach, attach_cmd, output_file)
        self.attach_check(file_to_attach, attach_installed_cmd, output_file, use_installed=True)

    @unittest.skipIf(sys.platform == "win32", "Does not support on Windows")
    def test_attach(self):
        file_to_attach = textwrap.dedent("""
            import time
            print("Ready", flush=True)
            while True:
                time.sleep(0.5)
        """)
        output_file = os.path.abspath(f"./remote_{int(time.time() * 1000)}.json")
        attach_cmd = cmd_with_coverage(["viztracer", "-o", output_file, "--attach"])

        self.attach_check(file_to_attach, attach_cmd, output_file)

        file_to_attach_tracing = textwrap.dedent("""
            import time
            import viztracer
            tracer = viztracer.VizTracer(tracer_entries=1000)
            tracer.start()
            print("Ready", flush=True)
            while True:
                time.sleep(0.5)
        """)

        self.attach_check(file_to_attach_tracing, attach_cmd, output_file, file_should_exist=False)

    def attach_check(self, file_to_attach, attach_cmd, output_file, file_should_exist=True, use_installed=False):
        with open("attached_script.py", "w") as f:
            f.write(file_to_attach)

        # Run the process to attach first
        script_cmd = cmd_with_coverage(["python", "attached_script.py"])
        p_script = subprocess.Popen(script_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            pid_to_attach = p_script.pid
            attach_cmd = attach_cmd + [str(pid_to_attach)]

            out = p_script.stdout.readline()
            self.assertIn("Ready", out.decode("utf-8"))

            wait_time = 2
            # Test attach feature
            attach_cmd_with_t = attach_cmd + ["-t", str(wait_time)]
            p_attach = subprocess.Popen(attach_cmd_with_t, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p_attach.wait()
            out, err = p_attach.stdout.read().decode("utf-8"), p_attach.stderr.read().decode("utf-8")
            p_attach.stdout.close()
            p_attach.stderr.close()
            self.assertEqual(p_attach.returncode, 0,
                             msg=f"attach failed\n{out}\n{err}\n")
            self.assertIn("success", out, msg=f"Attach success not in {out}")
            if file_should_exist:
                self.assertFileExists(output_file, 40, msg=f"{out}\n{err}\n")
                os.remove(output_file)
            else:
                self.assertFileNotExist(output_file)

            p_attach = subprocess.Popen(attach_cmd, stdout=subprocess.PIPE, bufsize=0)
            # Read the attach success line
            out = p_attach.stdout.readline()
            self.assertIn("success", out.decode("utf-8"))
            p_attach.send_signal(signal.SIGINT)
            p_attach.wait()
            p_attach.stdout.close()
            self.assertEqual(p_attach.returncode, 0)
            time.sleep(0.5)

            if file_should_exist:
                self.assertFileExists(output_file, 20)
                os.remove(output_file)
            else:
                self.assertFileNotExist(output_file)
        finally:
            p_script.terminate()
            p_script.wait()
            attached_out, attached_err = p_script.stdout.read().decode("utf-8"), p_script.stderr.read().decode("utf-8")
            p_script.stdout.close()
            p_script.stderr.close()
            os.remove("attached_script.py")
            if file_should_exist and not use_installed:
                self.assertIn("Detected attaching", attached_out, msg=f"out:\n{attached_out}\nerr:\n{attached_err}\n")
                self.assertIn("Saved report to", attached_out, msg=f"out:\n{attached_out}\nerr:\n{attached_err}\n")

        p_attach_invalid = subprocess.Popen(attach_cmd, stdout=subprocess.DEVNULL)
        p_attach_invalid.wait()
        self.assertTrue(p_attach_invalid.returncode != 0)

    @unittest.skipIf(sys.platform == "win32", "Does not support on Windows")
    def test_uninstall(self):
        file_to_attach = textwrap.dedent("""
            import time
            import viztracer
            tracer = viztracer.VizTracer()
            tracer.start()
            print("Ready", flush=True)
            while True:
                time.sleep(0.5)
        """)
        output_file = os.path.abspath(f"remote_{int(time.time() * 1000)}.json")
        uninstall_cmd = cmd_with_coverage(["viztracer", "-o", output_file, "--uninstall"])
        attach_cmd = cmd_with_coverage(["viztracer", "-o", output_file, "--attach"])

        with open("attached_script.py", "w") as f:
            f.write(file_to_attach)

        # Run the process to attach first
        script_cmd = cmd_with_coverage(["python", "attached_script.py"])
        p_script = subprocess.Popen(script_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            out = p_script.stdout.readline()
            self.assertIn("Ready", out.decode("utf-8"))
            pid_to_attach = p_script.pid
            uninstall_cmd = uninstall_cmd + [str(pid_to_attach)]
            attach_cmd = attach_cmd + [str(pid_to_attach)]

            # Give it some time for viztracer to install
            time.sleep(1)

            # Try to attach. This should fail as viztracer is already running
            p_attach = subprocess.Popen(attach_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out = p_attach.stdout.readline()
            self.assertIn("success", out.decode("utf-8"))
            p_attach.send_signal(signal.SIGINT)
            p_attach.wait()
            p_attach.stdout.close()
            self.assertTrue(p_attach.returncode == 0)
            time.sleep(0.5)
            self.assertFileNotExist(output_file)

            # Uninstall viztracer from the process
            subprocess.check_call(uninstall_cmd)

            # Try it again
            p_attach = subprocess.Popen(attach_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            out = p_attach.stdout.readline()
            self.assertIn("success", out.decode("utf-8"))
            p_attach.send_signal(signal.SIGINT)
            p_attach.wait()
            p_attach.stdout.close()
            self.assertTrue(p_attach.returncode == 0)
            time.sleep(0.5)
            self.assertFileExists(output_file)
            os.remove(output_file)
        finally:
            p_script.terminate()
            p_script.wait()
            p_script.stdout.close()
            os.remove("attached_script.py")

        p_attach_invalid = subprocess.Popen(attach_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p_attach_invalid.wait()
        self.assertTrue(p_attach_invalid.returncode != 0)

        p_attach_uninstall = subprocess.Popen(uninstall_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p_attach_uninstall.wait()
        self.assertTrue(p_attach_uninstall.returncode != 0)

    @unittest.skipIf(sys.platform != "win32", "Only test Windows")
    def test_windows(self):
        tracer = VizTracer(output_file="remote.json")
        with self.assertRaises(SystemExit):
            tracer.install()

        self.template(["viztracer", "--attach", "1234"], success=False)
        self.template(["viztracer", "--attach_installed", "1234"], success=False)
        self.template(["viztracer", "--uninstall", "1234"], success=False)


@unittest.skipIf(sys.platform == "darwin" and sys.version_info >= (3, 11), "Does not support 3.11+ on Mac")
class TestAttachSanity(CmdlineTmpl):
    @unittest.skipIf(sys.platform == "win32", "Can't run attach on Windows")
    def test_basic(self):
        file_to_attach = textwrap.dedent("""
            import time
            print("Ready", flush=True)
            while True:
                time.sleep(0.5)
        """)
        with open("attached_script.py", "w") as f:
            f.write(file_to_attach)

        # Run the process to attach first
        script_cmd = cmd_with_coverage(["python", "attached_script.py"])
        p_script = subprocess.Popen(script_cmd, stdout=subprocess.PIPE)
        try:
            out = p_script.stdout.readline()
            self.assertIn("Ready", out.decode("utf-8"))
            pid_to_attach = p_script.pid
            retcode, out, err = run_python_code(pid_to_attach, "print(\\\"finish\\\", flush=True);")
            self.assertEqual(retcode, 0, msg=f"out: {out}; err: {err}")
        finally:
            p_script.terminate()
            p_script.wait()
            self.assertIn("finish", p_script.stdout.read().decode("utf-8"))
            p_script.stdout.close()
            os.remove("attached_script.py")


@unittest.skipIf(sys.platform == "darwin" and sys.version_info >= (3, 11), "Does not support 3.11+ on Mac")
class TestAttachScript(CmdlineTmpl):
    def test_attach_script(self):
        # Isolate the attach stuff in a separate process
        kwargs = {"output_file": "attach_test.json"}
        kwargs_non_exist = {"output_file": "non_exist.json"}
        kwargs_b64 = base64.urlsafe_b64encode(json.dumps(kwargs).encode("ascii")).decode("ascii")
        kwargs_non_exist_b64 = base64.urlsafe_b64encode(json.dumps(kwargs_non_exist).encode("ascii")).decode("ascii")
        attach_script = textwrap.dedent(f"""
            import viztracer.attach
            print(viztracer.attach.attach_status.created_tracer, flush=True)
            viztracer.attach.start_attach(\"{kwargs_b64}\")
            print(viztracer.attach.attach_status.created_tracer, flush=True)
            viztracer.attach.start_attach(\"{kwargs_b64}\")
            a = []
            a.append(1)
            viztracer.attach.stop_attach()
            print(viztracer.attach.attach_status.created_tracer, flush=True)
            viztracer.attach.start_attach(\"{kwargs_non_exist_b64}\")
            viztracer.attach.uninstall_attach()
            print(viztracer.attach.attach_status.created_tracer, flush=True)
        """)

        self.template(["python", "cmdline_test.py"],
                      script=attach_script,
                      expected_output_file="attach_test.json",
                      expected_stdout=re.compile(r".*?False.*?True.*?False.*?False.*?", re.DOTALL),
                      expected_stderr=".*Can't attach.*")
        if os.path.exists("non_exist.json"):
            os.remove("non_exist.json")
            self.fail("uninstall failed to prevent tracer from saving data")


@unittest.skipUnless(sys.platform == "darwin" and sys.version_info >= (3, 11), "Does not support 3.11+ on Mac")
class TestMacWarning(CmdlineTmpl):
    def test_mac_warning(self):
        pid = 12345
        while pid_exists(pid):
            pid += 1
        self.template(["viztracer", "--attach", str(pid)], success=False, expected_stdout=".*Warning.*")
