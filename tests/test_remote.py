# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt


from viztracer import VizTracer
import os
import signal
import sys
import time
import unittest
import textwrap
import subprocess

from .cmdline_tmpl import CmdlineTmpl
from .util import cmd_with_coverage


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
        attach_installed_cmd = cmd_with_coverage(["viztracer", "--attach_installed"])
        attach_cmd = cmd_with_coverage(["viztracer", "-o", "remote.json", "--attach"])

        output_file = "remote.json"

        self.attach_check(file_to_attach, attach_cmd, output_file)
        self.attach_check(file_to_attach, attach_installed_cmd, output_file)

    @unittest.skipIf(sys.platform == "win32", "Does not support on Windows")
    def test_attach(self):
        file_to_attach = textwrap.dedent("""
            import time
            while True:
                time.sleep(0.5)
        """)
        attach_cmd = cmd_with_coverage(["viztracer", "-o", "remote.json", "--attach"])

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
        script_cmd = cmd_with_coverage(["python", "attached_script.py"])
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
            out, err = p_attach.stdout.read(), p_attach.stderr.read()
            p_attach.stdout.close()
            p_attach.stderr.close()
            self.assertTrue(p_attach.returncode == 0,
                            msg=f"attach failed\n{out}\n{err}\n")
            if file_should_exist:
                self.assertFileExists(output_file, 20)
                os.remove(output_file)
            else:
                self.assertFileNotExist(output_file)

            p_attach = subprocess.Popen(attach_cmd)
            if sys.platform == "darwin":
                # loading lldb is super slow on MacOS
                time.sleep(5)
            else:
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
        finally:
            p_script.terminate()
            p_script.wait()
            os.remove("attached_script.py")

        p_attach_invalid = subprocess.Popen(attach_cmd)
        p_attach_invalid.wait()
        self.assertTrue(p_attach_invalid.returncode != 0)

    @unittest.skipIf(sys.platform == "win32", "Does not support on Windows")
    def test_uninstall(self):
        file_to_attach = textwrap.dedent("""
            import time
            import viztracer
            tracer = viztracer.VizTracer()
            tracer.start()
            while True:
                time.sleep(0.5)
        """)
        uninstall_cmd = cmd_with_coverage(["viztracer", "-o", "remote.json", "--uninstall"])
        attach_cmd = cmd_with_coverage(["viztracer", "-o", "remote.json", "--attach"])

        output_file = "remote.json"

        with open("attached_script.py", "w") as f:
            f.write(file_to_attach)

        # Run the process to attach first
        script_cmd = cmd_with_coverage(["python", "attached_script.py"])
        p_script = subprocess.Popen(script_cmd)
        try:
            pid_to_attach = p_script.pid
            uninstall_cmd = uninstall_cmd + [str(pid_to_attach)]
            attach_cmd = attach_cmd + [str(pid_to_attach)]

            # Give it some time for viztracer to install
            time.sleep(1)

            # Try to attach. This should fail as viztracer is already running
            p_attach = subprocess.Popen(attach_cmd)
            if sys.platform == "darwin":
                # loading lldb is super slow on MacOS
                time.sleep(5)
            else:
                time.sleep(1.5)
            p_attach.send_signal(signal.SIGINT)
            p_attach.wait()
            self.assertTrue(p_attach.returncode == 0)
            time.sleep(0.5)
            self.assertFileNotExist(output_file)

            # Uninstall viztracer from the process
            subprocess.check_call(uninstall_cmd)

            # Try it again
            p_attach = subprocess.Popen(attach_cmd)
            if sys.platform == "darwin":
                # loading lldb is super slow on MacOS
                time.sleep(5)
            else:
                time.sleep(1.5)
            p_attach.send_signal(signal.SIGINT)
            p_attach.wait()
            self.assertTrue(p_attach.returncode == 0)
            time.sleep(0.5)
            self.assertFileExists(output_file)
            os.remove(output_file)
        finally:
            p_script.terminate()
            p_script.wait()
            os.remove("attached_script.py")

        p_attach_invalid = subprocess.Popen(attach_cmd)
        p_attach_invalid.wait()
        self.assertTrue(p_attach_invalid.returncode != 0)

    @unittest.skipIf(sys.platform != "win32", "Only test Windows")
    def test_windows(self):
        tracer = VizTracer(output_file="remote.json")
        with self.assertRaises(SystemExit):
            tracer.install()

        self.template(["viztracer", "--attach", "1234"], success=False)
        self.template(["viztracer", "--attach_installed", "1234"], success=False)
