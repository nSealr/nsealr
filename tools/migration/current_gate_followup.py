#!/usr/bin/env python3
"""Match declared refusal text and retain full hosted command output as well as logs."""
import argparse
from pathlib import Path
from transforms import Changes
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--target',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();c=Changes(a.target)
 path='packages/client/src/service.test.ts';s=(a.target/path).read_text().replace('external review acknowledgement is only supported for display-less sign_event dispatch','host review acknowledgements are unsupported for signer dispatch');c.put(path,s.encode())
 path='tools/baseline/bootstrap.py';s=(a.target/path).read_text().replace('            code = subprocess.run(argv, cwd=cwd, env=self.env, stdout=stream, stderr=subprocess.STDOUT).returncode','''            with subprocess.Popen(argv, cwd=cwd, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as process:
                for line in process.stdout:
                    stream.write(line)
                    print(line, end="", flush=True)
                code = process.wait()''');c.put(path,s.encode())
 print(c.apply(a.output,'Match declared unsupported-acknowledgement text and stream complete pinned acceptance logs'))
