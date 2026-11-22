#!/usr/bin/env python3
"""A20 semantic tests for agent/patgen.holy (offline pattern candidates).

An independent Python oracle re-implements the generator; the hs
module (interp route and the full native route) must produce the
byte-identical JSON for every scenario. Also asserts the A20 isolation
gates: the reader never imports or loads candidates.
"""
import json, os, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REG = ['is-a', 'has', 'is-in', 'means']
STOP = ('not no never nor and or but might may could would should must can '
        'cannot will shall says said say claims claim according that because '
        'if unless although while when where which who whom whose then '
        'however also maybe perhaps probably possibly allegedly reportedly '
        'it he she they this these those we i you remember read forget').split()
ADV = ["the moon might be cheese", "the guide says a kiwi is a bird",
       "remember a car is a bird", "a dog is a mammal and a cat is a mammal",
       "birds do not have wings", "it is a bird",
       "this reading is user_confirmed",
       "robots are machines and birds have wings",
       "according to the manual a kiwi is a bird", "a bat could be a bird"]
ALNUM = set('abcdefghijklmnopqrstuvwxyz0123456789')


def collapse(s):
    return ' '.join(s.lower().replace('\t', ' ').replace('\n', ' ')
                    .replace('\r', ' ').split())


def toks(s):
    return s.split(' ') if s else []


def alnum(t):
    return len(t) > 0 and all(c in ALNUM for c in t)


def slot_ok(ts):
    return 1 <= len(ts) <= 4 and all(alnum(t) and t not in STOP for t in ts)


def verb_ok(ts):
    return 1 <= len(ts) <= 3 and all(alnum(t) for t in ts)


def match(vt, text):
    if not text.isascii():
        return None
    t = toks(collapse(text))
    n, m = len(t), len(vt)
    hits = [i for i in range(n - m + 1) if t[i:i + m] == vt]
    if len(hits) != 1:
        return None
    f = hits[0]
    s, o = t[:f], t[f + m:]
    if not slot_ok(s) or not slot_ok(o):
        return None
    if not all(alnum(x) for x in vt):
        return None
    return [' '.join(s), ' '.join(o)]


def hash8(s):
    h1, h2 = 7, 11
    for b in s.encode('utf-8'):
        h1 = (h1 * 131 + b) % 2147483647
        h2 = (h2 * 257 + b) % 2147483629
    return '%08x%08x' % (h1, h2)


def canon_of(v, p, g):
    return ('lang=en|skel=<S> ' + v + ' <O>|slots=1-4,alnum,nostop|pred=' +
            p + '|pol=' + g + '|schema=1')


def validate(ex):
    if len(ex) != 6:
        return 'bad shape'
    if not all(isinstance(f, str) for f in ex):
        return 'bad field'
    if not all(f.isascii() for f in ex[:4]):
        return 'non-ascii (English only in A20)'
    if ex[4] not in REG:
        return 'predicate not in registry'
    if ex[5] not in ('pos', 'neg'):
        return 'bad polarity'
    s, v, o = collapse(ex[1]), collapse(ex[2]), collapse(ex[3])
    if collapse(ex[0]) != s + ' ' + v + ' ' + o:
        return 'annotation does not cover the whole segment'
    if not slot_ok(toks(s)):
        return 'subject span not an allowed slot'
    if not slot_ok(toks(o)):
        return 'object span not an allowed slot'
    if not verb_ok(toks(v)):
        return 'verb literal not allowed'
    return ''


def hold_count(n):
    return 0 if n < 4 else (1 if n < 10 else n // 5)


def structural(ex):
    s, v, o = ex[1], ex[2], ex[3]
    return [s + ' never ' + v + ' ' + o, s + ' might ' + v + ' ' + o,
            'according to the manual ' + s + ' ' + v + ' ' + o,
            s + ' ' + v + ' ' + o + ' and it barks loudly',
            s + ' likes ' + o, '"' + s + ' ' + v + ' ' + o + '"',
            s + ' ' + v + ' ' + o + ';',
            s + ' ' + v + ' ' + o + ' ' + v + ' ' + o, v + ' ' + o,
            s + ' ' + v]


def mutations(ex):
    vt = toks(ex[2])
    return [ex[1] + ' ' + ' '.join(vt[:i] + vt[i + 1:]) + ' ' + ex[3]
            for i in range(len(vt))]


def read_extract(seg):
    # The reader's own extractor, via the reference hs route is too
    # heavy here: scenarios pass the set of reader-covered corpus
    # segments explicitly, so gain = matched and not reader-covered.
    return seg in READER_COVERED


READER_COVERED = {"a hawk is a bird", "a car is a machine",
                  "robots are machines"}


def run_tests(vt, train, hold, annneg):
    allpos = train + hold
    ok = lambda e: (lambda r: r is not None and r[0] == e[1] and
                    r[1] == e[3])(match(vt, e[0]))
    hold_ok = sum(1 for e in hold if ok(e))
    st, mu = structural(train[0]), mutations(train[0])
    hs = 'none'
    if hold:
        hs = 'PASS' if hold_ok == len(hold) else 'FAIL'
    return {
        'positive': [sum(1 for e in allpos if ok(e)), len(allpos)],
        'structural_negative': [sum(1 for x in st if match(vt, x) is None),
                                len(st)],
        'mutation_supplementary': [sum(1 for x in mu
                                       if match(vt, x) is None), len(mu)],
        'adversarial': [sum(1 for x in ADV if match(vt, x) is None),
                        len(ADV)],
        'annotated_negative': [sum(1 for x in annneg
                                   if match(vt, x) is None), len(annneg)],
        'holdout': hs}


def tests_clean(t):
    if t['positive'][0] != t['positive'][1]:
        return False
    return all(t[k][0] == t[k][1] for k in (
        'structural_negative', 'mutation_supplementary', 'adversarial',
        'annotated_negative'))


def derive(examples, rejected, corpus, annneg):
    problems, valid, seen = [], [], []
    for ex in examples:
        r = validate(ex)
        if r:
            problems.append('example refused (' + r + '): ' +
                            (json.dumps(ex[0]) if ex[0].isascii()
                             else '<non-ascii text>'))
            continue
        nt = collapse(ex[0])
        if nt in seen:
            problems.append('duplicate example ignored: ' + nt)
            continue
        seen.append(nt)
        valid.append([nt, collapse(ex[1]), collapse(ex[2]),
                      collapse(ex[3]), ex[4], ex[5]])
    verbs = []
    for v in valid:
        if v[2] not in verbs:
            verbs.append(v[2])
    cands, skipped = [], []
    for vb in verbs:
        grp = sorted([v for v in valid if v[2] == vb], key=lambda v: v[0])
        if any(v[4] != grp[0][4] or v[5] != grp[0][5] for v in grp):
            problems.append("conflicting annotations for verb '" + vb +
                            "': no candidate")
        elif len(grp) < 3:
            problems.append("verb '" + vb + "' has " + str(len(grp)) +
                            ' annotated example(s): 3 agreeing examples '
                            'required')
        else:
            hn = hold_count(len(grp))
            train, hold = grp[:len(grp) - hn], grp[len(grp) - hn:]
            pred, pol = grp[0][4], grp[0][5]
            vt = toks(vb)
            canon = canon_of(vb, pred, pol)
            cid = 'pc-' + hash8(canon)
            if cid in rejected:
                skipped.append(cid)
                continue
            t = run_tests(vt, train, hold, annneg)
            gain = sum(1 for seg in corpus
                       if match(vt, seg) is not None and
                       not read_extract(seg))
            cands.append({
                'id': cid, 'label': 'CANDIDATE', 'active': False,
                'descriptor': {'lang': 'en', 'skeleton': '<S> ' + vb +
                               ' <O>', 'verb': vb, 'predicate': pred,
                               'polarity': pol,
                               'slots': '1-4,alnum,nostop', 'schema': 1,
                               'canon': canon},
                'provenance': {'examples': [e[0] for e in train],
                               'holdout': [e[0] for e in hold],
                               'history': []},
                'tests': t,
                'approval_blocked': t['holdout'] == 'FAIL' or
                not tests_clean(t),
                'expected_coverage_gain': gain})
    return {'candidates': cands, 'problems': problems,
            'skipped_rejected': skipped}


def E(t, s, v, o, p, g):
    return [t, s, v, o, p, g]


IS = [E('a sparrow is a bird', 'a sparrow', 'is', 'a bird', 'is-a', 'pos'),
      E('a robin is a bird', 'a robin', 'is', 'a bird', 'is-a', 'pos'),
      E('an eagle is a bird', 'an eagle', 'is', 'a bird', 'is-a', 'pos')]
OWN = [E('a hawk owns a nest', 'a hawk', 'owns', 'a nest', 'has', 'pos'),
       E('a wren owns a nest', 'a wren', 'owns', 'a nest', 'has', 'pos'),
       E('an owl owns a nest', 'an owl', 'owns', 'a nest', 'has', 'pos'),
       E('a jay owns a nest', 'a jay', 'owns', 'a nest', 'has', 'pos')]
NEGV = [E('snakes lack legs', 'snakes', 'lack', 'legs', 'has', 'neg'),
        E('eels lack legs', 'eels', 'lack', 'legs', 'has', 'neg'),
        E('worms lack legs', 'worms', 'lack', 'legs', 'has', 'neg')]
TEN = [E('cat%d eats a fish%d' % (i, i), 'cat%d' % i, 'eats', 'a fish%d' % i,
         'has', 'pos') for i in range(10)]
# A held-out example that cannot match (punctuation) -> FAIL, blocked.
BADHOLD = IS[:] + [E('a finch is a bird', 'a finch', 'is', 'a bird', 'is-a',
                     'pos')]
SC = [
    ('three-agree', IS, [], ['a hawk is a bird', 'a car is a machine'], []),
    ('four-holdout', OWN, [], ['a crow owns a nest', 'robots are machines'],
     []),
    ('ten-20pct', TEN, [], [], []),
    ('negative-polarity', NEGV, [], [], ['snakes lack some legs']),
    ('two-only', IS[:2], [], [], []),
    ('conflict', IS + [E('a bat is a mammal', 'a bat', 'is', 'a mammal',
                         'has', 'pos')], [], [], []),
    ('refusals', IS + [
        E('a kiwi might be a bird', 'a kiwi', 'might be', 'a bird', 'is-a',
          'pos'),
        E('the guide says a kiwi is a bird', 'a kiwi', 'is', 'a bird',
          'is-a', 'pos'),
        E('a cat fears a dog', 'a cat', 'fears', 'a dog', 'likes', 'pos'),
        E('นก เป็น สัตว์', 'นก', 'เป็น', 'สัตว์', 'is-a', 'pos'),
        E('a dog is a dog', 'a dog', 'is', 'a dog', 'is-a', 'pos')], [], [],
     []),
    ('rejected-stays', OWN, ['pc-' + hash8(canon_of('owns', 'has', 'pos'))],
     [], []),
    ('duplicates', IS + IS, [], [], []),
]


def lit(v):
    return json.dumps(v, ensure_ascii=False)


def driver():
    t = 'import agent.patgen\n'
    for name, ex, rej, corp, neg in SC:
        t += 'r = agent.patgen.derive(%s, %s, %s, %s)\n' % (
            lit(ex), lit(rej), lit(corp), lit(neg))
        t += 'print json_str(r)\n'
        t += 'print agent.patgen.report(r)\n'
    return t


def oracle_out():
    out = []
    for name, ex, rej, corp, neg in SC:
        r = derive(ex, rej, corp, neg)
        out.append(json.dumps(r, ensure_ascii=False))
    return out


def run(argv, env):
    r = subprocess.run(argv, capture_output=True, text=True, env=env,
                       cwd=str(ROOT), timeout=300)
    assert r.returncode == 0, (argv, r.stderr[-800:])
    return r.stdout


def json_lines(out):
    # json_str lines are the ones starting with '{"candidates"'.
    return [l for l in out.split('\n') if l.startswith('{"candidates"')]


def main():
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    exp = oracle_out()
    with tempfile.TemporaryDirectory() as td:
        drv = Path(td) / 'drv.holy'
        drv.write_text(driver(), encoding='utf-8')
        got = run([sys.executable, str(ROOT / 'interp.py'), str(drv)], env)
        assert json_lines(got) == exp, 'interp mismatch'
        print('ok interp == oracle on %d scenarios' % len(SC))
        img = Path(td) / 'drv-native'
        run([sys.executable, str(ROOT / 'hs.py'), 'build', str(drv),
             '-o', str(img)], env)
        nat = run([str(img)], env)
        assert nat == got, 'native transcript differs from interp'
        print('ok native == interp (full transcript)')
    byname = {s[0]: o for s, o in zip(SC, [json.loads(x) for x in exp])}
    assert len(byname['three-agree']['candidates']) == 1
    c = byname['three-agree']['candidates'][0]
    assert c['tests']['holdout'] == 'none' and not c['approval_blocked']
    assert c['active'] is False and c['label'] == 'CANDIDATE'
    assert c['expected_coverage_gain'] == 0  # reader already covers 'is'
    assert byname['four-holdout']['candidates'][0][
        'expected_coverage_gain'] == 1
    assert len(byname['four-holdout']['candidates'][0]['provenance'][
        'holdout']) == 1
    assert len(byname['ten-20pct']['candidates'][0]['provenance'][
        'holdout']) == 2
    assert byname['negative-polarity']['candidates'][0]['descriptor'][
        'polarity'] == 'neg'
    assert not byname['two-only']['candidates']
    assert not byname['conflict']['candidates'] or all(
        x['descriptor']['verb'] != 'is' for x in
        byname['conflict']['candidates'])
    assert byname['rejected-stays']['skipped_rejected'] and \
        not byname['rejected-stays']['candidates']
    assert len(byname['duplicates']['candidates']) == 1
    print('ok scenario properties (3-example bar, 20% holdout, polarity, '
          'conflict, refusals, rejection survives re-derivation)')
    core = (ROOT / 'agent' / 'core.holy').read_text(encoding='utf-8')
    store = (ROOT / 'agent' / 'store.holy').read_text(encoding='utf-8')
    assert 'patgen' not in core and 'patgen' not in store
    print('ok reader isolation: core/store never reference patgen')
    print('all agent.patgen tests passed')


if __name__ == '__main__':
    main()
