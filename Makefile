SHELL=/bin/bash -e

help:
	@echo "- make coverage     Run test coverage"
	@echo "- make test         Run tests"
	@echo "- make lint         Run lint"
	@echo "- make black        Format code"
	@echo "- make clean        Clean"
	@echo "- make venv         Create virtual environment"
	@echo "- make tag          Create version tag"

coverage:
	@pytest --cov --cov-report=term-missing

test:
	@pytest

lint:
	@flake8 alkemy_workflow

black:
	@black alkemy_workflow setup.py aw.py tests

tag:
	@git tag "v$$(cat alkemy_workflow/VERSION)"

build: clean
	@python3 setup.py bdist_wheel
	@python3 setup.py sdist bdist_wheel

clean:
	-rm -rf build dist
	-rm -rf *.egg-info
	-rm -rf bin lib share pyvenv.cfg

venv:
	@python3 -m virtualenv .
	. bin/activate; pip install -Ur requirements.txt
	. bin/activate; pip install -Ur requirements-dev.txt

shell:
	@docker run -it --rm -v "$$(pwd):/app" -w /app python:3.8 bash
