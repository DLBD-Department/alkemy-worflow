SHELL=/bin/bash -e

help:
	@echo - make coverage
	@echo - make test
	@echo - make lint
	@echo - make clean
	@echo - make venc

coverage:
	coverage run --source=alkemy_workflow -m pytest && python3 -m coverage report -m

test:
	pytest

lint:
	flake8 alkemy_workflow

black:
	black alkemy_workflow setup.py aw.py tests

clean:
	-rm -rf build dist
	-rm -rf *.egg-info
	-rm -rf bin lib share pyvenv.cfg

venv:
	python3 -m virtualenv .
	. bin/activate; pip install -Ur requirements.txt
	. bin/activate; pip install -Ur requirements-dev.txt
