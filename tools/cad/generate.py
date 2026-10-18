#!/usr/bin/env python3
"""Disposable resistor divider: 3 components, 7 pads, 3 named nets.
Adapted from the nSealr authored 2026-10-18 readiness canary; see provenance.json.
Runs with the AppImage Python, and imports SWIG only for native fixture creation.
The actual acceptance checks run in native KiCad CLI and live IPC/MCP separately.
"""
import json, pathlib, shutil, sys, uuid, os
from common import runtime, output, require
os.environ["KICAD_CONFIG_HOME"] = str(runtime() / "config")
os.environ["KICAD_DOCUMENTS_HOME"] = str(runtime() / "documents")
import pcbnew as pcb
BASE, OUT = runtime(), output()
require(not (OUT / "fixtures").exists(), "Refuse existing fixture output")
LIB=BASE/'squashfs-root/share/kicad'
NS=uuid.UUID('8c208174-42aa-4423-80d6-6881f1fa9656')
def uid(s): return str(uuid.uuid5(NS,s))
def block(text,start):
 i=text.index(start); depth=0; quoted=False; escaped=False
 for j in range(i,len(text)):
  c=text[j]
  if c=='"' and not escaped: quoted=not quoted
  if not quoted:
   if c=='(': depth+=1
   elif c==')':
    depth-=1
    if depth==0:return text[i:j+1]
  escaped=(c=='\\' and not escaped)
 raise ValueError('unbalanced symbol')
symbols={}
for n,lib in [('R','Device'),('Conn_01x03','Connector_Generic')]:
 symbols[n]=block((LIB/f'symbols/{lib}.kicad_symdir/{n}.kicad_sym').read_text(),f'(symbol "{n}"')
def prop(n,v,x,y,hide=False):return f'(property "{n}" "{v}" (at {x} {y} 0) (effects (font (size 1.27 1.27))'+(' (hide yes)' if hide else '')+'))'
ROOT=uid('sheet')
refs=[('J1','Conn_01x03','DIVIDER_IO',114.3,76.2,'Header'),('R1','R','10k',76.2,63.5,'Resistor'),('R2','R','10k',76.2,88.9,'Resistor')]
def schematic(bad=False):
 parts=[f'(kicad_sch (version 20250114) (generator "restart_canary") (uuid "{ROOT}") (paper "A4")', '(title_block (title "Disposable KiCad qualification canary") (comment 1 "10k/10k divider, synthetic tooling fixture; not a production design"))', '(lib_symbols '+''.join(s.replace(f'(symbol "{n}"',f'(symbol "Canary:{n}"',1) for n,s in symbols.items())+')']
 for ref,name,val,x,y,fp in refs:
  parts.append(f'(symbol (lib_id "Canary:{name}") (at {x} {y} 0) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid "{uid(ref)}") '+prop('Reference',ref,x+5.08,y-2.54)+prop('Value',val,x+5.08,y)+prop('Footprint','Canary:'+fp,x,y,True)+f'(instances (project "canary" (path "/{ROOT}" (reference "{ref}") (unit 1)))))')
 def wire(a,b,key):parts.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{uid(key)}"))')
 def label(n,xy,key):parts.append(f'(label "{n}" (at {xy[0]} {xy[1]} 0) (effects (font (size 1.27 1.27)) (justify left bottom)) (uuid "{uid(key)}"))')
 wire((76.2,59.69),(76.2,53.34),'vinwire');label('VIN',(76.2,53.34),'vinlabel')
 wire((76.2,67.31),(76.2,76.2),'outwire1');wire((76.2,76.2),(76.2,85.09),'outwire2');label('VOUT',(76.2,76.2),'outlabel')
 if not bad:wire((76.2,92.71),(76.2,99.06),'gndwire')
 label('GND',(76.2,99.06),'gndlabel')
 for i,n in enumerate(['VIN','VOUT','GND']):
  y=73.66+i*2.54;wire((109.22,y),(104.14,y),'connwire'+n);label(n,(104.14,y),'connlabel'+n)
 parts.append('(embedded_fonts no))')
 return '\n'.join(parts)+'\n'
def V(x,y):return pcb.VECTOR2I(pcb.FromMM(x),pcb.FromMM(y))
for variant in ['bad','fixed','width','clearance']:
 dest=OUT/'fixtures'/variant;dest.mkdir(parents=True,exist_ok=False)
 (dest/'canary.kicad_sch').write_text(schematic(variant=='bad'))
 (dest/'Canary.kicad_sym').write_text('(kicad_symbol_lib (version 20251024) (generator "restart_canary") '+''.join(symbols.values())+')\n')
 (dest/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Canary") (type "KiCad") (uri "${KIPRJMOD}/Canary.kicad_sym") (options "") (descr "Pinned canary library")))\n')
 pretty=dest/'Canary.pretty';pretty.mkdir(exist_ok=True)
 for filename,source in [('Header','Connector_PinHeader_2.54mm.pretty/PinHeader_1x03_P2.54mm_Vertical'),('Resistor','Resistor_SMD.pretty/R_0805_2012Metric')]:
  text=(LIB/f'footprints/{source}.kicad_mod').read_text()
  # Preserve full official footprint, changing only its library identifier.
  old=source.split('/')[-1];text=text.replace(f'(footprint "{old}"',f'(footprint "{filename}"',1)
  (pretty/(filename+'.kicad_mod')).write_text(text)
 (dest/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Canary") (type "KiCad") (uri "${KIPRJMOD}/Canary.pretty") (options "") (descr "Pinned canary footprints")))\n')
 (dest/'canary.kicad_pro').write_text(json.dumps({'meta':{'filename':'canary.kicad_pro','version':3},'board':{'design_settings':{'rules':{'min_clearance':0.2,'min_track_width':0.2}}}},indent=2)+'\n')
 b=pcb.BOARD();nets={}
 for i,n in enumerate(['VIN','VOUT','GND'],1):
  item=pcb.NETINFO_ITEM(b,"/"+n,i);b.Add(item);nets[n]=item
 positions={'J1':(25,30),'R1':(35,32.54),'R2':(40,32.54)}
 pinmap={'J1':{'1':'VIN','2':'VOUT','3':'GND'},'R1':{'1':'VIN','2':'VOUT'},'R2':{'1':'VOUT','2':'GND'}}
 for ref,_,value,_,_,fname in refs:
  f=pcb.FootprintLoad(str(pretty),fname);f.SetReference(ref);f.SetValue(value);f.SetFPID(pcb.LIB_ID('Canary',fname));f.SetPath(pcb.KIID_PATH('/'+ROOT+'/'+uid(ref)))
  f.SetPosition(V(*positions[ref]));f.Value().SetVisible(False)
  if ref=='J1':f.Reference().SetPosition(V(25,27.5))
  else:f.Reference().SetPosition(V(positions[ref][0],30.6))
  for pad in f.Pads():pad.SetNet(nets[pinmap[ref][pad.GetNumber()]])
  b.Add(f)
  print(variant,ref,[(x.GetNumber(),(pcb.ToMM(x.GetPosition().x),pcb.ToMM(x.GetPosition().y)),x.GetNetname()) for x in f.Pads()])
 routes=[('VIN',[(25,30),(34.0875,30),(34.0875,32.54)]),('VOUT',[(35.9125,32.54),(37.5,32.54),(39.0875,32.54)]),('VOUT',[(25,32.54),(29,32.54),(29,39),(37.5,39),(37.5,32.54)]),('GND',[(40.9125,32.54),(43,32.54),(43,42),(27,42),(27,35.08),(25,35.08)])]
 for ni,(n,points) in enumerate(routes):
  for j,(a,z) in enumerate(zip(points,points[1:])):
   if variant=='bad' and ni==1 and j==0:continue
   tr=pcb.PCB_TRACK(b);tr.SetStart(V(*a));tr.SetEnd(V(*z));tr.SetWidth(pcb.FromMM(.15 if variant=='width' and ni==0 and j==0 else .25));tr.SetLayer(pcb.F_Cu);tr.SetNet(nets[n]);b.Add(tr)
 # A connected GND spur runs 0.30 mm from VIN: 0.05 mm edge clearance,
 # below the project 0.20 mm minimum, without deliberately joining the nets.
 if variant=='clearance':
  for a,z in zip([(43,32.54),(43,29.7)],[(43,29.7),(30,29.7)]):
   tr=pcb.PCB_TRACK(b);tr.SetStart(V(*a));tr.SetEnd(V(*z));tr.SetWidth(pcb.FromMM(.25));tr.SetLayer(pcb.F_Cu);tr.SetNet(nets['GND']);b.Add(tr)
 # Deliberate short in bad fixture, independent of its removed VOUT segment.
 if variant=='bad':
  tr=pcb.PCB_TRACK(b);tr.SetStart(V(34.0875,32.54));tr.SetEnd(V(35.9125,32.54));tr.SetWidth(pcb.FromMM(.25));tr.SetLayer(pcb.F_Cu);tr.SetNet(nets['VIN']);b.Add(tr)
 for a,z in zip([(20,25),(47,25),(47,45),(20,45)],[(47,25),(47,45),(20,45),(20,25)]):
  edge=pcb.PCB_SHAPE();edge.SetShape(pcb.SHAPE_T_SEGMENT);edge.SetStart(V(*a));edge.SetEnd(V(*z));edge.SetWidth(pcb.FromMM(.05));edge.SetLayer(pcb.Edge_Cuts);b.Add(edge)
 txt=pcb.PCB_TEXT(b);txt.SetText('CANARY');txt.SetPosition(V(35,27.5));txt.SetTextSize(V(1,1));txt.SetTextThickness(pcb.FromMM(.15));txt.SetLayer(pcb.F_SilkS);b.Add(txt)
 b.GetTitleBlock().SetTitle('Disposable 10k/10k divider canary')
 pcb.SaveBoard(str(dest/'canary.kicad_pcb'),b)
 # Attribute the separately redistributed selected library collection.
 for p in (pathlib.Path(__file__).parent / "licenses").iterdir():
  shutil.copyfile(p, dest / p.name)
