import pathlib,subprocess
from elftools.elf.elffile import ELFFile
P=pathlib.Path("/home/tux/nsealr/.restart-tools/mac-resume-2026-10-25/s3-probe")
elf=P/"native/build/idf-public/nsealr_s3_native_public.elf"
objdump=P/"native/tools/tools/xtensa-esp-elf/esp-13.2.0_20240530/xtensa-esp-elf/bin/xtensa-esp32s3-elf-objdump"
with open(elf,"rb") as f:
 s=ELFFile(f).get_section_by_name(".symtab")
 names=sorted({x.name for x in s.iter_symbols() if x["st_info"]["type"]=="STT_FUNC" and ("s3_entropy_collect" in x.name or x.name in ["nsealr_s3_public_auxiliary","bootloader_random_enable","bootloader_random_disable","esp_random"] or any(x.name.startswith(z) for z in ["_ZL7observeR","_ZL6enable","_ZL7cleanup","_ZL5claim"]))})
for name in names:
 print("SELECTED_FUNCTION",name,flush=True)
 out=subprocess.check_output([str(objdump),"-d","--disassemble="+name,str(elf)],text=True)
 assert "<"+name+">:" in out,name
 print(out,flush=True)
