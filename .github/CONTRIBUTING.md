
First of all, many thanks to everyone who wants to contribute to VizTracer!

## Before Writing Code

If you have any thoughts that involve more than a couple of lines of code, I highly recommend you to
submit an issue first talking about the stuff you want to implement. We should have a discussion about
whether we want to do it, before you put too much effort into it.

## Coding

### Implementation

VizTracer requires type annotation for functions. Please do a lint check described below before you
submit the code.

There's no exact coding standards VizTracer follows, just try to make the code readable.

### Tests

If you are implementing something new, you need to write tests for it. VizTracer is a 100% coverage
project. There might be lines that can't be covered, give yourself(and me) a good reason why, and
add ``pragma: no cover`` after the line to skip the line.

Every new line of your code should be covered by the existing tests or your own tests.

### Docs

If you implement a new feature, you also need to write docs for it for others to understand.
It should definitely lives in ``docs/``, and could possibly lives in ``README.md`` as well
if it's important.

If you don't know where the docs belong to, ask me in the issue/PR.

## Build and Test

### Build

To contribute, first fork this project under your account, then create a feature branch:

```
git clone https://github.com/<your_user_name>/viztracer.git
cd viztracer
git checkout -b <your_feature_branch>
```

``virtualenv``(or other package manager) is highly recommended for development.

```
python3 -m venv venv
source venv/bin/activate
# On Windows
# .\venv\Scripts\activate
```

Install the requirements for development

```
pip install -r requirements-dev.txt
```

To build the project on Linux/MacOS, you can simply do ``make``.

However, if you are on Windows or prefer more explicit build process, you can do the following:

```
# uninstall viztracer first
pip uninstall -y viztracer
# build and install
python setup.py build install
```

### Lint

Check lint with flake8 and mypy

```
# On Unix
make lint

# explicit or windows
flake8 src/ tests/ example/ --exclude "src/viztracer/attach_process/*" --count --ignore=W503 --max-line-length=127 --statistics
mypy src/ --exclude src/viztracer/attach_process/
```

### Test

VizTracer uses built-in library ``unittest`` for testing.

You can do ``make test`` on Linux/MacOS, or do ``python -m unittest``. To run a specific
test, refer to unittest [docs](https://docs.python.org/3/library/unittest.html)

There might be a few tests that are not 100% stable on github actions. They should be listed in issues.
You should, however, make sure local tests pass before doing a pull request.

## Pull Request

Do a pull request to the ``master`` branch of ``gaogaotiantian/viztracer``, and I will review the code
and give feedbacks as soon as possible.
