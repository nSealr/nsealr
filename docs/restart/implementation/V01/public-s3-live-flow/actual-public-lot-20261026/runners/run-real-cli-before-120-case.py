#!/usr/bin/env python3
"""Root operational capture of an unmodified real CLI invocation; no signer emulator."""
import sys,os,pathlib,json,time,datetime,subprocess,selectors,hashlib
label=sys.argv[1]
if label not in ("setup-cancel","setup-cancel-user-socket","physical-reject","physical-approve"): raise SystemExit("unknown case")
r=pathlib.Path("/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25")
lab=r/"intake/v01-live-physical-20261026"; w=r/"client-account-binding"
case=lab/label; case.mkdir(mode=0o700)
env=os.environ.copy(); env["PATH"]="/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/node/bin:/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final/.tools/bin:/usr/bin:/bin"
argv=["pnpm","nsealr","local","dispatch-public-s3","--grant-store",str(lab/"grants.json"),"--account-store",str(lab/"accounts.json"),"--route-driver-store",str(lab/"drivers.json"),"--storage-approval",str(lab/"storage-approval.json"),"--expected-public-key","f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9","--out",str(case/"result.json")]
now=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
record={"label":label,"scope":"actual CLI/LocalServiceClient/child-service/Unix/SSH/MacUSB/S3 publicfixture; no test responder","argv":argv,"cwd":str(w),"PATH":env["PATH"],"started_utc":now(),"head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=w,text=True).strip(),"controls":[]}
(case/"launch.json").write_text(json.dumps(record,indent=2)+"\n")
p=subprocess.Popen(argv,cwd=w,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
record["launcher_pid"]=p.pid
selector=selectors.DefaultSelector(); selector.register(p.stdout,selectors.EVENT_READ,"stdout"); selector.register(p.stderr,selectors.EVENT_READ,"stderr"); selector.register(sys.stdin,selectors.EVENT_READ,"control")
logs={k:(case/("cli."+k)).open("xb") for k in ("stdout","stderr")}
started=time.monotonic(); streams=2
print(json.dumps({"cli_capture_started":label,"pid":p.pid,"controls":"enter sends newline; eof closes CLI setup stdin; capture has 240s outer limit"}),flush=True)
try:
 while streams or p.poll() is None:
  if time.monotonic()-started>240: raise TimeoutError("root capture outer ceiling; no product deadline extended")
  for key,_ in selector.select(.2):
   if key.data=="control":
    line=sys.stdin.readline()
    if not line: selector.unregister(sys.stdin); continue
    command=line.strip()
    if command not in ("enter","eof"): print("Unknown control; no action",flush=True); continue
    record["controls"].append({"utc":now(),"control":command})
    if command=="enter":
     p.stdin.write(b"\n"); p.stdin.flush()
    elif not p.stdin.closed: p.stdin.close()
    (case/"launch.json").write_text(json.dumps(record,indent=2)+"\n")
   else:
    data=os.read(key.fd,4096)
    if not data: selector.unregister(key.fileobj); streams-=1; continue
    logs[key.data].write(data); logs[key.data].flush()
    print(key.data+": "+data.decode("utf-8","replace"),end="",flush=True)
 record["exit"]=p.wait(); record["ended_utc"]=now(); record["elapsed_seconds"]=time.monotonic()-started
 record["result_exists"]=(case/"result.json").exists()
finally:
 for f in logs.values(): f.close()
 if p.poll() is None:
  p.terminate()
  try: p.wait(timeout=4)
  except subprocess.TimeoutExpired: p.kill();p.wait()
 record["observed_exit"]=p.returncode
 record["captures"]={n:{"bytes":(case/n).stat().st_size,"sha256":hashlib.sha256((case/n).read_bytes()).hexdigest()} for n in ("cli.stdout","cli.stderr")}
 (case/"launch.json").write_text(json.dumps(record,indent=2)+"\n")
 print("\nROOT_CAPTURE_RESULT "+json.dumps(record),flush=True)
