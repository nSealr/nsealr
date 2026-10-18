#!/usr/bin/env python3
"""Check this product repository, independent of the checkout directory name."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REQUIRED_FILES=('README.md','LICENSE','Makefile','.pre-commit-config.yaml',
 'docs/architecture.md','docs/testing.md','docs/roadmap.md','docs/audit-checklist.md',
 '.github/workflows/ci.yml','plan/work-items.json','plan/evidence-index.json',
 'protocols/contracts/v1/manifest.json','apps/desktop-simulator/Cargo.lock',
 'apps/desktop-simulator/rust-toolchain.toml','pnpm-lock.yaml','packages/sdk/package.json')
REQUIRED_DIRS=('crates','apps/bridge','apps/pi','ci','boards','docs','scripts','tests/integration','tools/bridge')

def validate(root=ROOT):
 errors=[]
 for name in REQUIRED_FILES:
  path=root/name
  if not path.is_file() or path.is_symlink():errors.append('missing/nonregular required file: '+name)
  elif not path.read_text().strip():errors.append('empty required file: '+name)
 for name in REQUIRED_DIRS:
  path=root/name
  if not path.is_dir() or path.is_symlink():errors.append('missing/nonregular required directory: '+name)
 if (root/'LICENSE').is_file() and 'MIT License' not in (root/'LICENSE').read_text():errors.append('product license must retain MIT notice')
 if (root/'README.md').is_file() and '## License' not in (root/'README.md').read_text():errors.append('README.md must include a License section')
 return errors

if __name__=='__main__':
 errors=validate()
 for error in errors:print('ERROR:',error)
 if not errors:print('nSealr consolidated product structure passed')
 raise SystemExit(bool(errors))
