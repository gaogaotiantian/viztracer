import sys
import subprocess

# 使用当前Python环境的pip安装openai
subprocess.check_call([sys.executable, "-m", "pip", "install", "openai"])

print("openai模块安装完成，请重新运行你的代码")
    