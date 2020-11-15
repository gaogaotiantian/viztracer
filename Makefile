refresh: clean build install lint

build:
	python setup.py build

install: 
	python setup.py install

build_dist:
	make clean
	python setup.py sdist bdist_wheel
	pip install dist/*.whl
	make test

json:
	python example/generate_examples.py

release:
	python -m twine upload dist/*

lint:
	flake8 src tests --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src tests --exclude tests/data/ --count --exit-zero --statistic --ignore=E501,E122,E126,E127,E128,W503

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
