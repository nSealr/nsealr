#!/usr/bin/env python3
"""Use the existing pinned installer for one self-contained product checkout."""
import argparse,json,re
from pathlib import Path
from rehearse import canonical
from transforms import Changes

def apply(target,output):
 c=Changes(target);path='tools/baseline/bootstrap.py';s=(target/path).read_text();s=s.replace('software baseline','product bootstrap').replace("['git', 'fetch', '--depth=1', origin, commit]","['git', 'fetch', '--no-tags', origin, commit]")
 start=s.index('\ndef apply_lab_overlay(');end=s.index('\ndef main()',start);s=s[:start]+s[end:]
 s=s.replace("    parser.add_argument('--mirrors', type=Path, help='authorized sibling Git repositories; transport only, pins still verified')\n",'').replace("    parser.add_argument('--core-only', action='store_true', help='public core only; no private integration sources')\n",'').replace('    mirrors = args.mirrors.resolve() if args.mirrors else None\n','')
 s=s.replace("fetch(clones, 'firmware', str(SOURCE), candidate, root)","fetch(clones, 'nsealr', str(SOURCE), candidate, root)")
 start=s.index('    if not args.core_only:');end=s.index("    recorder = Recorder(root/'evidence/bootstrap', env)",start)
 s=s[:start]+"    write_json(root/'source-commits.json', inputs)\n"+s[end:]
 start=s.index("    for name in ('companion', 'website'):");end=s.index('    versions = {}',start)
 s=s[:start]+"    recorder.run('product-frozen-install', ['pnpm', 'install', '--frozen-lockfile'], root/'nsealr')\n    recorder.run('pi-setup', ['make', 'setup'], root/'nsealr/apps/pi')\n"+s[end:]
 s=s.replace("root/('firmware' if name == 'nsealr' else name)",'root/name').replace('cold_destination=True, core_only=args.core_only','cold_destination=True, scope="single public product checkout; hardware and optional physical resources are separate", os_hermetic=False').replace('{root}/firmware/tools/baseline/run.py','{root}/nsealr/tools/baseline/run.py')
 c.put(path,s.encode())
 path='tools/baseline/inputs.json';lock=json.loads((target/path).read_bytes());lock.pop('repositories');c.put(path,canonical(lock))
 path='tools/baseline/test_bootstrap.py';s=(target/path).read_text().replace('Recorder, apply_lab_overlay, apply_lab_overlays, download, environment, sha256','Recorder, download, environment, fetch, sha256');start=s.index('\nclass OverlayBoundaryTests');end=s.index('\nif __name__',start);s=s[:start]+'''
class ProductSourceTests(unittest.TestCase):
    def test_exact_selected_history_available_without_unselected_branch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';source.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(source),*args],stderr=subprocess.STDOUT).strip().decode()
            git('init','-q');(source/'public.txt').write_text('public source\\n');git('add','public.txt');git('-c','user.name=Test','-c','user.email=test@invalid.example','commit','-qm','public');selected=git('rev-parse','HEAD')
            git('checkout','-qb','unselected');(source/'excluded.txt').write_text('synthetic excluded source\\n');git('add','excluded.txt');git('-c','user.name=Test','-c','user.email=test@invalid.example','commit','-qm','unselected');excluded=git('rev-parse','HEAD')
            git('checkout','--detach',selected)
            rec=Recorder(root/'evidence',dict(os.environ));fetch(rec,'nsealr',str(source),selected,root)
            self.assertEqual(subprocess.check_output(['git','-C',str(root/'nsealr'),'rev-parse','HEAD'],text=True).strip(),selected)
            result=subprocess.run(['git','-C',str(root/'nsealr'),'cat-file','-e',excluded],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((root/'nsealr/excluded.txt').exists())

    def test_missing_selected_commit_preserves_fetch_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);source=root/'source';subprocess.run(['git','init','-q',str(source)],check=True)
            recorder=Recorder(root/'evidence',dict(os.environ))
            with self.assertRaisesRegex(RuntimeError,'fetch exited'):
                fetch(recorder,'nsealr',str(source),'0'*40,root)
            self.assertNotEqual(recorder.results[-1]['exit_code'],0)
            self.assertEqual(recorder.results[-1]['label'],'nsealr-fetch')

'''+s[end:];c.put(path,s.encode())
 # Historical overlay helpers have no active consumer after selected postimages
 # are integrated. Original source/patches remain in f2 history and A02 replay.
 for p in sorted((target/'tools/baseline/overlays').glob('*')):c.remove(p.relative_to(target).as_posix())
 path='tools/baseline/run.py';s=(target/path).read_text().replace("root/('firmware' if name == 'nsealr' else name)",'root/name')
 start=s.index('    if args.smoke:');end=s.index("    write_json(directory/'source-after.json'",start)
 s=s[:start]+'''    if args.smoke:
        recorder.run('product-smoke', ['make', 'test', 'cargo-test'], root/'nsealr', required=False)
    else:
        # One complete product entrypoint; -k preserves independent failures.
        recorder.run('product-ci', ['make', '-k', 'ci'], root/'nsealr', required=False)
'''+s[end:]
 s=s.replace('and card/USB','and USB').replace('outside R00 software baseline','outside software acceptance');c.put(path,s.encode())
 c.put('tools/baseline/README.md',b'''# Pinned product bootstrap

From a clean committed nsealr checkout on Linux x86_64/glibc:

```sh
python3 tools/baseline/bootstrap.py /absolute/absent/runtime
python3 /absolute/absent/runtime/nsealr/tools/baseline/run.py /absolute/absent/runtime
```

The existing installer pins downloadable Python, Node, pnpm, cargo tools and
wheels by version and SHA-256. Rustup installs the declared Rust version and
targets. It fetches only the exact current product commit, with its reachable
history for immutable contract/evidence checks. No sibling or private repository
is fetched. The caller's HOME remains unchanged; caches/configuration belong to
the new runtime. Destination reuse, archive hash failures, dirty source and
source drift are rejected. The full run records commands, outputs and failures.

The host OS, libc, compiler, Git, make, rsync and hosted runner are not hermetic.
Downloaded Rust toolchain manifests use the existing rustup trust boundary.
Actual installed browser, live relay, attached hardware and physical security
qualification require separate evidence. Historical R00/S01 multi-repository
inputs and overlay tools are preserved in original Git history and reviewed
restart evidence; they are no longer the active product bootstrap.
''')
 return c.apply(output,'Bootstrap only the exact consolidated public product with pinned tools and preserved source-history checks')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
