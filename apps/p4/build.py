#!/usr/bin/env python3
"""Build this one P4 consumer with existing isolated tools and source pins."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, subprocess, sys, time
APP=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument("stage",choices=["rust","configure","app"])
parser.add_argument("--rust-target",choices=["riscv32imafc-unknown-none-elf","x86_64-unknown-linux-gnu"],default="riscv32imafc-unknown-none-elf")
parser.add_argument("--probe-mode",choices=["normal","busy-cpu","blocking-wait"],default="normal")
args=parser.parse_args();probe_mode={"normal":0,"busy-cpu":1,"blocking-wait":2}[args.probe_mode]
PROBE=Path(os.environ.get("NSEALR_P4_TOOLS","/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25/p4-probe"))
PERIPHERAL=PROBE/"candidates/lvgl96-public-headers"
sys.path.insert(0,str(PROBE/"scripts"))
from active_environment import ACT
ENV=ACT.copy();ENV["P4_PERIPHERAL_ROOT"]=str(PERIPHERAL)
RUST=Path(os.environ.get("NSEALR_RUST_TOOLS","/home/tux/nsealr/.restart-tools/goal/r00/tools/baseline/.work/final-replay/.tools"))
RUSTBIN=RUST/"rustup/toolchains/1.95.0-x86_64-unknown-linux-gnu/bin"
ENV["CARGO_HOME"]=str(RUST/"cargo");ENV["RUSTUP_HOME"]=str(RUST/"rustup")
ENV["PATH"]=str(RUSTBIN)+":"+ENV["PATH"]
ENV["RUSTFLAGS"]="-C force-frame-pointers=yes"
if args.stage=="rust":
 argv=[str(RUSTBIN/"cargo"),"build","--release","--offline","--target",args.rust_target]
 cwd=APP/"rust"
elif args.stage=="configure":
 baseline=PROBE/"sdkconfig.rev3_x-lvgl96"
 expected=json.loads((APP/"inputs.json").read_text())["sdkconfig_input_sha256"]
 if hashlib.sha256(baseline.read_bytes()).hexdigest()!=expected:raise RuntimeError("Changed admitted sdkconfig input")
 overrides={}
 for line in (APP/"sdkconfig.public").read_text().splitlines():
  if line.startswith("CONFIG_"):
   key,value=line.split("=",1);overrides[key]=value
 # Remove affected legacy aliases; IDF regenerates them from canonical options.
 legacy={"CONFIG_TASK_WDT_PANIC"}
 lines=[]
 for line in baseline.read_text().splitlines():
  key=line.removeprefix("# ").split("=",1)[0].split(" ",1)[0]
  if key in legacy:continue
  if key in overrides:
   value=overrides.pop(key)
   lines.append("# "+key+" is not set" if value=="n" else key+"="+value)
  else:lines.append(line)
 for key,value in overrides.items():lines.append("# "+key+" is not set" if value=="n" else key+"="+value)
 (APP/"sdkconfig").write_text("\n".join(lines)+"\n")
 if not (APP/"managed_components").exists():
  (APP/"managed_components").symlink_to(PERIPHERAL/"vendor/examples/esp-idf/09_video_lcd_display/managed_components",target_is_directory=True)
 argv=[str(PROBE/"tools/tools/cmake/4.0.3/bin/cmake"),"-S",str(APP),"-B",str(APP/"build"),"-G","Ninja","-DIDF_TARGET=esp32p4","-DSDKCONFIG="+str(APP/"sdkconfig"),"-DP4_PERIPHERAL_ROOT="+str(PERIPHERAL),"-DP4_WDT_PROBE_MODE="+str(probe_mode)]
 cwd=APP
else:
 cache=(APP/"build/CMakeCache.txt").read_text()
 if "P4_WDT_PROBE_MODE:STRING="+str(probe_mode)+"\n" not in cache:raise RuntimeError("Configure the requested probe mode before app build")
 argv=[str(PROBE/"tools/tools/ninja/1.12.1/ninja"),"-C",str(APP/"build"),"-j","8","all"]
 cwd=APP
stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
evidence=APP/"evidence"/(stamp+"-"+args.stage);evidence.mkdir(parents=True,exist_ok=False)
record={"argv":argv,"cwd":str(cwd),"stage":args.stage,"probe_mode":args.probe_mode,"start_utc":stamp,"controlled_environment":{k:ENV.get(k) for k in ["IDF_PATH","IDF_TOOLS_PATH","IDF_PYTHON_ENV_PATH","CARGO_HOME","RUSTUP_HOME","RUSTFLAGS","P4_PERIPHERAL_ROOT"]}}
(evidence/"command.json").write_text(json.dumps(record,indent=2)+"\n")
start=time.monotonic();print("START",args.stage,evidence,flush=True)
with (evidence/"stdout.log").open("w") as out,(evidence/"stderr.log").open("w") as err:
 result=subprocess.run(argv,cwd=cwd,env=ENV,stdout=out,stderr=err,timeout=900)
record.update(exit=result.returncode,elapsed_seconds=time.monotonic()-start)
for name in ["sdkconfig.public","sdkconfig","dependencies.lock","rust/Cargo.lock"]:
 if (APP/name).exists():record[name+"_sha256"]=hashlib.sha256((APP/name).read_bytes()).hexdigest()
for name in ["stdout.log","stderr.log"]:record[name+"_sha256"]=hashlib.sha256((evidence/name).read_bytes()).hexdigest()
(evidence/"result.json").write_text(json.dumps(record,indent=2)+"\n")
print("END",args.stage,"exit",result.returncode,"seconds",record["elapsed_seconds"],flush=True)
if result.returncode:
 print((evidence/"stdout.log").read_text(errors="replace")[-5000:])
 print((evidence/"stderr.log").read_text(errors="replace")[-4000:])
sys.exit(result.returncode)
