import os as _o, sys as _s; _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))  # experiments/ bootstrap: resolve ai/wnn modules
import induce as I, cur2 as C, sys
P={'add':('bwd','bwd','tape+r',I.fn('((x+(r+y))%10)'),I.fn('((x+(r+y))//10)')),
 'sub':('bwd','bwd','tape',I.fn('(((x-y)-r)%10)'),I.fn('(1 if (x-y)<r else 0)')),
 'mul1':('bwd','bwd','tape+r',I.fn('((r+(x*y))%10)'),I.fn('((r+(x*y))//10)')),
 'shift':('fwd','fwd','tape+r',I.fn('x'),I.fn('y')),
 'compare':('bwd','fwd','final',I.fn('r'),I.fn('(1 if (y-x)<r else 0)'))}
L=C.Lib(P); ops=set(sys.argv[2].split(',')) if len(sys.argv)>2 else {'add','sub','mul1','shift','cmp','ite'}
for name in sys.argv[1].split(','):
    f,tried,dt,nT,nB=C.run_task(name,L,ops)
    print(name, sorted(ops), 'FOUND' if f else 'NOT FOUND', f and (f[0],[C.show(x) for x in f[1:]]), 'tried',tried, round(dt),'s', nT, nB, C.test(name,f,L) if f else '', flush=True)
