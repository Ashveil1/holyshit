#!/usr/bin/env python3
"""A19.1 frozen article-selection manifest builder (design note A19 v9
section 3).

Selects EXACTLY 150 articles (exact page IDs + titles), stratified
across the relation classes the extractor handles, plus deliberate hard
cases. Selection is reproducible: within each stratum, candidate titles
are ordered by FNV-1a(title, UTF-8) and the first N are taken; the stub
stratum additionally peeks at extracted lead length (same converter as
the preprocessing stage) - deterministic given the pinned dump + index
hashes recorded in the manifest.

    python3 scripts/a19_manifest.py INDEX DUMP OUT.json

Strata (150 = 5x24 ordinary + 5x6 hard):
  ordinary: animals-plants, everyday-objects, body-natural, places,
            everyday-concepts (word-match in title, seed lists below)
  hard: disambiguation ("(disambiguation)" titles), list ("List of"),
        infobox-heavy (4-digit year titles), polysemy (pinned exact-
        title word list), stub (lead < 400 bytes)
Negation and long-sentence cases are content properties: they arrive
via the ordinary strata and are characterized by the pilot's manual
audit sample, not by title selection (recorded here per the design's
hard-case list).
"""
import bz2
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from a19_preprocess import extract_articles, fnv1a  # noqa: E402

MANIFEST_ID = 'a19-pilot-150-v1'

SEEDS = {
    'animals-plants': ('cat dog bird fish tree flower horse snake bear lion '
                       'tiger monkey rabbit frog spider insect plant grass '
                       'elephant chicken whale eagle').split(),
    'everyday-objects': ('table chair car bicycle door window book pen cup '
                         'bottle telephone computer knife spoon clock shoe '
                         'shirt hat bag lamp train').split(),
    'body-natural': ('hand foot eye ear heart brain blood bone skin hair '
                     'mountain river ocean lake rain snow wind fire stone '
                     'cloud').split(),
    'places': ('city town village country island river mountain lake park '
               'bridge castle temple church museum airport station forest '
               'desert beach').split(),
    'everyday-concepts': ('love time day work play music game food water '
                          'money school family friend house colour color '
                          'number word name idea question').split(),
}
POLYSEMY_TITLES = ('Bank Bat Crane Date Rock Spring Bark Bow Fly Jam Light '
                   'Match Mouse Nail Orange Palm Park Pitch Ring Rose Scale '
                   'Seal Star Stone Train Watch Wave').split()
ORDINARY_N = 24
HARD_N = 6
STUB_MAX_LEAD_BYTES = 400


def words_of(title):
    return re.sub(r'[^a-z ]', ' ', title.lower()).split()


def fnv_key(title):
    return fnv1a(title.encode('utf-8'))


def load_titles(index_path):
    """page_id -> title for main-namespace pages (no ':' in title)."""
    out = {}
    with bz2.open(index_path, 'rt', encoding='utf-8') as f:
        for line in f:
            _, pid, title = line.rstrip('\n').split(':', 2)
            if ':' not in title:
                out[int(pid)] = title
    return out


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__)
    index_path, dump_path, out_path = argv[1:]
    titles = load_titles(index_path)
    print(f'main-namespace titles: {len(titles)}')

    selected = {}  # pid -> (title, stratum)
    articles = []

    def take(cands, stratum, n):
        cands = [(fnv_key(t), pid, t) for pid, t in cands
                 if pid not in selected]
        cands.sort()
        for _, pid, t in cands[:n]:
            selected[pid] = (t, stratum)
            articles.append({'page_id': pid, 'title': t, 'stratum': stratum})
        return len(cands)

    for stratum, seeds in SEEDS.items():
        cands = [(pid, t) for pid, t in titles.items()
                 if any(w in seeds for w in words_of(t))]
        total = take(cands, stratum, ORDINARY_N)
        print(f'{stratum}: {total} candidates -> {ORDINARY_N}')

    hard = [
        ('hard-disambiguation',
         [(pid, t) for pid, t in titles.items()
          if t.endswith('(disambiguation)')]),
        ('hard-list',
         [(pid, t) for pid, t in titles.items() if t.startswith('List of ')]),
        ('hard-year',
         [(pid, t) for pid, t in titles.items()
          if re.fullmatch(r'\d{4}', t)]),
        ('hard-polysemy',
         [(pid, t) for pid, t in titles.items() if t in POLYSEMY_TITLES]),
    ]
    for stratum, cands in hard:
        total = take(cands, stratum, HARD_N)
        print(f'{stratum}: {total} candidates -> {HARD_N}')

    # Stub stratum: FNV-ordered unused titles; first HARD_N whose
    # extracted lead is non-empty and under STUB_MAX_LEAD_BYTES.
    rest = [(fnv_key(t), pid, t) for pid, t in titles.items()
            if pid not in selected]
    rest.sort()
    peek = {pid: t for _, pid, t in rest[:400]}
    found = extract_articles(dump_path, index_path, set(peek))
    stubs = 0
    for _, pid, t in rest:
        if stubs >= HARD_N:
            break
        got = found.get(pid)
        if not got:
            continue
        if got[4].lstrip()[:9].upper() == '#REDIRECT':
            continue
        lead = got[3].encode('utf-8')
        if 0 < len(lead) < STUB_MAX_LEAD_BYTES:
            selected[pid] = (t, 'hard-stub')
            articles.append({'page_id': pid, 'title': t,
                             'stratum': 'hard-stub'})
            stubs += 1
    print(f'hard-stub: peeked {len(found)} -> {stubs}')
    if len(articles) != 150:
        raise SystemExit(f'selection incomplete: {len(articles)}/150')

    manifest = {
        'manifest_id': MANIFEST_ID,
        'created': '2026-11-26',
        'design': 'A19 v9 section 3 (stratified, FNV-ordered, hard cases)',
        'source': {
            'dump': 'simplewiki-20261101-pages-articles-multistream.xml.bz2',
            'dump_sha256':
                '995f57d1d5a6c0bc3ed4b5d690de5cbdbd71109ceb67a7118976c49027db50ca',
            'dump_bytes': 389720944,
            'dump_date': '2026-11-01',
            'index':
                'simplewiki-20261101-pages-articles-multistream-index.txt.bz2',
            'index_sha256':
                'ef7b184b6a6cefe0e37a4ad1a282b64ac67d7739a4640732a476f90dd26ced1d',
        },
        'selection': {
            'algorithm': 'per-stratum filter, order by FNV-1a(title,utf8) '
                         'ascending, take first N; stub stratum also '
                         'requires 0 < lead_bytes < 400 (converter peek)',
            'seeds': SEEDS, 'polysemy_titles': POLYSEMY_TITLES,
            'ordinary_n': ORDINARY_N, 'hard_n': HARD_N,
        },
        'articles': articles,
    }
    Path(out_path).write_text(
        json.dumps(manifest, indent=1, ensure_ascii=False) + '\n',
        encoding='utf-8')
    import hashlib
    print('manifest_sha256',
          hashlib.sha256(Path(out_path).read_bytes()).hexdigest())


if __name__ == '__main__':
    main(sys.argv)
