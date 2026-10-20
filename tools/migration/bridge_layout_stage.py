#!/usr/bin/env python3
"""Place retained Bridge consumers in one checkout and expose explicit SDK entries."""
import argparse,json,re,tempfile
from pathlib import Path
from admission import Recorder
from rehearse import canonical
from transforms import Changes


def apply(target,output,environment):
    output.mkdir(mode=0o700);rec=Recorder(output/'lock-generation');c=Changes(target)
    manifests=['package.json']+[p.relative_to(target).as_posix() for root in ['packages','apps/bridge'] for p in sorted((target/root).glob('*/package.json'))]
    for path in manifests:
        data=json.loads((target/path).read_bytes())
        for section in ['dependencies','devDependencies','peerDependencies','optionalDependencies']:
            data.get(section,{}).pop('@nsealr/smartcard',None)
        for field in ['repository','bugs','homepage']:
            if field in data:data[field]=json.loads(json.dumps(data[field]).replace('nSealr/companion','nSealr/nsealr'))
        if path=='package.json':
            data['name']='@nsealr/bridge-workspace'
            data['scripts']={k:v.replace('node scripts/','node tools/bridge/') for k,v in data['scripts'].items()}
            data['devDependencies']['@nsealr/fixtures']='workspace:*'
        elif path.startswith('packages/') and path!='packages/sdk/package.json':
            data['private']=True;data.pop('publishConfig',None)
        if path=='packages/sdk/package.json':data['exports']['./node']={'types':'./dist/node.d.ts','import':'./dist/node.js'}
        c.put(path,canonical(data))
    c.put('pnpm-workspace.yaml',b'packages:\n  - "apps/bridge/*"\n  - "packages/*"\n')
    config=json.loads((target/'tsconfig.json').read_bytes());config['exclude']=['apps/bridge/*/dist','packages/*/dist'];c.put('tsconfig.json',canonical(config))
    for path in sorted((target/'tools/bridge').glob('*.mjs')):
        text=path.read_text().replace('new URL("../package.json", import.meta.url)','new URL("../../package.json", import.meta.url)')
        text=text.replace('apps/browser-extension','apps/bridge/browser-extension').replace('"apps", "sdk-examples"','"apps", "bridge", "sdk-examples"')
        text=text.replace('"docs", "api.md"','"docs", "bridge", "api.md"').replace('"docs", "api-review.md"','"docs", "bridge", "api-review.md"')
        text=text.replace('node scripts/','node tools/bridge/')
        if path.name=='build_packages.mjs':text=text.replace('  "smartcard",\n','')
        if path.name=='package_set.mjs':
            start=text.index('  const env = { ...process.env };',text.index('export function packageManagerCommand'))
            end=text.index('\n}',start)
            text=text[:start]+'''  const env = { ...process.env };
  const version = spawnSync("pnpm", ["--version"], { env, encoding: "utf8" });
  assert.equal(version.status, 0, "pinned pnpm must be available in the bootstrap PATH");
  assert.equal(version.stdout.trim(), packageManager.slice("pnpm@".length), "pnpm version must match packageManager exactly");
  return { command: "pnpm", prefixArgs: [], env };'''+text[end:]
        c.put(path.relative_to(target).as_posix(),text.encode())
    c.put('packages/fixtures/src/specs-root.ts',b'''import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

/** Resolve the one artifact independently of process CWD; no snapshot fallback. */
export function resolveSpecsRoot(preferredRoot?: string): string {
  const root = resolve(preferredRoot ?? process.env.NSEALR_CONTRACTS_ROOT ??
    fileURLToPath(new URL("../../../protocols/contracts/v1/", import.meta.url)));
  const manifest = resolve(root, "manifest.json");
  if (!existsSync(manifest) || !existsSync(resolve(root, "vectors")) || !existsSync(resolve(root, "examples"))) {
    throw new Error(`authoritative contract artifact is missing: ${root}`);
  }
  const identity = JSON.parse(readFileSync(manifest, "utf8"));
  if (identity.artifact_format !== 1 || identity.artifact_id !== "nsealr-contracts-v1") {
    throw new Error("unsupported contract artifact identity");
  }
  return root;
}
''')
    for path in ['packages/policy/src/policy.test.ts','packages/review/src/review.test.ts']:
        text=(target/path).read_text();start=text.index('function resolveSpecsRoot(');end=text.index('\nfunction loadJson',start)
        text='import { resolveSpecsRoot } from "@nsealr/fixtures/specs-root";\n'+text[:start]+text[end:]
        text=text.replace('existsSync, ','');c.put(path,text.encode())
    c.put('packages/sdk/src/node.ts',(target/'packages/sdk/src/index.ts').read_bytes().replace(b'import * as smartcard from "@nsealr/smartcard";\n',b'').replace(b'  review,\n  smartcard',b'  review'))
    c.put('packages/sdk/src/index.ts',b'// The root is platform-neutral; Node consumers explicitly use ./node.\nexport * from "./browser.js";\n')
    c.put('packages/dev-signer/src/index.ts',(target/'packages/dev-signer/src/index.ts').read_bytes().replace(b'export * from "./smartcard-simulator.js";\n',b''))
    path='apps/bridge/cli/src/index.ts';text=(target/path).read_text().replace('devSignRequest, SmartcardSimulator','devSignRequest').replace('import { SmartcardSigner } from "@nsealr/smartcard";\n','')
    start=text.index('  program\n    .command("smartcard-sim-sign")');end=text.index('  const serialFrame',start)
    text=text[:start]+text[end:];c.put(path,text.encode())
    path='apps/bridge/sdk-examples/src/index.ts';text=(target/path).read_text()
    text=re.sub(r'import \{\n  CommandApdu,.*?\} from "@nsealr/smartcard";\n','',text,flags=re.S)
    start=text.index('  const command = new CommandApdu');end=text.index('  let writtenLine',start);text=text[:start]+text[end:]
    text=text.replace('smartcardAndTransportExample','transportExample').replace('  assert.equal(typeof sdk.smartcard.CommandApdu, "function");\n','')
    start=text.index('function specsRootForExamples()');end=text.index('\nawait requestAndQrExample',start)
    text=text[:start]+'function specsRootForExamples(): string { return resolveSpecsRoot(); }\n'+text[end:]
    text=text.replace('const companionRoot = fileURLToPath(new URL("../../..", import.meta.url));\nconst siblingSpecsRoot = join(dirname(companionRoot), "specs");\n','')
    c.put(path,text.encode())
    path='apps/bridge/consumer-smoke/src/index.ts';text=(target/path).read_text().replace('"..", "..", "..")','"..", "..", "..", "..")');c.put(path,text.encode())
    path='packages/policy/src/policy.ts';text=(target/path).read_text().replace('repository?: "raspberry" | "firmware" | "smartcard" | "hardware"','repository?: "nsealr"')
    for key,old in [('raspberry_qr_vault','raspberry'),('esp32_qr_vault','firmware'),('esp32_usb_nip46','firmware'),('custom_hardware_wallet','hardware'),('smartcard','smartcard')]:text=text.replace('["'+key+'", "'+old+'"]','["'+key+'", "nsealr"]')
    c.put(path,text.encode())
    path='packages/fixtures/src/fixtures.ts';text=(target/path).read_text().replace('repository: "hardware"','repository: "nsealr"').replace('fixture.repository !== "hardware"','fixture.repository !== "nsealr"');c.put(path,text.encode())
    with tempfile.TemporaryDirectory(dir=output,prefix='lock-metadata-') as tmp:
        scratch=Path(tmp)
        for path in manifests+['pnpm-workspace.yaml','pnpm-lock.yaml']:
            dest=scratch/path;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(c.updates[path][0] if path in c.updates else (target/path).read_bytes())
        rec.run('resolve-moved-workspace-lock',['pnpm','install','--lockfile-only','--ignore-scripts'],scratch,env=environment)
        c.put('pnpm-lock.yaml',(scratch/'pnpm-lock.yaml').read_bytes())
    return c.apply(output/'transformation','Move Bridge consumers to integrated paths and retire active card package entrypoints')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--environment',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output,json.loads(a.environment.read_bytes())))
