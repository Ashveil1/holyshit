#!/usr/bin/env python3
"""A19 Grammar Observatory: inventory of unsupported structures.

A20 groundwork. Counts the structures the reader does NOT extract
from, over the data available to A19: the frozen eval corpus
(tests/reader_eval.txt - its skip and unmatched fixtures) and the
fetch fixture pages (tests/fix_fetch_server.py canned bodies).

Every unsupported segment is classified into a structural category
by ordered first-match rules mirroring the reader's own skip
classes, then counted. The printed table ranks categories by a
static, argued scoring table (usefulness = knowledge coverage the
structure would add; ambiguity = misparse risk; difficulty =
implementation cost in the pattern-table architecture). The scores
are explicit judgment recorded in one place; the frequencies are
computed from the data. Nothing here changes reader behavior.

    python3 tests/reader_observatory.py            # ranked table
    python3 tests/reader_observatory.py --examples # + one example each
"""
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def eval_segments():
    """(sentence, disposition) for every skip/unmatched fixture."""
    out = []
    for line in (ROOT / 'reader_eval.txt').read_text(
            encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split('|')]
        if parts[2] in ('skip', 'unmatched'):
            out.append((parts[1], parts[2]))
    return out


def fixture_segments():
    """Text segments of the canned fixture pages, mirroring the
    reader's terminator split."""
    ns = {}
    exec((ROOT / 'fix_fetch_server.py').read_text(encoding='utf-8')
         .split('def page(')[0], ns)
    bodies = [v for k, v in sorted(ns.items())
              if k.isupper() and isinstance(v, bytes)]
    segs = []
    for body in bodies:
        text = body.decode('utf-8', 'replace')
        text = re.sub(r'<(script|style|title)[^>]*>.*?</\1>',
                      ' ', text, flags=re.S | re.I)
        text = re.sub(r'<[^>]*>', ' ', text)
        text = html.unescape(text)
        text = re.sub(r'\\s+', ' ', text).strip()
        cur = ''
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in '.!?' and (i + 1 >= len(text)
                                or text[i + 1] == ' '):
                if cur:
                    segs.append(cur)
                cur = ''
                i += 1
            else:
                cur += ch
            i += 1
        if cur:
            segs.append(cur)
    return segs


# Ordered first-match structure rules, mirroring the reader's own
# skip precedence. Each rule: (category id, predicate on the lowered
# segment). Thai categories key on Thai substrings.
def _has_thai(s):
    return any('ก' <= c <= '๙' for c in s)


RULES = [
    ('quoted-or-attributed',
     lambda s: '"' in s or "'" in s or ' says ' in s or
     ' said ' in s or ' according to ' in s or
     s.startswith('according to ')),
    ('directive-or-command-shaped',
     lambda s: s.split(' ')[0] + ' ' in
     ('remember ', 'no, ', 'mode ', 'clear ', 'forget ', 'read ',
      'note ', 'say ') or s in
     ('quit', 'exit', 'help', 'list', 'notes', 'readings',
      'click here', 'subscribe now', 'download this file')),
    ('modal-hedged declarative',
     lambda s: any(w in ' ' + s + ' ' for w in
                   (' might ', ' may ', ' could ', ' should ',
                    ' would ', ' must ', ' probably ', ' maybe ',
                    ' perhaps '))),
    ('thai-latin mixed boundary',
     lambda s: _has_thai(s) and re.search('[a-z]', s)),
    ('thai glued negation (ไม่ใช่)', lambda s: 'ไม่ใช่' in s),
    ('thai glued copula (เป็น/เคยเป็น, no spaces)',
     lambda s: 'เป็น' in s and ' เป็น ' not in s),
    ('thai glued มี (have/has)', lambda s: 'มี' in s),
    ('thai unsegmented verb phrase',
     lambda s: _has_thai(s)),
    ('compound subject (x and y are)',
     lambda s: re.match(r'.* and .* (are|have) ', s) is not None),
    ('3+-way conjunction', lambda s: s.count(' and ') >= 2),
    ('comma/semicolon multi-clause',
     lambda s: ',' in s or ';' in s),
    ('copula + adjective complement',
     lambda s: re.match(r'.* (is|are) (red|fast|huge|big|small|'
                        r'green|blue|wet)\b', s) is not None),
    ('existential there-are',
     lambda s: s.startswith('there ')),
    ('pronoun subject declarative',
     lambda s: s.split(' ')[0] in
     ('i', 'you', 'he', 'she', 'it', 'we', 'they')),
    ('quantity/measurement statement',
     lambda s: re.search(r'\\d', s) is not None),
    ('transitive verb + prepositional phrase',
     lambda s: re.search(r' (on|in|at|by|over|under|into) ', s)
     is not None),
    ('unsupported transitive verb declarative',
     lambda s: True),
]

# Static argued scores: (usefulness, ambiguity, difficulty) 1-5 and
# a one-line rationale. Judgment, recorded explicitly.
SCORES = {
    'thai glued copula (เป็น/เคยเป็น, no spaces)':
        (5, 3, 3, 'huge Thai coverage; needs word-boundary cues, '
         'marker itself is unambiguous'),
    'thai unsegmented verb phrase':
        (5, 4, 5, 'real Thai comprehension; needs a segmenter or '
         'lexicon, high misparse risk'),
    'thai glued มี (have/has)':
        (4, 3, 3, 'Thai has-relation coverage; glued boundaries '
         'are the hard part'),
    'thai glued negation (ไม่ใช่)':
        (4, 2, 2, 'Thai negative is-a; marker is lexicalized, '
         'boundaries still glued'),
    'thai-latin mixed boundary':
        (3, 2, 2, 'A19 skips these honestly; splitting needs '
         'both-sides validation (done) + segmentation'),
    'quoted-or-attributed':
        (4, 2, 4, 'attributed claims could enter as scoped '
         'evidence (X says Y); needs speaker modeling'),
    'modal-hedged declarative':
        (4, 2, 3, 'hedged claims could enter as explicitly '
         'hedged evidence; modal scope is the risk'),
    'quantity/measurement statement':
        (4, 2, 3, 'facts with numbers (boils at 100 C); needs a '
         'quantity object shape'),
    'transitive verb + prepositional phrase':
        (3, 3, 3, 'location/manner relations; PP attachment is '
         'ambiguous'),
    'unsupported transitive verb declarative':
        (3, 4, 2, 'each new verb is one pattern-table row; '
         'choosing WHICH verbs is the risk'),
    'compound subject (x and y are)':
        (3, 2, 2, 'distributes one claim over two subjects; '
         'low ambiguity'),
    'copula + adjective complement':
        (3, 3, 2, 'property edges (is red); adjective semantics '
         'are shallow but fuzzy'),
    '3+-way conjunction':
        (2, 1, 2, 'generalizes the A17 atomic split; low value, '
         'low risk'),
    'comma/semicolon multi-clause':
        (2, 4, 4, 'clause splitting without a segmenter is '
         'error-prone'),
    'existential there-are':
        (2, 3, 3, 'existence/count claims; weak knowledge value'),
    'pronoun subject declarative':
        (2, 5, 5, 'needs anaphora resolution - explicitly out of '
         'scope so far'),
    'directive-or-command-shaped':
        (1, 1, 1, 'correctly inert in A19; could later drive '
         'meta-commands from trusted channels only'),
}


def classify(seg):
    s = seg.lower()
    for name, pred in RULES:
        try:
            if pred(s):
                return name
        except Exception:
            pass
    return 'unsupported transitive verb declarative'


def main():
    verbose = '--examples' in sys.argv
    counts = {}
    examples = {}
    for seg, _disp in eval_segments():
        c = classify(seg)
        counts[c] = counts.get(c, 0) + 1
        examples.setdefault(c, seg)
    for seg in fixture_segments():
        c = classify(seg)
        counts[c] = counts.get(c, 0) + 1
        examples.setdefault(c, seg)
    rows = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    print('A19 Grammar Observatory - unsupported structures')
    print('data: tests/reader_eval.txt skip+unmatched fixtures + '
          'fix_fetch_server canned pages')
    print('rank: frequency, then usefulness/ambiguity/difficulty '
          '(1-5, static argued scores)')
    print()
    print('%-44s %3s  %2s %2s %2s  rationale' %
          ('structure', 'n', 'U', 'A', 'D'))
    for name, n in rows:
        u, a, d, why = SCORES.get(name, (0, 0, 0, ''))
        print('%-44s %3d  %2d %2d %2d  %s' % (name, n, u, a, d, why))
        if verbose:
            print('    e.g. %s' % examples[name])
    print()
    print('%d structures, %d unsupported segments' %
          (len(rows), sum(counts.values())))


if __name__ == '__main__':
    main()
