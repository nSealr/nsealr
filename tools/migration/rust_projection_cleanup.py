#!/usr/bin/env python3
"""Remove stale copied-fixture comments and keep projected digest constants live."""
import argparse,re
from pathlib import Path
from transforms import Changes

def apply(target,output):
    c=Changes(target)
    path='ci/project_core_fixtures.py';text=(target/path).read_text().replace("quote(review['approval_digest'])+',&'+pages(review['pages'])", "name.upper()+'_REVIEW_SCREEN_APPROVAL_DIGEST,&'+pages(review['pages'])")
    c.put(path,text.encode())
    path='crates/nsealr-core/src/review/test_fixtures.rs';text=(target/path).read_text()
    start=text.index('/// The basic trusted-review request;');end=text.index('/// True if any frame body line',start)
    text=text[:start]+'// Basic/tagged pages, digests and limits are extracted from the single artifact.\ninclude!(concat!(env!("OUT_DIR"), "/review-fixtures.rs"));\n\n'+text[end:]
    c.put(path,text.encode())
    path='crates/nsealr-core/src/review/qr.rs';text=(target/path).read_text();start=text.index('    /// The four READ-ONLY specs/vectors/review-detail-pages');end=text.index('    include!',start)
    text=text[:start]+'    // Extract every authoritative detail-page fixture without computing expectations.\n'+text[end:];c.put(path,text.encode())
    return c.apply(output,'Remove stale copied-fixture comments and retain projected digest references')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(apply(a.target,a.output))
