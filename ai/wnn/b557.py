"""B-557 harness: bounded n-hop composition unification (pre-registered in LEDGER 2026-10-26).
Nonce words; live memory; kind/text/provenance compat on old 2/3-hop inputs; 4-hop new;
over-cap honest absence; มี-cycle safe; retraction mid-chain."""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from hsml import HSML

FAILS = []
def check(cid, cond, detail):
    print(('PASS' if cond else 'FAIL'), cid, '' if cond else str(detail)[:200], flush=True)
    if not cond: FAILS.append(cid)

h = HSML(seed=0)
# C1a: old 2-hop input -> identical kind/text/prov shape as before
h.hear('มิวน์ มี ท็อป'); h.hear('ท็อป มี รีก')
r = h.hear('มิวน์ มี อะไรที่มี รีก')
check('C1a', r['kind'] == 'composed' and r['text'] == 'มิวน์ มี ท็อป และ ท็อป มี รีก'
      and r['prov'] == [('ท็อป', ('own', None), ('own', None))], r)
# C1b: old 3-hop input -> identical
h.hear('คิวน์ มี ล็อก'); h.hear('ล็อก มี แพท'); h.hear('แพท มี สิง')
r = h.hear('คิวน์ มี อะไรที่มี แพท ที่มี สิง')
check('C1b', r['kind'] == 'composed3' and r['text'] == 'คิวน์ มี ล็อก และ ล็อก มี แพท และ แพท มี สิง'
      and r['prov'] == [('ล็อก', ('own', None), ('own', None), ('own', None))], r)
# C2a: 4-hop TH, with one inherited hop + provenance
h2 = HSML(seed=0)
h2.hear('กัล เป็น วีร'); h2.hear('วีร มี อัค'); h2.hear('อัค มี เอก'); h2.hear('เอก มี ไอ๋'); h2.hear('ไอ๋ มี อู๊')
r = h2.hear('กัล มี อะไรที่มี เอก ที่มี ไอ๋ ที่มี อู๊')
check('C2a', r['kind'] == 'composed4'
      and r['text'] == 'กัล มี อัค และ อัค มี เอก และ เอก มี ไอ๋ และ ไอ๋ มี อู๊'
      and r['prov'] == [('อัค', ('inherited', 'วีร'), ('own', None), ('own', None), ('own', None))], r)
# C2b: 4-hop EN twin
h2.hear('กัล ภาษาอังกฤษคือ kan'); h2.hear('เอก ภาษาอังกฤษคือ ek'); h2.hear('ไอ๋ ภาษาอังกฤษคือ ai'); h2.hear('อู๊ ภาษาอังกฤษคือ uu')
r = h2.hear('what does kan have that has ek that has ai that has uu')
check('C2b', r['kind'] == 'composed4'
      and r['text'] == 'kan has อัค and อัค has ek and ek has ai and ai has uu', r)
# C3: over-cap chain (4 attrs = 5 links) -> honest absence, both languages
r = h2.hear('กัล มี อะไรที่มี เอก ที่มี ไอ๋ ที่มี อู๊ ที่มี เอี่ย')
check('C3a', r['kind'] == 'compose_unknown' and r['text'] == 'ไม่รู้', r)
r = h2.hear('what does kan have that has ek that has ai that has uu that has zz')
check('C3b', r['kind'] == 'compose_unknown' and r['text'] == 'unknown', r)
# C4: มี-cycle in graph -> search terminates, correct answer
h3 = HSML(seed=0)
h3.hear('จั่น มี ขั้น'); h3.hear('ขั้น มี จั่น'); h3.hear('ขั้น มี ตั้น')
r = h3.hear('จั่น มี อะไรที่มี ตั้น')
check('C4', r['kind'] == 'composed' and r['text'] == 'จั่น มี ขั้น และ ขั้น มี ตั้น', r)
# C6: retract a middle link of a verified 4-hop chain -> ไม่รู้
h2.hear('ไม่ใช่ เอก มี ไอ๋')
r = h2.hear('กัล มี อะไรที่มี เอก ที่มี ไอ๋ ที่มี อู๊')
check('C6', r['kind'] == 'compose_unknown' and r['text'] == 'ไม่รู้', r)

print('FAILS:', len(FAILS), flush=True)
sys.exit(1 if FAILS else 0)
