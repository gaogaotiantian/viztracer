# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/gaogaotiantian/viztracer/blob/master/NOTICE.txt

import inspect
import os
import subprocess
import sys
from contextlib import contextmanager
from itertools import product
from unittest import SkipTest


class PackageConfig:
    def __init__(self, pkg_config):
        self.pkg_config = pkg_config

    def has(self, package):
        for pkg in self.pkg_config:
            if f"~{package}" in pkg:
                return False
            elif package in pkg:
                return True
        return False


def get_curr_packages():
    freeze_process = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                                    check=True, stdout=subprocess.PIPE)
    packages = freeze_process.stdout.decode("utf-8").strip().splitlines()
    return [pkg for pkg in packages if "viztracer" not in pkg]


@contextmanager
def package_keeper():
    orig_packages = get_curr_packages()
    try:
        yield orig_packages
    finally:
        curr_packages = get_curr_packages()
        for pkg in curr_packages:
            if pkg not in orig_packages:
                subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", pkg], stdout=subprocess.DEVNULL)
        subprocess.check_call([sys.executable, "-m", "pip", "install", *orig_packages], stdout=subprocess.DEVNULL)


def setup_env(pkg_matrix, orig_packages):
    def pkg_key(pkg):
        # Put the the config that already meets the requirement first
        for package in orig_packages:
            if pkg.startswith("~") and pkg[1:] not in package:
                return 0
            elif pkg in package:
                return 0
        return 1

    if isinstance(pkg_matrix[0], list):
        pkg_config_iter = product(*pkg_matrix)
    else:
        pkg_matrix.sort(key=pkg_key)
        pkg_config_iter = product(pkg_matrix)
    for pkg_config in pkg_config_iter:
        try:
            for pkg in pkg_config:
                if pkg.startswith("~"):
                    subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", pkg[1:]], stdout=subprocess.DEVNULL)
                else:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg], stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            continue
        yield PackageConfig(pkg_config)


def package_matrix(pkg_matrix):

    def inner_func(func):

        def wrapper(*args, **kwargs):
            if os.getenv("GITHUB_ACTIONS"):
                with package_keeper() as orig_packages:
                    for _ in setup_env(pkg_matrix, orig_packages):
                        try:
                            func(*args, **kwargs)
                        except SkipTest:
                            pass
            else:
                func(*args, **kwargs)
        return wrapper

    def inner_cls(cls):

        if os.getenv("GITHUB_ACTIONS"):
            def new_run(self, result=None):
                with package_keeper() as orig_packages:
                    for pkg_config in setup_env(pkg_matrix, orig_packages):
                        self.pkg_config = pkg_config
                        self._run(result)
                        self.pkg_config = None

            cls._run = cls.run
            cls.run = new_run
        else:
            cls.pkg_config = PackageConfig(get_curr_packages())
        return cls

    def inner(func_or_cls):
        if not pkg_matrix:
            return func_or_cls
        elif inspect.isfunction(func_or_cls):
            return inner_func(func_or_cls)
        elif inspect.isclass(func_or_cls):
            return inner_cls(func_or_cls)
        else:
            assert False

    return inner
