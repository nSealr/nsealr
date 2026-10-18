.PHONY: setup test lint audit docs ci

PYTHON := .venv/bin/python
PIP := $(PYTHON) -m pip

setup:
	python3 -m venv .venv
	$(PIP) install --disable-pip-version-check -r requirements.txt
	PIP_IN_TREE_BUILD="$$( $(PIP) install --use-feature=in-tree-build --help >/dev/null 2>&1 && printf '%s' '--use-feature=in-tree-build' || true )"; \
	$(PIP) install --disable-pip-version-check $$PIP_IN_TREE_BUILD .

test:
	$(PYTHON) scripts/verify_repo.py
	$(PYTHON) -m unittest discover -s tests

lint:
	$(PYTHON) scripts/verify_repo.py
	$(PYTHON) -m compileall -q app tests

audit:
	$(PYTHON) scripts/verify_repo.py
	$(PIP) check

docs:
	$(PYTHON) scripts/verify_repo.py

ci: setup test lint audit docs
