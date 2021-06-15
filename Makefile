
init:
	pip3 install -r requirements.txt
	pip3 install --editable .

check:
	mypy --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs -p gsa

# mypy --disallow-untyped-calls --disallow-untyped-defs --disallow-incomplete-defs tests/*.py

#test: check
#	pytest --cov-report term-missing --cov=gsa tests

build:
	python3 -m build

install:
	python3 setup.py install


.PHONY: init check test build install
