.PHONY: refresh build install build_dist json release lint test clean

refresh: clean build install lint

build:
	python -m build

install:
	pip install .

build_dist:
	make clean
	python -m build
	pip install dist/*.whl
	make test

json:
	python example/generate_examples.py

release:
	python -m twine upload dist/*

lint:
	flake8 src/ tests/ example/ --exclude "src/viztracer/attach_process/*" --count --ignore=W503 --max-line-length=127 --statistics
	mypy src/ --exclude 'src/viztracer/attach_process/.*'

test:
	python -m unittest

clean:
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf src/viztracer/__pycache__
	rm -rf build
	rm -rf dist
	rm -rf viztracer.egg-info
	rm -rf src/viztracer.egg-info
	pip uninstall -y viztracer
