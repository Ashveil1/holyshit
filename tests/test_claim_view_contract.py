#!/usr/bin/env python3
"""A24.0a contract tests for the claim view REFERENCE MODEL (python only).

These pin the contract in agent/CLAIM_VIEW_CONTRACT.md. They do not test
the agent (no Holy code exists for the view) and the model passing proves
nothing about a later implementation: the shared fixtures exist so the
later Oracle and core can be held to the same cases.
"""
import copy, itertools, json, random, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'claimview'))
import ref_claim_view as m

FIX = json.loads((HERE / 'claimview' / 'fixtures-0a.json').read_text())
EX = {'version': 1, 'sources': []}
fails = 0


def check(name, cond, detail=''):
    global fails
    if cond:
        print('ok   ' + name)
    else:
        fails += 1
        print('FAIL %s %s' % (name, detail))


def Q(s, p, o, neg=False):
    return {'propositions': [{'s': s, 'p': p, 'o': o, 'neg': neg}]}


def st(**k):
    d = {'facts': {}, 'aliases': {}, 'rels': [], 'readings': [], 'guards': []}
    d.update(k)
    return d


def texts(items):
    return [i['text'] for i in items]


# 1. shared fixtures (the same file the Oracle will use later)
for c in FIX['cases']:
    s0, e0 = copy.deepcopy(c['state']), copy.deepcopy(c['ex'])
    out = m.view(c['state'], c['query'], c['ex'])
    ex = c['expect']
    ok = True
    why = ''
    for k, v in ex.items():
        if k == 'support' or k == 'opposition':
            got = texts(out.get(k, []))
        elif k == 'blocked_count':
            got = len(out['derivations_blocked'])
        elif k == 'derivation_nodes_truncated':
            got = out['truncated']['derivation_nodes']
        elif k == 'readings':
            rs = out.get('readings')
            got = None if rs is None else [[r['source'], r['side']] for r in rs]
        else:
            got = out.get(k)
        if got != v:
            ok = False
            why = '%s: %r != %r' % (k, got, v)
    check('fixture ' + c['name'], ok, why)
    check('fixture ' + c['name'] + ' read-only',
          c['state'] == s0 and c['ex'] == e0)
    json.dumps(out)

# 2. exact status truth table over the four evidence conditions
def build(dp, vp, dn, vn):
    rels, facts = [], {'a': ['x'], 'z': ['x'], 'w': ['x']}
    if dp:
        rels.append(['a', 'is', 'b'])
    if vp:
        rels += [['a', 'is', 'z'], ['z', 'is', 'b']]
    if dn:
        rels.append(['a', 'not-is', 'b'])
    if vn:
        rels += [['a', 'is', 'w'], ['w', 'not-is', 'b']]
    return st(facts=facts, rels=rels)


for dp, vp, dn, vn in itertools.product([0, 1], repeat=4):
    out = m.view(build(dp, vp, dn, vn), Q('a', 'is', 'b'), EX)
    pos, opp = dp or vp, dn or vn
    if pos and opp:
        want = ('CONTRADICTED', 'both_sides')
    elif pos:
        want = ('SUPPORTED', 'support_only' if dp else 'derived_only')
    elif opp:
        want = ('CONTRADICTED', 'opposition_only')
    else:
        want = ('UNKNOWN', 'no_trusted_evidence')
    check('truth table dp=%d vp=%d dn=%d vn=%d' % (dp, vp, dn, vn),
          (out['epistemic'], out['basis']) == want, str(out['epistemic']))

# 3. readings never change status or evidence lists (with/without)
base = build(1, 0, 0, 0)
rd = [{'s': 'a', 'p': 'is', 'o': 'b', 'pos': [['s1', 'a is b']], 'neg': [['s2', 'a is not b']], 'marker': 'USER_CONFIRMED'}]
with_r = dict(copy.deepcopy(base), readings=rd)
o1, o2 = m.view(base, Q('a', 'is', 'b'), EX), m.view(with_r, Q('a', 'is', 'b'), EX)
for k in ('epistemic', 'basis', 'support', 'opposition', 'truncated'):
    check('readings do not change ' + k, o1[k] == o2[k])
check('readings carry the unverified label and the marker is not auth',
      all(r['label'] == m.READING for r in o2['readings']) and
      o2['readings'][0]['marker'] == 'USER_CONFIRMED' and
      m.IDENTITY in o2['labels'].values())
check('reading with only an opposite-side entry leaves a SUPPORTED claim '
      'SUPPORTED', o2['epistemic'] == 'SUPPORTED')

# 4. privacy: filter BEFORE order, count and cap; output == state without
many = [{'s': 'a', 'p': 'is', 'o': 'b', 'pos': [['s%d' % i, 'sent %d' % i] for i in range(8)], 'neg': [], 'marker': ''}]
sec = {'version': 1, 'sources': ['s0', 's1', 's2']}
full = dict(copy.deepcopy(base), readings=many)
pruned = copy.deepcopy(many)
pruned[0]['pos'] = [e for e in pruned[0]['pos'] if e[0] not in sec['sources']]
a = m.view(full, Q('a', 'is', 'b'), sec)
b = m.view(dict(copy.deepcopy(base), readings=pruned), Q('a', 'is', 'b'), EX)
check('excluded readings: output equals state without them', a == b)
check('cap 5 applied after eligibility, truncation counts only eligible',
      len(a['readings']) == 5 and a['readings_truncated'] == 0 and
      [r['source'] for r in a['readings']] == ['s3', 's4', 's5', 's6', 's7'])
blob = json.dumps(a)
check('no excluded source or sentence anywhere in output',
      'sent 0' not in blob and '"s0"' not in blob and 'hidden' not in blob)
allx = m.view(full, Q('a', 'is', 'b'), {'version': 1, 'sources': ['s%d' % i for i in range(8)]})
check('all readings excluded: section absent, no hint',
      'readings' not in allx and 'readings_truncated' not in allx)
for bad in (None, [], 'x', {}, {'version': 2, 'sources': []},
            {'version': 1}, {'version': 1, 'sources': 'x'},
            {'version': 1, 'sources': [1]}, {'version': 1, 'sources': ['']}):
    o = m.view(full, Q('a', 'is', 'b'), bad)
    check('malformed exclusions fail closed: %r' % (bad,),
          'readings' not in o and o['epistemic'] == 'SUPPORTED')
nos = m.view(dict(copy.deepcopy(base), readings=[]), Q('a', 'is', 'b'), EX)
check('fail-closed output equals state with no readings',
      m.view(full, Q('a', 'is', 'b'), None) == nos)
bad_src = dict(copy.deepcopy(base), readings=[{'s': 'a', 'p': 'is', 'o': 'b', 'pos': [[None, 'x'], [7, 'y']], 'neg': [], 'marker': ''}])
check('readings without a usable source id are dropped',
      'readings' not in m.view(bad_src, Q('a', 'is', 'b'), EX))
amb = st(facts={'jaguar': ['x'], 'car': ['y']}, aliases={'jaguar': 'car'},
         readings=[{'s': 'jaguar', 'p': 'is', 'o': 'a cat', 'pos': [['src-secret', 'leak me']], 'neg': [], 'marker': ''}])
o = m.view(amb, Q('jaguar', 'is', 'a cat'), sec | {'sources': ['src-secret']})
check('ambiguity path shows no readings and only taught candidates',
      'readings' not in o and o['candidates'] == ['car', 'jaguar'] and
      'leak me' not in json.dumps(o))
o = m.view(amb, Q('jaguar', 'is', 'a cat'), None)
check('ambiguity path never carries readings even when unfiltered',
      'readings' not in o)

# 5. determinism and ordering independent of state order; not chronology
rng = random.Random(7)
s5 = st(facts={k: ['x'] for k in 'abcdefg'},
        rels=[['a', 'is', c] for c in 'bcdef'] + [[c, 'has', 'wings'] for c in 'bcdef'])
ref = m.view(s5, Q('a', 'has', 'wings'), EX)
same = True
for _ in range(20):
    t = copy.deepcopy(s5)
    rng.shuffle(t['rels'])
    ks = list(t['facts'].items())
    rng.shuffle(ks)
    t['facts'] = dict(ks)
    same = same and m.view(t, Q('a', 'has', 'wings'), EX) == ref
check('output independent of rels/facts insertion order', same)
check('support items sorted lexicographically (not chronological)',
      texts(ref['support']) == sorted(texts(ref['support'])))
check('caps: 5 shown, truncation counted explicitly',
      len(ref['support']) == 5 and ref['truncated']['support'] == 0)
s6 = st(facts={k: ['x'] for k in 'abcdefgh'},
        rels=[['a', 'is', c] for c in 'bcdefg'] + [[c, 'has', 'wings'] for c in 'bcdefg'])
r6 = m.view(s6, Q('a', 'has', 'wings'), EX)
check('6 derivations: 5 shown, 1 more', len(r6['support']) == 5 and r6['truncated']['support'] == 1)
check('no ranking or time words in a view',
      not any(w in json.dumps(r6).lower() for w in ('rank', 'reliab', 'confiden', 'recent', 'earlier', 'later', 'score')))

# 6. forgotten data and session logs are never read
s7 = copy.deepcopy(base)
s7['forgotten'] = ['a secret thing']
s7['session'] = [['forgot', 'a secret thing']]
o7 = m.view(s7, Q('a', 'is', 'b'), EX)
check('tombstones and session log are ignored',
      o7 == m.view(base, Q('a', 'is', 'b'), EX) and 'secret' not in json.dumps(o7))
fz = m.view(st(facts={}, rels=[]), Q('a secret thing', 'is', 'b'), EX)
check('forgotten subject: UNKNOWN with no trace', fz['epistemic'] == 'UNKNOWN' and 'secret' not in json.dumps(fz))

# 7. wording and field separation
o = m.view(base, Q('a', 'is', 'b'), EX)
check('provenance wording says wording and time are not retained',
      'original wording and time are not retained' in o['labels']['assertion'])
check('identity and quality labels are cautious and separate',
      o['labels']['identity'] == 'not independently authenticated' and
      o['labels']['quality'] == 'evidence quality not assessed' and
      len({o['labels'][k] for k in o['labels']}) == 3)
check('no user-visible id or hash field',
      not any(k in json.dumps(o) for k in ('"id"', '"key"', '"hash"', 'claim_id')))
check('words true/verified never appear as a status',
      '"true"' not in json.dumps(o).lower() and 'verified' not in json.dumps(o).replace('unverified', ''))
d = m.view(build(0, 1, 0, 0), Q('a', 'is', 'b'), EX)
check('derived support carries the premises wording, never independent',
      d['support'][0]['kind'] == 'derived_rule' and len(d['support'][0]['premises']) == 2 and
      'not independent corroboration' in m.DERIVED)
check('UNKNOWN text is exactly the contract wording',
      m.view(base, Q('a', 'is', 'zzz'), EX)['text'] == 'no matching trusted support in current view')

# 8. no near matches, no pronouns
nm = st(facts={'a robin': ['x']}, rels=[['a robin', 'is', 'a bird']])
for q in ('a robins', 'robin', 'a rob', 'a robi n'):
    check('no near match: %r' % q, m.view(nm, Q(q, 'is', 'a bird'), EX)['resolution'] == 'NONE')
for w in m.REFERENCES:
    check('reference refused: ' + w, m.view(nm, Q(w, 'is', 'a bird'), EX)['status'] == 'REFUSED')
check('empty and non-string subjects resolve to NONE',
      m.resolve(nm, '')[0] == 'NONE' and m.resolve(nm, None)[0] == 'NONE' and m.resolve(nm, '   ')[0] == 'NONE')

# 9. cycles, node bound, depth semantics
cyc = st(facts={k: ['x'] for k in 'abc'}, rels=[['a', 'is', 'b'], ['b', 'is', 'c'], ['c', 'is', 'a'], ['c', 'has', 'wings']])
oc = m.view(cyc, Q('a', 'has', 'wings'), EX)
check('cycle terminates and a depth-2 proof is allowed',
      oc['epistemic'] == 'SUPPORTED' and oc['basis'] == 'derived_only')
chain = st(facts={k: ['x'] for k in 'abcd'}, rels=[['a', 'is', 'b'], ['b', 'is', 'c'], ['c', 'is', 'd'], ['d', 'has', 'wings']])
oc = m.view(chain, Q('a', 'has', 'wings'), EX)
check('premises beyond depth 2 are not expanded and truncation is explicit',
      oc['epistemic'] == 'UNKNOWN' and oc['truncated']['derivation_nodes'] is True)
wide = st(facts={'a': ['x']}, rels=[['a', 'is', 'z%02d' % i] for i in range(40)])
wide['facts'].update({'z%02d' % i: ['x'] for i in range(40)})
ow = m.view(wide, Q('a', 'has', 'wings'), EX)
check('total derivation nodes are bounded', ow['truncated']['derivation_nodes'] is True)

# 10. contradiction is narrow: same S/P/O opposite polarity only
fn = st(facts={'a robin': ['x']}, rels=[['a robin', 'in', 'a nest'], ['a robin', 'not-in', 'a tree']])
check('different objects never contradict',
      m.view(fn, Q('a robin', 'in', 'a tree'), EX)['basis'] == 'opposition_only' and
      m.view(fn, Q('a robin', 'in', 'a nest'), EX)['epistemic'] == 'SUPPORTED')
fn2 = st(facts={'a robin': ['x']}, rels=[['a robin', 'in', 'a nest']])
check('a different object of the same predicate is not opposition',
      m.view(fn2, Q('a robin', 'in', 'a tree'), EX)['opposition'] == [])

# 11. post-approval scope guard. A24.0b was approved on 2026-11-23; the old
# assert here was a pre-approval guard ("A24.0b not approved") and tripped on
# the approved 0b Holy sources (publisher kickback on PR #444). Claim-view
# code and wording may now appear ONLY in the approved 0b modules listed
# below; anywhere else still fails. Each allowlisted file must exist, so a
# rename or removal cannot hollow the list into a no-op.
CV_ALLOWLIST = ('relindex.holy', 'claimview.holy', 'cvsort.holy')  # slice 2 adds 'cvwire.holy'
adir = HERE.parent / 'agent'
holy = {f.name: f.read_text() for f in adir.glob('*.holy')}
for name in CV_ALLOWLIST:
    check('approved 0b module present: ' + name, name in holy)
stray = sorted(name for name, txt in holy.items()
               if name not in CV_ALLOWLIST and
               ('claim_view' in txt or 'm[:13] == "evidence for "' in txt or 'evidence for "' in txt))
check('no claim view outside the approved 0b modules', stray == [], stray)
# No wiring into respond()/REPL and no activation: the runtime sources must
# not reference the claim-view modules or entry points at all (C20 gate stays).
rt = (adir / 'core.holy').read_text() + (adir / 'repl.holy').read_text()
wired = [w for w in ('relindex', 'claimview', 'cvsort', 'cvwire', 'cv_view',
                     'cv_assign', 'cv_query', 'cv_holder', 'cv_status', 'cv_rebuild') if w in rt]
check('no claim-view wiring into respond()/REPL (activation stays gated)', wired == [], wired)
check('model has no I/O or clock imports',
      all(w not in (HERE / 'claimview' / 'ref_claim_view.py').read_text()
          for w in ('import os', 'import time', 'import random', 'open(')))

print('FAILS' if fails else 'all claim-view contract tests passed', fails)
sys.exit(1 if fails else 0)
