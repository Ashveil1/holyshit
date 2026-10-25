"""b547.py - B-547 harness: English frames sharing ONE attribute memory via taught links.
C1 teach-Thai ask-English; C2 teach-English ask-Thai; C3 ambiguity abstain + resolution;
C4 unseen phrasing abstains + English question words never stored; C5 save/load +
noninterference (b546, b544 subprocess)."""
import json, random, subprocess, sys
from hsml import HSML
import b521

def fresh(seed=0):
    h = HSML(seed=seed)
    for s in b521.gen_corpus(random.Random(0), 8): h.hear(s)
    return h

def s1():
    h = fresh()
    out = {}
    h.hear('ปีก ภาษาอังกฤษคือ wings')
    h.hear('ขน ภาษาอังกฤษคือ fur')
    r = h.hear('does นก have wings'); out['c1_yn_taught'] = [r['kind'], r.get('text'), r.get('answer')]
    r = h.hear('does นก have fur'); out['c1_yn_notaught'] = [r['kind'], r.get('text'), r.get('answer')]
    r = h.hear('what does นก have'); out['c1_rev'] = [r['kind'], r.get('text')]
    out['c1'] = (out['c1_yn_taught'] == ['yesno', 'yes', 'yes']
                 and out['c1_yn_notaught'] == ['yesno', 'unknown', 'unknown']
                 and out['c1_rev'][0] == 'attr_list' and 'ปีก' in out['c1_rev'][1])
    return out

def s2():
    h = HSML(seed=0)   # NO demo corpus: English teaching must build the memory alone
    out = {}
    h.hear('นก ภาษาอังกฤษคือ bird')
    h.hear('ปีก ภาษาอังกฤษคือ wings')
    r = h.hear('a bird has wings'); out['teach_en'] = [r['kind'], r.get('text')]
    r = h.hear('นก มี อะไรบ้าง'); out['th_rev'] = [r['kind'], r.get('text')]
    r = h.hear('ปีก'); out['th_probe'] = [r['kind'], r.get('text')]
    r = h.hear('นก มี ปีก ไหม'); out['th_yn'] = [r['kind'], r.get('text')]
    out['c2'] = (out['teach_en'][0] == 'observed'
                 and out['th_rev'] == ['attr_list', 'นก มี ปีก']
                 and out['th_probe'][0] == 'attr_answer' and 'นก' in str(out['th_probe'][1])
                 and out['th_yn'] == ['yesno', 'ใช่'])
    return out

def s3():
    h = HSML(seed=0)
    out = {}
    h.hear('นก ภาษาอังกฤษคือ bird')
    h.hear('ปีก ภาษาอังกฤษคือ wings')
    h.hear('a bird has wings')
    h.hear('แมว ภาษาอังกฤษคือ bird')   # ambiguous surface word on purpose
    r = h.hear('what does bird have'); out['amb_rev'] = [r['kind'], r.get('text')]
    r = h.hear('does bird have wings'); out['amb_yn'] = [r['kind'], r.get('text')]
    r = h.hear('แมว ภาษาอังกฤษไม่ใช่ bird'); out['retract'] = [r['kind'], r.get('text')]
    r = h.hear('what does bird have'); out['resolved_rev'] = [r['kind'], r.get('text')]
    out['c3'] = (out['amb_rev'][0] == 'abstain' and 'นก' in out['amb_rev'][1] and 'แมว' in out['amb_rev'][1]
                 and out['amb_yn'][0] == 'abstain'
                 and out['retract'] == ['link_retracted', 'ลบแล้ว']
                 and out['resolved_rev'] == ['attr_list', 'bird has ปีก'])
    return out

def s4():
    h = fresh()
    out = {}
    r = h.hear('a bird has beautiful wings'); out['unseen'] = [r['kind'], r.get('text')]
    r = h.hear('what has wings'); out['qword_stmt'] = [r['kind'], r.get('text')]
    r = h.hear('ปีก'); probe_after = [r['kind'], r.get('text')]
    out['probe_after'] = probe_after   # nothing polluted the store
    out['c4'] = (out['unseen'][0] == 'abstain'
                 and out['qword_stmt'][0] in ('abstain', 'unsupported_question')
                 and probe_after[0] == 'attr_answer' and 'นก' in str(probe_after[1]))
    return out

def s5():
    h = HSML(seed=0)
    out = {}
    h.hear('นก ภาษาอังกฤษคือ bird'); h.hear('ปีก ภาษาอังกฤษคือ wings')
    h.hear('a bird has wings')
    h.save('/tmp/b547_mem.pkl')
    h2 = HSML.load('/tmp/b547_mem.pkl', seed=0)
    r = h2.hear('what does bird have'); out['loaded_rev'] = [r['kind'], r.get('text')]
    r = h2.hear('does นก have wings'); out['loaded_yn'] = [r['kind'], r.get('text')]
    ok_load = out['loaded_rev'] == ['attr_list', 'bird has ปีก'] and out['loaded_yn'] == ['yesno', 'yes']
    for t in ('b546', 'b544'):
        p = subprocess.run([sys.executable, '-u', f'{t}.py'], capture_output=True, text=True)
        jl = next((ln for ln in p.stdout.strip().splitlines() if ln.startswith('{')), '')
        out[f'noninterf_{t}'] = json.loads(jl)['verdict'] if p.returncode == 0 and jl else f'rc={p.returncode}'
    out['c5'] = ok_load and out['noninterf_b546'] == 'PASS' and out['noninterf_b544'] == 'PASS'
    return out

if __name__ == '__main__':
    o = {'s1': s1(), 's2': s2(), 's3': s3(), 's4': s4(), 's5': s5()}
    checks = {k: v[k2] for k, v in o.items() for k2 in v if k2.startswith('c') and isinstance(v[k2], bool)}
    print(json.dumps({**o, 'checks': checks,
                      'verdict': 'PASS' if all(checks.values()) else 'FAIL'}, ensure_ascii=False))
    print('DONE')
