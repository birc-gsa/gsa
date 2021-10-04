
init:
	pip3 install -r requirements.txt
	pip3 install --editable .

check:
	mypy --strict -p gsa

test: check
	python3 -m pytest --cov-report term-missing --cov=gsa tests

build:
	python3 -m build

install:
	python3 setup.py install


.PHONY: init check test build install
