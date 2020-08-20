import setuptools
from distutils.core import Extension

with open("README.md") as f:
    long_description = f.read()

with open("./src/viztracer/__init__.py") as f:
    for line in f.readlines():
        if line.startswith("__version__"):
            # __version__ = "0.9"
            delim = '"' if '"' in line else "'"
            version = line.split(delim)[1]
            break
    else:
        print("Can't find version! Stop Here!")
        exit(1)

setuptools.setup(
    name="viztracer",
    version=version,
    author="Tian Gao",
    author_email="gaogaotiantian@hotmail.com",
    description="A debugging and profiling tool that can trace and visualize python code execution",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gaogaotiantian/viztracer",
    packages=setuptools.find_packages("src"),
    package_dir={"":"src"},
    package_data={
        "viztracer": [
            "html/*.js",
            "html/*.css",
            "html/*.html"
        ]
    },
    ext_modules=[
        Extension(
            "viztracer.snaptrace",
            sources = [
                "src/viztracer/modules/snaptrace.c",
            ]
        )
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires=">=3.6",
)
