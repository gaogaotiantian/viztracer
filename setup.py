import setuptools

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name = "codesnap",
    version = "0.0.1",
    author = "Tian Gao",
    author_email = "gaogaotiantian@hotmail.com",
    description = "A profiling tool that can visualize python code running",
    long_description = long_description,
    long_description_content_type = "text/markdown",
    url = "https://github.com/gaogaotiantian/codesnap",
    packages = setuptools.find_packages(),
    classifiers = [
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires = ">=3.5",
)