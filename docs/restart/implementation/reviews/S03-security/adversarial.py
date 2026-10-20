#!/usr/bin/env python3
"""Independent Python grammar/canonical/inspection expectations against public Rust APIs."""
import hashlib,itertools,json,pathlib,random,re,subprocess
OWN=pathlib.Path(__file__).resolve().parent
ROOT=OWN.parents[4]
KEY='f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9'
BASE={'created_at':0,'kind':1,'tags':[],'content':''}
def dump(x,ascii=False):return json.dumps(x,ensure_ascii=ascii,separators=(',',':')).encode()
def pairs(p):
    d={}
    for k,v in p:
        if k in d:raise ValueError('duplicate')
        d[k]=v
    return d
def number(s):
    if not re.fullmatch(r'0|[1-9][0-9]*',s):raise ValueError('integer syntax')
    return int(s)
def bad(s):raise ValueError(s)
def strict(raw):
    if len(raw)>4096:raise ValueError('input bound')
    t=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_int=number,parse_float=bad,parse_constant=bad)
    if type(t)!=dict or set(t)!={'created_at','kind','tags','content'}:raise ValueError('shape')
    if type(t['created_at'])!=int or not 0<=t['created_at']<=9007199254740991:raise ValueError('time')
    if type(t['kind'])!=int or not 0<=t['kind']<=65535:raise ValueError('kind')
    if type(t['content'])!=str or len(t['content'].encode())>2048:raise ValueError('content')
    if type(t['tags'])!=list or len(t['tags'])>32:raise ValueError('tags')
    size=len(t['content'].encode())
    for tag in t['tags']:
        if type(tag)!=list or not 1<=len(tag)<=8 or tag[0]=='':raise ValueError('tag shape')
        for f in tag:
            if type(f)!=str or len(f.encode())>256:raise ValueError('field')
            size+=len(f.encode())
    if size>4096:raise ValueError('aggregate')
    return t
def canonical(t):return dump([0,KEY,t['created_at'],t['kind'],t['tags'],t['content']]).decode()

def inspect(s):
    out='"'
    named={'"':'\\"','\\':'\\\\','\b':'\\b','\f':'\\f','\n':'\\n','\r':'\\r','\t':'\\t'}
    for c in s:
        out+=named.get(c,c if ' '<=c<='~' else '\\u{'+format(ord(c),'X')+'}')
    return out+'"'
def tokenized(line):
    i=0
    while i<len(line):
        if line[i]!='\\':
            assert 32<=ord(line[i])<=126;i+=1
        elif line[i:i+2] in ['\\"','\\\\','\\b','\\f','\\n','\\r','\\t']:i+=2
        else:
            m=re.match(r'\\u\{[0-9A-F]{1,6}\}',line[i:]);assert m,(line,i);i+=len(m.group())

def check_frames(out,t,columns,lines):
    frames=out['frames'];assert out['production']=='Err(SigningUnavailable)' and out['retry']=='Err(InvalidState)'
    groups={};last=None
    for i,f in enumerate(frames):
        assert f['index']==i and f['total']==len(frames) and f['position']==f'{i+1}/{len(frames)}'
        assert f['decision']==(i==len(frames)-1)
        assert sum(len(f[k].split('\n')) for k in ('label','body','position'))<=lines
        for key in ('label','body','position'):
            assert all(len(x)<=columns for x in f[key].split('\n'))
        label=f['label'].replace('\n','');name,fragment=label.rsplit(' / fragment ',1)
        if name not in groups:groups[name]=[]
        assert int(fragment)==len(groups[name])
        if last!=name:assert not groups[name],('nonadjacent field',name)
        last=name
        for line in f['body'].split('\n'):tokenized(line)
        groups[name].append(f['body'].replace('\n',''))
    fields={k:''.join(v) for k,v in groups.items()}
    expected={'Signed kind':str(t['kind']),'Signed created_at (untrusted timestamp)':str(t['created_at']),'Signed tag count':str(len(t['tags'])),'Signed content (plain text)':t['content'],'Selected actual signing identity':KEY,'Canonical event ID':out['event_id'],'Request ID (host correlation only)':'r','Decision':'Approve?'}
    for k,v in expected.items():assert fields[k]==inspect(v),(k,fields[k],inspect(v))
    signed_tags={k:v for k,v in fields.items() if re.match(r'^Signed tag [0-9]+ field [0-9]+: ',k)}
    assert len(signed_tags)==sum(map(len,t['tags']))
    for ti,tag in enumerate(t['tags']):
        for fi,value in enumerate(tag):
            matches=[v for k,v in signed_tags.items() if k.startswith(f'Signed tag {ti} field {fi}: ')]
            assert matches==[inspect(value)],(ti,fi,value,matches)
    return len(frames)

cases=[]
def add(raw,**extra):cases.append({'bytes':list(raw),**extra})
for order in itertools.permutations(BASE):add(dump({k:BASE[k] for k in order}))
# Deliberately distinguish literal escapes, bidi, C0/DEL, supplementary scalars,
# combining text, private use and quote-like mathematical/confusable characters.
strings=['','\\u{202E}','\u202e','\\n','\n','U+202E','e\u0301','é','\ufeff','\u200d','\u2066x\u2069','\U0010ffff','\U0001f600','"\\/',''.join(map(chr,range(32)))+'\x7f','  a\t b \r\n  ']
for value in strings:
    for ascii in [False,True]:add(dump({**BASE,'content':value,'tags':[['x',value,'']]},ascii),review=True)
for value in ['-0','00','01','1e0','1.0','+1','NaN','Infinity','null','true','"1"','18446744073709551616']:
    for field in ['created_at','kind']:add(dump(BASE).replace(('"'+field+'":'+str(BASE[field])).encode(),('"'+field+'":'+value).encode()))
for field in BASE:
    raw=dump(BASE)
    add(raw[:-1]+b','+dump(field)+b':null}')
    alias=''.join('\\u%04x'%ord(c) for c in field)
    add(raw[:-1]+b',"'+alias.encode()+b'":null}')
    add(dump({k:v for k,v in BASE.items() if k!=field}))
for suffix in [b'{}',b' null',b'\x00',b',',b'\xc2\xa0',b'\x0b'] :add(dump(BASE)+suffix)
for prefix in [b'\xef\xbb\xbf',b'\x00',b'// comment\n',b'[']:add(prefix+dump(BASE))
for content in [b'\xff',b'\xc0\x80',b'\xed\xa0\x80',b'\xf4\x90\x80\x80',b'\x1f',b'\\uD800',b'\\uDC00',b'\\uD800x',b'\\x41']:
    add(dump(BASE).replace(b'"content":""',b'"content":"'+content+b'"'))
for t in [{**BASE,'tags':[[]]},{**BASE,'tags':[['']]},{**BASE,'tags':[['x']*9]},{**BASE,'tags':[['x']]*33},{**BASE,'content':'a'*2049},{**BASE,'tags':[['x','a'*257]]},{**BASE,'created_at':9007199254740992},{**BASE,'kind':65536}]:add(dump(t))
# Unknown members reject without recursively walking attacker-chosen structures.
add(dump(BASE)[:-1]+b',"unknown":'+b'['*1600+b'0'+b']'*1600+b'}')
rng=random.Random(0x5303)
for _ in range(1800):
    raw=bytearray(dump(BASE));action=rng.randrange(3);p=rng.randrange(len(raw))
    if action==0:raw[p]=rng.randrange(256)
    elif action==1:del raw[p]
    else:raw[p:p]=bytes([rng.randrange(256)])
    add(bytes(raw))
# Geometry acceptance is deliberately inspected, not assumed. Every admitted
# review must be complete; rejected geometries must fail before any approval.
rich={**BASE,'created_at':9007199254740991,'content':('a'*29+'\\u{202E}\u202e\n\U0010ffff')*20,'tags':[['x','suffix:'+('e\u0301 '*35),''],['p',KEY,'wss://Example.com:65535/a%2f:b@c', 'signed extension']]}
for width in range(10,33):
    for height in [6,7,8]:add(dump(rich),review=True,columns=width,lines=height)
for width in range(10,33):add(dump({**BASE,'content':''.join(strings)}),review=True,columns=width,lines=8)
# Hand-specified semantic controls (grammar is tested above independently).
semantics=[]
def semantic(tags,expected):
    i=len(cases);add(dump({**BASE,'tags':tags}),review=True);semantics.append((i,expected))
ID='ab'*32;OTHER='34'*32
for tags in [[],[['e',ID]],[['e',ID,'','root']],[['e',ID,'','root'],['e',OTHER,'','reply']],[['q',ID,'',KEY]],[['q','30023:'+KEY+':a:b','']],[['p',KEY,'','uninterpreted']], [['x','1'],['x','1']]]:semantic(tags,True)
for uri in ['', 'ws://127.0.0.1', 'wss://ExAmPlE.com:443/a%2F!$&\'()*+,;=:@/_~.-', 'ws://a'] :semantic([['p',KEY,uri]],True)
for uri in ['wss://127.01.0.1','wss://1.2.3','wss://256.1.1.1','wss://u@h','wss://[::1]','wss://-a.example','wss://a-.example','wss://a..example','wss://a:0','wss://a:01','wss://a:65536','wss://a/%','wss://a/%0G','wss://a?q','wss://a/#fragment','wss://é.com','WSS://a','wss://a/\\','wss://a/\n'] :semantic([['p',KEY,uri]],False)
for tags in [[['e',ID,'','reply']],[['e',ID,'','root'],['e',ID,'','reply']],[['e',ID,'','root'],['e',OTHER]],[['e',ID,'','root'],['e',OTHER,'','root']],[['e',ID,'','mention']],[['e',ID.upper()]],[['p','ff'*32]],[['q',ID,'']],[['q','030023:'+KEY+':x','']],[['q','10002:'+KEY+':nonempty','']],[['q','1:'+KEY+':','']],[['emoji','x','wss://a']]]:semantic(tags,False)
# Envelope member aliases/duplicates and authority-looking host input.
env={'version':1,'request_id':'r','method':'sign_event','params':{'event_template':BASE}}
for order in itertools.permutations(env):add(dump({k:env[k] for k in order}),envelope=True,expected=True)
for field in env:
    alias=''.join('\\u%04x'%ord(c) for c in field)
    add(dump(env).replace(dump(field),('"'+alias+'"').encode(),1),envelope=True,expected=True)
    add(dump(env)[:-1]+b',"'+alias.encode()+b'":null}',envelope=True,expected=False)
for field in ['approved','trusted','button','approval_digest','pubkey','id','sig','policy','host_origin']:
    add(dump({**env,field:True}),envelope=True,expected=False)
for value in ['1.0','1e0','01','0','2','null','true']:
    add(dump(env).replace(b'"version":1',b'"version":'+value.encode()),envelope=True,expected=False)
add(dump(env)+b'{}',envelope=True,expected=False)

payload=''.join(json.dumps(x)+'\n' for x in cases)
p=subprocess.run([str(OWN/'build/debug/s03-security-probe')],input=payload.encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
(OWN/'evidence/adversarial-inputs.jsonl').write_text(payload)
(OWN/'evidence/adversarial-output.jsonl').write_bytes(p.stdout)
(OWN/'evidence/adversarial-stderr.log').write_bytes(p.stderr)
assert p.returncode==0,(p.returncode,p.stderr)
outputs=[json.loads(x) for x in p.stdout.splitlines()];assert len(outputs)==len(cases)
stats={'cases':len(cases),'strict_accepted':0,'strict_rejected':0,'canonical_matches':0,'reviews_reconstructed':0,'frames_reconstructed':0,'preflight_rejections':0,'envelope_checks':0,'semantic_checks':len(semantics)}
for i,(case,out) in enumerate(zip(cases,outputs)):
    if case.get('envelope'):
        for k in ('parsed_request','qr','serial'):assert out[k]==case['expected'],(i,k,case,out)
        stats['envelope_checks']+=1;continue
    try:t=strict(bytes(case['bytes']));expected=True
    except (ValueError,UnicodeError):expected=False
    assert out['template']==expected,(i,bytes(case['bytes']),out,expected)
    stats['strict_accepted' if expected else 'strict_rejected']+=1
    # Framing has its own small limits. Malformed template inputs must reject at
    # every real path; known-small positive controls must succeed at all paths.
    if not expected:
        assert not out['parsed_request'] and not out['qr'] and not out['serial'],(i,out)
    elif len(case['bytes'])<700 and not case.get('review'):
        assert out['parsed_request'] and out['qr'] and out['serial'],(i,out)
    if expected:
        c=canonical(t);assert out['canonical']==c and out['event_id']==hashlib.sha256(c.encode()).hexdigest(),(i,out)
        stats['canonical_matches']+=1
        if 'frames' in out:
            stats['frames_reconstructed']+=check_frames(out,t,case.get('columns',32),case.get('lines',8));stats['reviews_reconstructed']+=1
        elif case.get('review') and out['kind1']:
            assert out['review_error']=='Inspection(Limit)',(i,out);stats['preflight_rejections']+=1
for i,expected in semantics:
    assert outputs[i]['kind1']==expected,(i,cases[i],outputs[i],expected)
    assert ('frames' in outputs[i])==expected,(i,'authorization semantic mismatch',outputs[i])
assert stats['reviews_reconstructed']>40 and stats['strict_accepted']>30 and stats['strict_rejected']>1000
(OWN/'evidence/adversarial-summary.json').write_text(json.dumps(stats,indent=2)+'\n')
print(json.dumps(stats,sort_keys=True))
