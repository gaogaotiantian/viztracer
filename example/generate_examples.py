import os
import subprocess


def generate_by_script(script):
    file_path = os.path.join(os.path.dirname(__file__), "src", script)
    subprocess.run(["python", file_path])


def generate_by_vt(script, options):
    file_path = os.path.join(os.path.dirname(__file__), "src", script)
    output_file = os.path.join(os.path.dirname(__file__), "json", script.replace("py", "json"))
    subprocess.run(["viztracer"] + options + ["-o", output_file, "--file_info", file_path])


if __name__ == "__main__":
    vt_options = {
        "mcts_game": ["--log_gc"],
        "logging_integration": ["--include_files", os.path.dirname(__file__)],
        "multi_process_pool": ["--log_multiprocess"],
        "async_simple": ["--log_async"],
    }
    for script in os.listdir(os.path.join(os.path.dirname(__file__), "src")):
        if script.split(".")[0] in vt_options:
            options = vt_options[script.split(".")[0]]
            generate_by_vt(script, options)
        elif script.endswith(".py"):
            generate_by_script(script)
