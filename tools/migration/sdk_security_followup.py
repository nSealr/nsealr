#!/usr/bin/env python3
"""Check the SDK's explicit bundled-runtime dependencies without relaxing facade imports."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 path='tools/bridge/check_browser_extension_security.mjs';text=(a.target/path).read_text();text=text.replace('  for (const dependency of Object.keys(dependencies)) {','''  // The single packed SDK now owns previously indirect verification/NIP-44
  // dependencies. Its facade source still cannot import signing primitives;
  // bundle_sdk checks every emitted dependency and excludes test signing code.
  const bundledSdkDependencies = {
    "@noble/ciphers": "2.1.1", "@noble/curves": "2.2.0",
    "@noble/hashes": "2.2.0", "nostr-tools": "2.23.3"
  };
  const isSdk = relativePath(path) === "packages/sdk/package.json";
  if (isSdk) assert.deepEqual(manifest.dependencies, bundledSdkDependencies,
    "SDK bundled-runtime dependency graph must match its reviewed exact versions");
  for (const dependency of Object.keys(dependencies)) {
    if (isSdk && bundledSdkDependencies[dependency] === dependencies[dependency]) continue;''');c.put(path,text.encode());print(c.apply(a.output,'Bind SDK security audit to exact owned-runtime dependencies while retaining facade import restrictions'))
