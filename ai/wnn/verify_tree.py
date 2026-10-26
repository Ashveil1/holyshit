"""Bounded live aggregate RSS monitor, includes supervisor+all descendants."""
import os,sys,subprocess,time,json,signal
BUDGET=1_000_000_000

def processes():
    ps={}
    for n in os.listdir('/proc'):
        if not n.isdigit():continue
        try:
            fields={}
            with open('/proc/'+n+'/status') as f:
                for line in f:
                    k,_,v=line.partition(':');fields[k]=v.strip()
            ps[int(n)]=(int(fields['PPid']),int(fields.get('VmRSS','0 kB').split()[0])*1024)
        except (OSError,KeyError,ValueError):pass
    return ps

if __name__=='__main__':
    pid=os.getpid();peak=0;peak_pids=[];samples=0;exceeded=False
    child=subprocess.Popen(sys.argv[1:],start_new_session=True)
    start=time.monotonic()
    while True:
        ps=processes();tree={pid}
        while True:
            nxt=tree|{p for p,(parent,rss) in ps.items() if parent in tree}
            if nxt==tree:break
            tree=nxt
        total=sum(ps.get(p,(0,0))[1] for p in tree);samples+=1
        if total>peak:peak=total;peak_pids=sorted(tree)
        if total>BUDGET or time.monotonic()-start>120:
            exceeded=total>BUDGET
            os.killpg(child.pid,signal.SIGKILL);child.wait();break
        if child.poll() is not None:break
        time.sleep(.01)
    print('LIVE-TREE '+json.dumps({'command':sys.argv[1:],'peak_concurrent_rss_bytes':peak,
          'budget_bytes':BUDGET,'exceeded':exceeded,'samples':samples,
          'sample_interval_seconds':.01,'includes':'supervisor plus all descendants',
          'pids_at_peak':peak_pids,'child_exit':child.returncode}),flush=True)
    sys.exit(137 if exceeded else child.returncode)
