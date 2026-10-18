#!/usr/bin/env python3
"""Replace copied Rust expected data by deterministic test-only projections."""
import argparse,hashlib,json,re
from pathlib import Path
from rehearse import canonical,digest
from transforms import Changes

TOKENS=re.compile(r'//[^\n]*|/\*.*?\*/|(?P<raw>b?r(?P<hashes>\#*)".*?"(?P=hashes))|(?P<quoted>b?"(?:\\.|[^"\\])*")',re.S)

def function_span(text,name):
    start=re.search(r'(?m)^\s*(?:pub )?fn '+name+r'\(',text).start();brace=text.index('{',start);depth=0;pos=brace
    for token in TOKENS.finditer(text,brace):
        for i in range(pos,token.start()):
            if text[i]=='{':depth+=1
            elif text[i]=='}':
                depth-=1
                if depth==0:return start,i+1
        pos=token.end()
    for i in range(pos,len(text)):
        if text[i]=='{':depth+=1
        elif text[i]=='}':
            depth-=1
            if depth==0:return start,i+1
    raise ValueError('unclosed Rust function '+name)

def replace_functions(text,names,include):
    spans=[function_span(text,n) for n in names]
    first=min(s[0] for s in spans)
    for start,end in sorted(spans,reverse=True):text=text[:start]+ ('\n    include!(concat!(env!("OUT_DIR"), "/'+include+'"));\n' if start==first else '')+text[end:]
    return text


def literal(token):
    raw=token.group('raw');quoted=token.group('quoted')
    if raw:
        value=raw[raw.index('"')+1:raw.rindex('"')];return value,raw.startswith('b')
    if quoted:
        byte=quoted.startswith('b');value=quoted[1:] if byte else quoted
        value=re.sub(r'\\u\{([0-9a-fA-F]+)\}',lambda m:chr(int(m[1],16)),value)
        try:return json.loads(value),byte
        except ValueError:return None
    return None


def apply(target,author,output):
    c=Changes(target);artifact=target/'protocols/contracts/v1';values={}
    def collect(value,path,pointer):
        if isinstance(value,(dict,list)):
            compact=json.dumps(value,ensure_ascii=False,separators=(',',':'))
            values.setdefault(compact,(path,pointer,'compact-json'))
            for key,item in (value.items() if isinstance(value,dict) else enumerate(value)):collect(item,path,pointer+[key])
        elif isinstance(value,str):values.setdefault(value,(path,pointer,'string'))
    for path in sorted(artifact.rglob('*.json')):
        if path.parts[len(artifact.parts)] not in ['vectors','examples']:continue
        collect(json.loads(path.read_bytes()),path.relative_to(artifact).as_posix(),[])
    replacements=[];projections={}
    for path in sorted((target/'crates/nsealr-core').rglob('*.rs')):
        relative=path.relative_to(target).as_posix();text=path.read_text()
        if '/tests/' in relative or path.name=='test_fixtures.rs':offset=0
        elif '#[cfg(test)]' in text:offset=text.index('#[cfg(test)]')
        else:continue
        # Independent primitive known answers retain their own attribution.
        if path.name in ['hash.rs','seedqr.rs','nip19.rs'] or relative.endswith('bip39/mod.rs'):continue
        if path.name=='test_fixtures.rs':
            text=replace_functions(text,['basic_trusted_review_request','tagged_trusted_review_request','t_display_s3_review_limits'],'review-fixtures.rs')
            text=text.replace('copies the same fixture values as Rust literals, each with its READ-ONLY\n//! source file named, and reads them at test time only.','projects the authoritative artifact into build output for tests only; no\n//! implementation computes these expected answers.')
        if relative.endswith('review/qr.rs'):text=replace_functions(text,['review_detail_page_vectors'],'detail-fixtures.rs')
        if relative.endswith('policy/policy_change_review.rs'):text=replace_functions(text,['proposal_from_literals','esp32_usb_fixture','custom_hardware_wallet_fixture'],'policy-fixtures.rs')
        edits=[]
        for token in TOKENS.finditer(text,offset):
            decoded=literal(token)
            if not decoded:continue
            value,byte=decoded
            if value not in values or len(value)<16:continue
            source,pointer,encoding=values[value];key=canonical([source,pointer,encoding]);filename='field-'+digest(key)[:24]+'.txt'
            projections[filename]={'output':filename,'artifact_path':source,'pointer':pointer,'encoding':encoding}
            replacement=('include_bytes!' if byte else 'include_str!')+'(concat!(env!("OUT_DIR"), "/'+filename+'"))'
            edits.append((token.start(),token.end(),replacement));replacements.append({'path':relative,'original_literal_sha256':digest(token[0].encode()),'value_sha256':digest(value.encode()),'projection':filename})
        for start,end,replacement in reversed(edits):text=text[:start]+replacement+text[end:]
        c.put(relative,text.encode())
    c.put('ci/core-test-projections.json',canonical(list(projections.values())))
    c.put('ci/project_core_fixtures.py',(author/'tools/migration/templates/ci/project_core_fixtures.py').read_bytes())
    c.put('crates/nsealr-core/build.rs',b'''// Data extraction only. Generated files are included exclusively under cfg(test).
use std::{env, path::PathBuf, process::Command};
fn main() {
    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap()).join("../..");
    let script = root.join("ci/project_core_fixtures.py");
    println!("cargo:rerun-if-changed={}", script.display());
    println!("cargo:rerun-if-changed={}", root.join("ci/core-test-projections.json").display());
    println!("cargo:rerun-if-changed={}", root.join("protocols/contracts/v1").display());
    let status = Command::new("python3").arg(script).arg(env::var_os("OUT_DIR").unwrap())
        .status().expect("pinned Python is required for test-data projection");
    assert!(status.success(), "contract test-data projection failed");
}
''')
    result=c.apply(output,'Project Rust test data from the authoritative artifact without generating expected behavior')
    (output/'literal-correspondence.json').write_bytes(canonical(replacements))
    return result


if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--author-repo',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.author_repo,a.output))
