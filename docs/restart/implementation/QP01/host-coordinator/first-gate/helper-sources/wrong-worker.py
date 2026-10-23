import os,json,time
mode="wrong-worker"
os.write(4,b'RX' if mode=='ready-extra' else b'' if mode=='ready-missing' else b'R');os.close(4)
command=os.read(3,1)
assert command==(b'X' if mode.startswith('ready-') else b'Q')
n=time.monotonic_ns()
r={'v':1,'kind':'terminal','owner_pid':os.getpid(),'outcome':'unused','ownership':'settled','worker_pid':None,'worker_wait':None,'worker_io':{'stdin_closed':None,'stdout_eof':None,'stderr_eof':None,'owned_fds_closed':True},'session_policy_verified':False,'input_bytes_received':0,'input_sha256':None,'G_bytes':0,'image_bytes_sent':0,'stdout_observed':0,'stdout_retained':0,'stderr_observed':0,'stderr_retained':0,'worker_stderr_base64':'','result_bytes':0,'result_sha256':None,'final_worker_eligible':False,'cancel_observed':False,'timing':{'begin_ns':None,'invalidated_ns':str(n),'cleanup_deadline_ns':str(n+4000000000),'settled_ns':str(n),'final_admission_ns':str(n)}}
if mode=='wrong-owner':r['owner_pid']+=1
if mode=='wrong-worker':r['worker_pid']=99
if mode=='contradictory-IO':r['worker_io']['owned_fds_closed']=False
wire=(json.dumps(r,separators=(',',':'))+'\n').encode()
if mode=='status-missing':wire=b''
if mode=='status-truncated':wire=wire[:-1]
if mode=='status-overflow':wire=b'x'*4097
if mode=='duplicate-key':wire=wire.replace(b'{',b'{"v":1,',1)
if mode=='duplicate-terminal':wire+=wire
if mode=='phase-after-terminal':wire+=b'{"kind":"worker_ready"}\n'
if mode.startswith('ready-'):wire=b''
try:os.write(5,wire)
except BrokenPipeError:pass
