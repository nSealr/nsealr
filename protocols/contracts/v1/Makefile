.PHONY: test lint audit ci
test:
	python3 scripts/verify_specs.py
	python3 -B -m unittest discover -s tests -v
lint:
	@cache=$$(mktemp -d) || exit $$?; \
	trap 'rm -rf "$$cache"' EXIT; trap 'exit 1' HUP INT TERM; \
	PYTHONPYCACHEPREFIX="$$cache" python3 -m compileall -q scripts tests
audit:
	python3 scripts/verify_repo.py
ci: test lint audit
