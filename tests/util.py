import os


def get_json_file_path(filename):
    return os.path.join(os.path.dirname(__file__), "data", filename)