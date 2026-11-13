import os
import platform
import sys

import setuptools
from setuptools.command.build_py import build_py as _build_py

from setup_helpers import get_linux_attach_binary

_LINUX_ATTACH_BINARIES = {
    "attach_process/attach_linux_amd64.so",
    "attach_process/attach_linux_x86.so",
}
_LINUX_ATTACH_BINARY_NAMES = {
    os.path.basename(binary) for binary in _LINUX_ATTACH_BINARIES
}
_NO_TARGET_PLATFORM = object()


class build_py(_build_py):
    """Copy only the Linux attach binary matching the wheel target."""

    def initialize_options(self) -> None:
        super().initialize_options()
        self._target_attach_binary = _NO_TARGET_PLATFORM

    def _set_target_attach_binary(self) -> None:
        bdist_wheel = self.distribution.get_command_obj("bdist_wheel", create=False)
        if bdist_wheel is None:
            self._target_attach_binary = _NO_TARGET_PLATFORM
        else:
            bdist_wheel.ensure_finalized()
            self._target_attach_binary = get_linux_attach_binary(bdist_wheel.plat_name)

    def run(self) -> None:
        self._set_target_attach_binary()
        self.__dict__.pop("data_files", None)
        super().run()

    def find_data_files(self, package: str, src_dir: str) -> list[str]:
        self._set_target_attach_binary()
        files = super().find_data_files(package, src_dir)
        is_viztracer_package = package == "viztracer" or package.startswith(
            "viztracer."
        )
        if (
            not is_viztracer_package
            or self._target_attach_binary is _NO_TARGET_PLATFORM
        ):
            return files

        files = [
            file
            for file in files
            if os.path.basename(file) not in _LINUX_ATTACH_BINARY_NAMES
        ]
        if package == "viztracer" and self._target_attach_binary:
            binary = os.path.join(src_dir, self._target_attach_binary)
            if os.path.isfile(binary):
                files.append(binary)
        return files


# Determine which attach binary to take into package
package_data = {
    "viztracer": [
        "html/*.js",
        "html/*.css",
        "html/*.html",
        "web_dist/*",
        "web_dist/*/*",
        "web_dist/*/*/*",
        "attach_process/__init__.py",
        "attach_process/add_code_to_python_process.py",
        "attach_process/LICENSE",
    ],
}

if sys.platform == "win32":
    package_data["viztracer"].extend(
        [
            "attach_process/attach_x86.dll",
            "attach_process/attach_x86_64.dll",
            "attach_process/inject_dll.exe",
            "attach_process/inject_dll_amd64.exe",
            "attach_process/run_code_on_dllmain_amd64.dll",
            "attach_process/run_code_on_dllmain_x86.dll",
        ]
    )
if sys.platform == "darwin":
    package_data["viztracer"].extend(
        [
            "attach_process/attach_x86_64.dylib",
        ]
    )
elif sys.platform in ("linux", "linux2"):
    if platform.machine() == "i686":
        package_data["viztracer"].extend(
            [
                "attach_process/attach_linux_x86.so",
            ]
        )
    elif platform.machine() == "x86_64":
        package_data["viztracer"].extend(
            [
                "attach_process/attach_linux_amd64.so",
            ]
        )

setuptools.setup(
    packages=setuptools.find_namespace_packages("src"),
    package_dir={"": "src"},
    package_data=package_data,
    cmdclass={"build_py": build_py},
    ext_modules=[
        setuptools.Extension(
            "viztracer.snaptrace",
            sources=[
                "src/viztracer/modules/util.c",
                "src/viztracer/modules/eventnode.c",
                "src/viztracer/modules/quicktime.c",
                "src/viztracer/modules/snaptrace.c",
                "src/viztracer/modules/snaptrace_member.c",
            ],
            extra_compile_args={"win32": []}.get(sys.platform, ["-Werror", "-std=c99"]),
            extra_link_args={"win32": []}.get(sys.platform, ["-lpthread"]),
        ),
    ],
)
