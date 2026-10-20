#!/usr/bin/env python3
"""Build a single independently consumable SDK with owned code and declarations."""
import argparse,json,tempfile
from pathlib import Path
from admission import Recorder
from rehearse import canonical
from transforms import Changes


def apply(target,author,output,environment):
 output.mkdir(mode=0o700);rec=Recorder(output/'lock-generation');c=Changes(target)
 sdk=json.loads((target/'packages/sdk/package.json').read_bytes());internal=sdk.pop('dependencies')
 sdk['dependencies']={'@noble/curves':'2.2.0','@noble/hashes':'2.2.0','nostr-tools':'2.23.3'};sdk['files']=['dist','README.md','LICENSE'];c.put('packages/sdk/package.json',canonical(sdk));c.put('packages/sdk/LICENSE',(target/'LICENSE').read_bytes())
 root=json.loads((target/'package.json').read_bytes());root['devDependencies'].update(internal);c.put('package.json',canonical(root))
 for name in ['bundle_sdk.mjs','pack_smoke.mjs']:c.put('tools/bridge/'+name,(author/'tools/migration/templates/tools/bridge'/name).read_bytes())
 path='tools/bridge/build_packages.mjs';text=(target/path).read_text().replace('console.log("nSealr package build artifacts generated");','await import("./bundle_sdk.mjs");\nconsole.log("nSealr package build artifacts generated");');c.put(path,text.encode())
 path='tools/bridge/package_set.mjs';text=(target/path).read_text().replace('  assert(!publicPackageSet.has("@nsealr/dev-signer"),','  assert.deepEqual(publicPackages, ["@nsealr/sdk"], "SDK is the sole public package");\n  assert(!publicPackageSet.has("@nsealr/dev-signer"),');c.put(path,text.encode())
 path='tools/bridge/check_public_imports.mjs';text=(target/path).read_text().replace('publicPackages, root','publicPackages, workspacePackages, root');text=text.replace('const publicPackageSet = new Set(publicPackages);','const runtimePackages = workspacePackages.map(({ manifest }) => manifest.name)\n  .filter((name) => !["@nsealr/dev-signer", "@nsealr/fixtures"].includes(name));\nconst publicPackageSet = new Set(runtimePackages);')
 text=text.replace('publicPackages.map((packageName)','runtimePackages.map((packageName)').replace('for (const packageName of publicPackages)','for (const packageName of runtimePackages)');c.put(path,text.encode())
 for name in ['release_plan.mjs','check_release_plan.mjs']:
  path='tools/bridge/'+name;text=(target/path).read_text().replace('make integration in ../lab','make integration').replace('make release-artifacts','pnpm release-artifacts').replace('["dist", "README.md"]','["dist", "README.md", "LICENSE"]').replace('only dist and README','dist, README and the MIT notice').replace('"scripts/release_plan.mjs"','"tools/bridge/release_plan.mjs"');c.put(path,text.encode())
 # Lock movement changes only workspace importers; retained external versions
 # and package integrity records must remain byte-for-byte unchanged.
 with tempfile.TemporaryDirectory(dir=output,prefix='lock-metadata-') as tmp:
  scratch=Path(tmp);paths=['package.json','pnpm-workspace.yaml','pnpm-lock.yaml']+[p.relative_to(target).as_posix() for root in ['packages','apps/bridge'] for p in (target/root).glob('*/package.json')]
  for path in paths:
   dest=scratch/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(c.updates[path][0] if path in c.updates else (target/path).read_bytes())
  rec.run('resolve-sdk-owner-lock',['pnpm','install','--lockfile-only','--ignore-scripts'],scratch,env=environment)
  lock=(scratch/'pnpm-lock.yaml').read_bytes();before=(target/'pnpm-lock.yaml').read_bytes()
  if lock.split(b'\npackages:\n',1)[1]!=before.split(b'\npackages:\n',1)[1]:raise ValueError('external dependency resolution changed; review required')
  c.put('pnpm-lock.yaml',lock)
 return c.apply(output/'transformation','Bundle the sole public SDK with owned runtime declarations and isolated packed consumer checks')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--environment',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.author_repo,a.output,json.loads(a.environment.read_bytes())))
