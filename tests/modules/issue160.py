import subprocess
import sys

subprocess.run([sys.executable, "-u", "-c", "lst=[]; lst.append(1)"])
