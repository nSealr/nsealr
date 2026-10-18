#!/usr/bin/env python3
"""Install the admitted source and current-guide guardrails without private source."""
import argparse,json
from pathlib import Path
from rehearse import canonical
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 path='tools/bridge/check_public_imports.mjs';s=(a.target/path).read_text();s=s.replace('function checkSourceFile(ownerPackage, packageSourceRoot, sourcePath) {','function checkSourceFile(ownerPackage, packageSourceRoot, sourcePath) {\n  return checkSourceText(ownerPackage, packageSourceRoot, sourcePath, readFileSync(sourcePath, "utf-8"));\n}\n\nexport function checkSourceText(ownerPackage, packageSourceRoot, sourcePath, sourceText) {').replace('    readFileSync(sourcePath, "utf-8"),','    sourceText,');c.put(path,s.encode())
 for name in ['check_product_boundaries.mjs','test_product_boundaries.mjs','check_current_guides.mjs','test_current_guides.mjs']:c.put('tools/bridge/'+name,(a.author_repo/'tools/migration/templates/tools/bridge'/name).read_bytes())
 package=json.loads((a.target/'package.json').read_bytes());package['scripts']['product-boundaries:check']='node tools/bridge/check_product_boundaries.mjs && node tools/bridge/test_product_boundaries.mjs';package['scripts']['current-guides:check']='node --import tsx/esm tools/bridge/check_current_guides.mjs && node --import tsx/esm tools/bridge/test_current_guides.mjs';c.put('package.json',canonical(package));print(c.apply(a.output,'Preserve admitted production source privacy ownership capability and current CLI guide guardrails'))
