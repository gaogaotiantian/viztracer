import platform
import sys

import setuptools

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
    package_data["viztracer"].extend([
        "attach_process/attach_x86.dll",
        "attach_process/attach_x86_64.dll",
        "attach_process/inject_dll.exe",
        "attach_process/inject_dll_amd64.exe",
        "attach_process/run_code_on_dllmain_amd64.dll",
        "attach_process/run_code_on_dllmain_x86.dll",
    ])
if sys.platform == "darwin":
    package_data["viztracer"].extend([
        "attach_process/attach_x86_64.dylib",
    ])
elif sys.platform in ("linux", "linux2"):
    if platform.machine() == "i686":
        package_data["viztracer"].extend([
            "attach_process/attach_linux_x86.so",
        ])
    elif platform.machine() == "x86_64":
        package_data["viztracer"].extend([
            "attach_process/attach_linux_amd64.so",
        ])

setuptools.setup(
    packages=setuptools.find_namespace_packages("src"),
    package_dir={"": "src"},
    package_data=package_data,
    ext_modules=[
        setuptools.Extension(
            "viztracer.snaptrace",
            sources=[
                "src/viztracer/modules/util.c",
                "src/viztracer/modules/eventnode.c",
                "src/viztracer/modules/snaptrace.c",
            ],
            extra_compile_args={"win32": []}.get(sys.platform, ["-Werror", "-std=c99"]),
            extra_link_args={"win32": []}.get(sys.platform, ["-lpthread"]),
        ),
        setuptools.Extension(
            "viztracer.vcompressor",
            sources=[
                "src/viztracer/modules/vcompressor/vcompressor.c",
                "src/viztracer/modules/vcompressor/vc_dump.c",
            ],
            extra_compile_args={"win32": []}.get(sys.platform, ["-Werror", "-std=c99"]),
        ),
    ],
)
