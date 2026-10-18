#!/usr/bin/env python3
"""Wire complete product acceptance to the retained verify job and main push."""
import argparse,json
from pathlib import Path
from rehearse import canonical
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 for name in ['check_product_gates.py','test_product_gates.py']:c.put('scripts/'+name,(a.author_repo/'tools/migration/templates/scripts'/name).read_bytes())
 path='Makefile';s=(a.target/path).read_text();s=s.replace('ci: test lint audit docs rust-ci','''contract-ci:
	$(MAKE) -C protocols/contracts/v1 ci

bridge-ci:
	pnpm ci

pi-ci:
	$(MAKE) -C apps/pi ci

integration-tests:
	python3 -B -m unittest discover -s tests/integration -p 'test_*.py' -v

integration:
	python3 -B -m tests.integration.run

product-gates:
	python3 scripts/check_product_gates.py
	python3 -B -m unittest discover -s scripts -p 'test_product_gates.py' -v

.PHONY: contract-ci bridge-ci pi-ci integration-tests integration product-gates
ci: test lint audit docs rust-ci contract-ci bridge-ci pi-ci integration-tests product-gates integration''');c.put(path,s.encode())
 c.put('protocols/contracts/v1/Makefile',b'''.PHONY: test lint audit ci
test:
	python3 scripts/verify_specs.py
	python3 -B -m unittest discover -s tests -v
lint:
	python3 -m compileall -q scripts tests
audit:
	python3 scripts/verify_repo.py
ci: test lint audit
''')
 path='package.json';d=json.loads((a.target/path).read_bytes());d['scripts']['ci']+=' && pnpm product-boundaries:check && pnpm current-guides:check';c.put(path,canonical(d))
 c.put('.github/workflows/ci.yml',b'''name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  verify:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09 # v5.1.0
        with:
          fetch-depth: 0
          persist-credentials: false
      - uses: actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1 # v6.3.0
        with:
          python-version: "3.12.15"
          check-latest: false
      # The existing hash-pinned installer records actual toolchain and source
      # inputs. Hosted OS/runner and service availability are not hermetic.
      - name: Bootstrap exact public product and pinned tools
        run: python3 tools/baseline/bootstrap.py "${RUNNER_TEMP}/nsealr-product"
      - name: Complete product acceptance
        run: python3 "${RUNNER_TEMP}/nsealr-product/nsealr/tools/baseline/run.py" "${RUNNER_TEMP}/nsealr-product"
''')
 print(c.apply(a.output,'Require complete consolidated acceptance in the verify job and main push with pinned official actions'))
