build:
	python setup.py build

install: 
	python setup.py install

build_dist:
	python setup.py sdist bdist_wheel

release:
	python -m twine upload dist/*

lint:
	flake8 src --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 src --count --exit-zero --max-complexity=10 --max-line-length=127 --statistic

test:
	python -m unittest

clean:
	rm -rf __pycache__
	rm -rf tests/__pycache__
	rm -rf src/codesnap/__pycache__
	rm -rf build
	rm -rf dist
	rm -rf codesnap.egg-info 
	pip uninstall -y codesnap