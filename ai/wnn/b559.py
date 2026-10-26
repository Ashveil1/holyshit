# B-559 batteries: Milo end-to-end acceptance + polarity/uncertainty/atomicity +
# is-a yes/no + scoped anaphora + spacing-tolerance regression + measured RSS (C7).
# Script-form (sweep discipline). Verdict lines: PASS/FAIL per check; FAILS: n at end.
import resource, sys
from hsml import HSML

fails = []
def check(label, cond, detail=''):
    print(('PASS ' if cond else 'FAIL ') + label + ((' | ' + str(detail)) if not cond else ''))
    if not cond:
        fails.append(label)

# ---------- C1: Ash's Milo dialogue end-to-end ----------
h = HSML()
r1 = h.hear('มิโล เป็น แมว และ แมว เป็น สัตว์เลี้ยงลูกด้วยนม')
check('C1 compound stored', r1['kind'] == 'compound_stored' and len(r1.get('stored', [])) == 2, r1)
r2 = h.hear('แมว เป็น สัตว์เลี้ยงลูกด้วยนม ไหม')
check('C1 direct is-a question', r2['kind'] == 'isa_yesno' and r2['answer'] == 'yes', r2)
r3 = h.hear('มิโล เป็น สัตว์เลี้ยงลูกด้วยนม ไหม')
check('C1 transitive is-a question', r3['kind'] == 'isa_yesno' and r3['answer'] == 'yes' and r3.get('path') == ['มิโล', 'แมว', 'สัตว์เลี้ยงลูกด้วยนม'], r3)
r4 = h.hear('มัน เป็น แมว ไหม')
check('C1 pronoun binds to มิโล not แมว', r4.get('via_anaphora') == 'มัน -> มิโล' and r4.get('answer') == 'yes', r4)
h.hear('แมว มี หนวด')  # most recent subject becomes แมว (designed most-recent rule)
r5 = h.hear('แล้ว มัน มี อะไรบ้าง')
check('C1 แล้ว+pronoun attr_list binds recent subject', r5['kind'] == 'attr_list' and 'หนวด' in (r5.get('text') or '') and r5.get('via_anaphora') == 'มัน -> แมว', r5)
r5b = h.hear('มัน เป็น สัตว์เลี้ยงลูกด้วยนม ไหม')
check('C1 follow-up pronoun keeps topic', r5b.get('via_anaphora') == 'มัน -> แมว' and r5b.get('answer') == 'yes', r5b)
r6 = h.hear('มิโล มี นม ไหม')
check('C1 honest unknown attr', r6['kind'] == 'yesno' and r6['answer'] == 'unknown', r6)

# ---------- C2: polarity / uncertainty / atomicity ----------
h = HSML()
r = h.hear('มิโล เป็น แมว และ บอร์ท น่าจะ มี ปีก')
check('C2 uncertain clause skipped', r['kind'] == 'compound_stored' and r['stored'] == ['มิโล เป็น แมว'] and len(r['skipped']) == 1, r)
r = h.hear('บอร์ท มี ปีก ไหม')
check('C2 uncertain never stored', r['answer'] == 'unknown', r)
h.hear('แมว มี หาง')
r = h.hear('แมว มี หนวด และ แมว ไม่มี หาง')
check('C2 store+retract in one compound', r['kind'] == 'compound_stored' and len(r['stored']) == 2, r)
r = h.hear('แมว มี หาง ไหม')
check('C2 retracted clause not held', r['answer'] in ('no_explicit', 'unknown'), r)
r = h.hear('แมว มี หนวด ไหม')
check('C2 sibling clause stored', r['answer'] == 'yes', r)
r = h.hear('มิโล เป็น แมว และ เมื่อไหร่จะ ว่ายน้ำ')
check('C2 malformed clause skipped not stored', r['kind'] == 'compound_stored' and r['stored'] == ['มิโล เป็น แมว'] and len(r['skipped']) == 1, r)
r = h.hear('น่าจะ บอร์ท มี ปีก และ มิโล เป็น หมา')
check('C2 leading-uncertain clause skipped', r['kind'] == 'compound_stored' and r['stored'] == ['มิโล เป็น หมา'] and len(r['skipped']) == 1, r)
r = h.hear('บอร์ท มี ปีก ไหม')
check('C2 leading-uncertain never stored', r['answer'] == 'unknown', r)

# ---------- C3: is-a yes/no battery ----------
h = HSML()
h.hear('มิโล เป็น แมว'); h.hear('แมว เป็น สัตว์'); h.hear('สัตว์ เป็น สิ่งมีชีวิต')
check('C3 direct', h.hear('มิโล เป็น แมว ไหม')['answer'] == 'yes')
r = h.hear('มิโล เป็น สิ่งมีชีวิต ไหม')
check('C3 transitive 3-hop with path', r['answer'] == 'yes' and r['path'] == ['มิโล', 'แมว', 'สัตว์', 'สิ่งมีชีวิต'], r)
check('C3 unknown', h.hear('มิโล เป็น หมา ไหม')['answer'] == 'unknown')
check('C3 unknown name', h.hear('บอร์ท เป็น แมว ไหม')['answer'] == 'unknown')
h.hear('แมว เป็น มิโล')  # cycle มิโล->แมว->มิโล
r = h.hear('มิโล เป็น สัตว์ ไหม')
check('C3 cycle terminates and still answers', r['answer'] == 'yes', r)
r = h.hear('สัตว์ เป็น สิ่งมีชีวิต ไหม')
check('C3 cycle sibling still answers', r['answer'] == 'yes', r)
h.hear('ไม่ใช่ มิโล เป็น แมว')
r = h.hear('มิโล เป็น สัตว์ ไหม')
check('C3 withdrawal breaks chain', r['answer'] == 'unknown', r)

# ---------- C4: scoped anaphora ----------
h = HSML()
h.hear('มิโล เป็น แมว'); h.hear('มิโล มี หนวด')
r = h.hear('มัน มี หนวด ไหม')
check('C4 single-topic pronoun binds', r.get('via_anaphora') == 'มัน -> มิโล' and r['answer'] == 'yes', r)
r = h.hear('เขา มี อะไรบ้าง')
check('C4 เขา binds same topic', r.get('via_anaphora') == 'เขา -> มิโล' and r['kind'] == 'attr_list', r)
h2 = HSML()
h2.hear('มิโล เป็น แมว และ บอร์ท มี ปีก')  # mixed-topic compound
r = h2.hear('มัน มี อะไรบ้าง')
check('C4 multi-topic compound -> clarify not bind', r['kind'] == 'anaphora_abstain' and set(r.get('candidates', [])) == {'มิโล', 'บอร์ท'}, r)
h3 = HSML()
h3.hear('มิโล เป็น แมว')
h3.hear('บอร์ท มี ปีก')
r = h3.hear('มัน มี ปีก ไหม')
check('C4 binds most recent topic', r.get('via_anaphora') == 'มัน -> บอร์ท' and r['answer'] == 'yes', r)
h4 = HSML()
r = h4.hear('มัน มี อะไรบ้าง')
check('C4 no topic -> abstain', r['kind'] == 'anaphora_abstain' and not r.get('candidates'), r)
h5 = HSML()
h5.hear('มิโล เป็น แมว และ แมว เป็น สัตว์เลี้ยงลูกด้วยนม')
r = h5.hear('มัน มี อะไรบ้าง')
check('C4 chain compound topic is head not class', r.get('via_anaphora') == 'มัน -> มิโล', r)

# ---------- C5: spacing tolerance + multiword content ----------
h = HSML()
h.hear('แมว มี หนวด'); h.hear('แมว มี หางยาว')
r1 = h.hear('แมว มี อะไรบ้าง')
r2 = h.hear('แมว มี อะไร บ้าง')
check('C5 spacing variant matches exact frame content', r1['kind'] == r2['kind'] == 'attr_list' and r1['text'] == r2['text'] and 'หนวด' in r2['text'], (r1, r2))
check('C5 spacing variant preserves all stored content', 'หางยาว' in (r2.get('text') or '') and r2['text'] == r1['text'], r2)
r3 = h.hear('แมว มี อะไร บ้าง ไหม')
check('C5 spacing frame does not over-match', r3['kind'] != 'attr_list' or 'หนวด' in (r3.get('text') or ''), r3)

# ---------- C7: measured whole-process RSS ----------
peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
print(f'C7 peak RSS this battery process: {peak_kb/1024:.1f} MB')

print('FAILS:', len(fails))
sys.exit(1 if fails else 0)
