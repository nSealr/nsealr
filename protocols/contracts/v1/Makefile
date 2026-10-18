.PHONY: test lint audit ci
test:
	python3 scripts/verify_specs.py
	python3 -B -m unittest discover -s tests -v
lint:
	python3 -m compileall -q scripts tests
audit:
	python3 scripts/verify_repo.py
ci: test lint audit
