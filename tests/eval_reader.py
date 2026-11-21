#!/usr/bin/env python3
"""A17 reader evaluation harness.

Runs the frozen fixtures in tests/reader_eval.txt through the agent
oracle and reports extraction precision/recall, skip-class accuracy,
false extractions, and polarity/provenance accuracy. Usable against
any build: pre-A17 builds lack per-class skip counts in the reply,
so skip-class accuracy is reported only when the format is present.

    python3 tests/eval_reader.py            # metrics
    python3 tests/eval_reader.py --verbose  # + per-fixture failures
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Reuse the oracle without executing the corpus suite: exec the test
# module up to the point where sessions are constructed.
_src = (ROOT / 'test_agent_core.py').read_text(encoding='utf-8')
_cut = _src.index('sessions = [make_session()')
_ns = {'__file__': str(ROOT / 'test_agent_core.py')}
exec(_src[:_cut], _ns)
Oracle = _ns['Oracle']

SKIP_RE = re.compile(
    r'(\d+) skipped \((\d+) quoted, (\d+) modal-hedged, (\d+) multi-clause\)')
CLASS_IDX = {'quoted': 2, 'modal-hedged': 3, 'multi-clause': 4}


def load_fixtures():
    for line in (ROOT / 'reader_eval.txt').read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        yield [p.strip() for p in line.split('|')]


def main():
    verbose = '--verbose' in sys.argv
    fixtures = list(load_fixtures())
    expected = 0          # expected triples
    correct = 0           # triples extracted with exact triple+pol+pattern+span
    records_total = 0     # records created across all fixtures
    false_extr = []       # skip/unmatched fixtures that produced records
    failures = []
    class_ok = class_total = 0
    for parts in fixtures:
        lang, sentence = parts[0], parts[1]
        kind = parts[2]
        oracle = Oracle()
        reply = oracle.respond('read ' + sentence)
        records_total += len(oracle.readings)
        if kind == 'extract':
            groups = ' | '.join(parts[2:]).split(' && ')
            spans = sentence.rstrip('.').split(' and ') if len(groups) > 1 \
                else [sentence.rstrip('.')]
            for g in groups:
                gp = [x.strip() for x in g.split('|')]
                subj, pred, obj, pol, pat = gp[1:6]
                expected += 1
                hit = next((r for r in oracle.readings
                            if r[0] == subj and r[1] == pred and r[2] == obj),
                           None)
                side = (hit[3] if pol == 'pos' else hit[4]) if hit else []
                ok = hit is not None and any(
                    se[2] == pat and se[1] in spans for se in side)
                if ok:
                    correct += 1
                else:
                    failures.append((sentence, 'want %s|%s|%s|%s|%s' %
                                     (subj, pred, obj, pol, pat),
                                     'got %r' % (oracle.readings,)))
        elif kind == 'skip':
            want_class = parts[3]
            if oracle.readings:
                false_extr.append((sentence, oracle.readings))
            m = SKIP_RE.search(reply)
            if m:
                class_total += 1
                if int(m.group(1)) == 1 and int(m.group(CLASS_IDX[want_class])) == 1:
                    class_ok += 1
                else:
                    failures.append((sentence, 'want skip class ' + want_class,
                                     'got reply ' + reply))
        else:  # unmatched
            if oracle.readings:
                false_extr.append((sentence, oracle.readings))
    print('fixtures            : %d (%d en, %d th)' % (
        len(fixtures),
        sum(1 for p in fixtures if p[0] == 'en'),
        sum(1 for p in fixtures if p[0] == 'th')))
    print('expected triples    : %d' % expected)
    print('correct extractions : %d (triple + polarity + pattern + span)' % correct)
    print('records created     : %d' % records_total)
    print('precision           : %.3f' % (correct / records_total if records_total else 1.0))
    print('recall              : %.3f' % (correct / expected if expected else 1.0))
    print('false extractions   : %d' % len(false_extr))
    for s, r in false_extr:
        print('  FALSE: %r -> %r' % (s, r))
    if class_total:
        print('skip-class accuracy : %d/%d' % (class_ok, class_total))
    else:
        print('skip-class accuracy : n/a (build has no per-class counts)')
    if verbose:
        for s, w, g in failures:
            print('FAIL %r\n  %s\n  %s' % (s, w, g))
    print('fixture failures    : %d' % len(failures))


if __name__ == '__main__':
    main()
