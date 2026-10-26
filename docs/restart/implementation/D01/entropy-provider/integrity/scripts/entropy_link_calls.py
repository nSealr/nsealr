import pathlib,subprocess,re,json
P=pathlib.Path("/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25/s3-probe")
objdump=P/"native/tools/tools/xtensa-esp-elf/esp-13.2.0_20240530/xtensa-esp-elf/bin/xtensa-esp32s3-elf-objdump"
raw=subprocess.check_output([str(objdump),"-d","-C",str(P/"native/build/idf-public/nsealr_s3_native_public.elf")],text=True)
targets={x:[] for x in ["esp_random","bootloader_random_enable","bootloader_random_disable"]};current=None
for line in raw.splitlines():
 m=re.match(r"^[0-9a-f]+ <(.+)>:$",line)
 if m:current=m.group(1);continue
 for target in targets:
  if re.search(r"<(?:"+re.escape(target)+r")>",line):targets[target].append({"caller":current,"instruction":line.strip()})
assert targets["esp_random"] and all(x["caller"]=="word(void*, unsigned long*, unsigned int*)" for x in targets["esp_random"]),targets
print(json.dumps({"method":"Pinned objdump -d -C of final ELF, retain exact direct target references; indirect/ROM calls are not exhaustively proved absent", "targets":targets},indent=2))
