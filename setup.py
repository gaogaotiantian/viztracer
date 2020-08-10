import setuptools
from distutils.core import Extension

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="codesnap",
    version="0.0.5",
    author="Tian Gao",
    author_email="gaogaotiantian@hotmail.com",
    description="A profiling tool that can visualize python code in flame graph",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gaogaotiantian/codesnap",
    packages=setuptools.find_packages("src"),
    package_dir={"":"src"},
    package_data={
        "codesnap": [
            "html/*.js",
            "html/*.css",
            "html/*.html"
        ]
    },
    ext_modules=[
        Extension(
            "codesnap.snaptrace",
            sources = [
                "src/codesnap/modules/snaptrace.c",
            ]
        )
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires=">=3.5",
)
