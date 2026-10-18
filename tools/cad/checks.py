"""Independent oracles: explicit divider connectivity and geometric contracts."""
import csv
import json
import re
import xml.etree.ElementTree as ET
import sexpdata
from common import HERE, digest, require, write_json

def children(tree,name):
    return [x for x in tree if isinstance(x,list) and x and str(x[0])==name]

def one(tree,name):
    rows=children(tree,name)
    require(len(rows)==1,f'Expected one {name}, got {len(rows)}')
    return rows[0]

def circuit(out,variant):
    exp=json.loads((HERE/'expected.json').read_text())
    xml=ET.parse(out/f'exports/{variant}/netlist.xml').getroot()
    components={x.attrib['ref']:x.findtext('value') for x in xml.findall('./components/comp')}
    require(components==exp['components'],'Component mismatch')
    nets={x.attrib['name'].removeprefix('/'):sorted(n.attrib['ref']+'.'+n.attrib['pin'] for n in x.findall('node')) for x in xml.findall('./nets/net')}
    require(nets=={k:sorted(v) for k,v in exp['nets'].items()},'Schematic connectivity mismatch')
    board=sexpdata.loads((out/f'fixtures/{variant}/canary.kicad_pcb').read_text())
    fps=children(board,'footprint')
    require(len(fps)==3,'Wrong footprint count')
    actual={k:[] for k in nets}
    positions={'J1':(25,30),'R1':(35,32.54),'R2':(40,32.54)}
    local_pads={'J1':{'1':(0,0),'2':(0,2.54),'3':(0,5.08)},
                'R1':{'1':(-.9125,0),'2':(.9125,0)},'R2':{'1':(-.9125,0),'2':(.9125,0)}}
    for f in fps:
        props={p[1]:p[2] for p in children(f,'property')};ref=props['Reference']
        require(props['Value']==components[ref],'Wrong value')
        require(f[1]=='Canary:'+('Header' if ref=='J1' else 'Resistor'),'Wrong footprint')
        at=one(f,'at')[1:]
        require(tuple(at[:2])==positions[ref] and (len(at)==2 or at[2]==0),'Footprint pose mismatch')
        require(one(f,'layer')[1]=='F.Cu','Footprint layer mismatch')
        pads=children(f,'pad')
        require({p[1] for p in pads}==set(local_pads[ref]),'Pad numbering mismatch')
        for pad in pads:
            actual[one(pad,'net')[1].removeprefix('/')].append(ref+'.'+pad[1])
            require(tuple(one(pad,'at')[1:3])==local_pads[ref][pad[1]],'Pad coordinate mismatch')
            layers=one(pad,'layers')[1:]
            require(layers==(['*.Cu','*.Mask'] if ref=='J1' else ['F.Cu','F.Paste','F.Mask']),'Pad layers mismatch')
    require({k:sorted(v) for k,v in actual.items()}==nets,'PCB connectivity mismatch')
    expected_routes={
      '/VIN':[((25,30),(34.0875,30)),((34.0875,30),(34.0875,32.54))],
      '/VOUT':[((35.9125,32.54),(37.5,32.54)),((37.5,32.54),(39.0875,32.54)),
               ((25,32.54),(29,32.54)),((29,32.54),(29,39)),((29,39),(37.5,39)),((37.5,39),(37.5,32.54))],
      '/GND':[((40.9125,32.54),(43,32.54)),((43,32.54),(43,42)),((43,42),(27,42)),((27,42),(27,35.08)),((27,35.08),(25,35.08))]}
    expected={(n,a,b) for n,pairs in expected_routes.items() for a,b in pairs}
    segments=children(board,'segment')
    actual={(one(x,'net')[1],tuple(one(x,'start')[1:]),tuple(one(x,'end')[1:])) for x in segments}
    require(len(segments)==13 and actual==expected,'Track geometry mismatch')
    require(all(one(x,'width')[1]==.25 and one(x,'layer')[1]=='F.Cu' for x in segments),'Track width/layer mismatch')
    edges=[x for x in children(board,'gr_line') if one(x,'layer')[1]=='Edge.Cuts']
    actual={tuple(sorted([tuple(one(x,'start')[1:]),tuple(one(x,'end')[1:])])) for x in edges}
    points=[(20,25),(47,25),(47,45),(20,45),(20,25)]
    require(len(edges)==4 and actual=={tuple(sorted([a,b])) for a,b in zip(points,points[1:])},'Outline mismatch')
    require(not children(board,'zone') and not children(board,'via'),'Unexpected zone or via')
    return {'components':components,'nets':nets,'pads':7,'tracks':13,'outline_mm':[20,25,47,45]}

def checks(out):
    findings={}
    for v in ['bad','fixed','width','clearance','roundtrip']:
        erc=json.loads((out/f'exports/{v}/erc.json').read_text())
        drc=json.loads((out/f'exports/{v}/drc.json').read_text())
        ev=[x for sheet in erc['sheets'] for x in sheet['violations']]
        types={x['type'] for x in drc['violations']}
        findings[v]={'erc':[x['type'] for x in ev],'drc':sorted(types),
                     'unconnected':len(drc['unconnected_items']),'parity':len(drc['schematic_parity']),
                     'ignored':drc['ignored_checks']}
        if v in ['fixed','roundtrip']:
            require(not(ev or drc['violations'] or drc['unconnected_items'] or drc['schematic_parity']),f'{v} native gate failed')
        elif v=='bad':
            require({'pin_not_connected','label_dangling'} <= {x['type'] for x in ev},'Missing negative ERC finding')
            require('shorting_items' in types and drc['unconnected_items'] and drc['schematic_parity'],'Missing negative PCB finding')
        elif v=='width':require('track_width' in types,'Narrow track was not rejected')
        elif v=='clearance':require('clearance' in types,'Copper clearance was not rejected')
    first=circuit(out,'fixed');second=circuit(out,'roundtrip')
    require(first==second,'Roundtrip changed circuit semantics')
    for v in ['fixed','roundtrip']:
        export=out/f'exports/{v}'
        with (export/'bom.csv').open() as f:bom=list(csv.DictReader(f))
        require({r['Reference']:r['Value'] for r in bom}==first['components'],'BOM mismatch')
        with (export/'placement.csv').open() as f:pos=list(csv.DictReader(f))
        require({r['Ref']:r['Val'] for r in pos}==first['components'],'Placement components')
        require(all(r['Side']=='top' and float(r['Rot'])==0 for r in pos),'Placement side/rotation')
        require({r['Ref']:(float(r['PosX']),float(r['PosY'])) for r in pos}=={'J1':(25,-30),'R1':(35,-32.54),'R2':(40,-32.54)},'CPL coordinates')
        drill=(export/'drill/canary.drl').read_text()
        require('METRIC' in drill and 'T1C1.000' in drill,'Drill format/tool')
        require(re.findall(r'^X([^Y]+)Y(.+)$',drill,re.M)==[('25.0','-30.0'),('25.0','-32.54'),('25.0','-35.08')],'Drill locations')
        gerbers=list((export/'gerbers').glob('*.g*'))
        require(len([x for x in gerbers if x.suffix!='.gbrjob'])==9,'Gerber layer count')
        for p in gerbers:
            if p.suffix!='.gbrjob':require('M02*' in p.read_text() and p.stat().st_size>100,'Incomplete Gerber')
        require((export/'schematic.pdf').read_bytes().startswith(b'%PDF-'),'Missing PDF')
        require('<svg' in (export/'board.svg').read_text(),'Missing SVG')
    require(json.loads((out/'mcp-read.json').read_text())['passed'],'MCP failed')
    return {'circuit':first,'native_findings':findings}
