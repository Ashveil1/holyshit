#!/usr/bin/env python3
"""A19.1 preprocessing-stage regression fixture (design note A19 v9
section 10: the converter is pinned to an exact version + config and
covered by regression fixtures).

Builds a TINY synthetic multistream dump (two stream blocks, six pages:
plain article, template+ref article, redirect -> resolved target,
empty-after-stripping page, oversized-record page, one unused page),
runs scripts/a19_preprocess.py end to end, and asserts:
  - the NDJSON output is byte-identical to the golden fixture;
  - redirect resolution, skip-and-log reasons, and the identity block
    fields (format contract, output sha256/bytes, fnv1a sidecar,
    converter name/version/config hash) are as expected.
Determinism: rerunning produces byte-identical output.
"""
import bz2
import hashlib
from xml.sax.saxutils import escape
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / 'tests' / 'fixtures' / 'a19_corpus_expected.ndjson'
sys.path.insert(0, str(ROOT / 'scripts'))
import a19_preprocess as pre  # noqa: E402

PAGE = ('<page><title>{t}</title><id>{i}</id><revision><id>{r}</id>'
        '<timestamp>2026-01-0{d}T00:00:00Z</timestamp>'
        '<text bytes="1">{x}</text></revision></page>')

PAGES = [
    ('Alpha', 101, 'Alpha is a small town. It has one bridge.'),
    ('Beta', 102, "{{Infobox thing\n|name=Beta\n}}'''Beta''' is a cup. "
                  'It holds water.<ref name=x />'
                  '<ref>{{cite web|url=http://e.example|title=E}}</ref> '
                  'See [[Alpha|the town]].'),
    ('Gamma', 103, '#REDIRECT [[Beta]]'),
    ('Delta', 104, '{{Unbalanced or infobox-only\n|x=1'),
    ('Epsilon', 105, 'Epsilon is a river. ' + 'Long. ' * 15000),
    ('Zeta', 106, 'Zeta is never selected.'),
]


def make_dump(tmp):
    # two stream blocks: pages 0-2 in the first, 3-5 in the second
    dump = tmp / 'dump.xml.bz2'
    index = tmp / 'index.txt.bz2'
    offsets = []
    blob = b''
    for group in (PAGES[:3], PAGES[3:]):
        offsets.append(len(blob))
        blob += bz2.compress(
            ''.join(PAGE.format(t=t, i=i, r=1000 + i, d=i % 9 + 1, x=escape(x))
                    for t, i, x in group).encode('utf-8'))
    dump.write_bytes(blob)
    ilines = []
    for off, group in zip(offsets, (PAGES[:3], PAGES[3:])):
        for t, i, _ in group:
            ilines.append(f'{off}:{i}:{t}')
    index.write_bytes(bz2.compress(('\n'.join(ilines) + '\n').encode()))
    return dump, index


def main():
    with tempfile.TemporaryDirectory(prefix='a19-pre-') as td:
        tmp = Path(td)
        dump, index = make_dump(tmp)
        manifest = {
            'manifest_id': 'fixture-v1',
            'source': {'dump': 'fixture', 'dump_sha256': 'x',
                       'dump_bytes': 0, 'dump_date': '2026-01-01',
                       'index': 'fixture', 'index_sha256': 'y'},
            'articles': [{'page_id': i, 'title': t, 'stratum': 'test'}
                         for t, i, _ in PAGES if i in (101, 103, 104, 105)],
        }
        mpath = tmp / 'manifest.json'
        mpath.write_text(json.dumps(manifest))
        r = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'a19_preprocess.py'),
             str(dump), str(index), str(mpath), str(tmp)],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        got = (tmp / 'corpus.ndjson').read_bytes()
        want = GOLDEN.read_bytes()
        assert got == want, (
            'NDJSON differs from golden fixture; if the converter '
            'changed intentionally, regenerate with --write-golden and '
            'review the diff')
        ident = json.loads((tmp / 'corpus.identity.json').read_text())
        assert ident['format_contract'] == 'ndjson-utf8-lead-v1'
        assert ident['output_sha256'] == hashlib.sha256(got).hexdigest()
        assert ident['output_bytes'] == len(got)
        assert ident['records'] == 2  # alpha + gamma resolved to beta
        classes = sorted(s['reason'].split(' (')[0].split(' > ')[0].rsplit(' ', 2)[0]
                         if False else s['reason'] for s in ident['skipped'])
        assert any(r.startswith('empty lead after stripping') for r in classes), classes
        assert any(r.startswith('record ') and r.endswith(' B cap')
                   for r in classes), classes
        assert len(classes) == 2, classes
        assert ident['redirect_resolutions'] == {
            '103': {'target_page_id': 102, 'chain': ['Beta']}}
        fnv = (tmp / 'corpus.fnv').read_text().split()
        assert fnv == ['fnv1a', f'{pre.fnv1a(got):08x}', 'bytes',
                       str(len(got))], fnv
    print('ok a19 preprocessing fixture: golden NDJSON byte-identical, '
          'redirect resolution, skip reasons, identity + fnv sidecar')


def write_golden():
    with tempfile.TemporaryDirectory(prefix='a19-pre-') as td:
        tmp = Path(td)
        dump, index = make_dump(tmp)
        manifest = {
            'manifest_id': 'fixture-v1',
            'source': {'dump': 'fixture', 'dump_sha256': 'x',
                       'dump_bytes': 0, 'dump_date': '2026-01-01',
                       'index': 'fixture', 'index_sha256': 'y'},
            'articles': [{'page_id': i, 'title': t, 'stratum': 'test'}
                         for t, i, _ in PAGES if i in (101, 103, 104, 105)],
        }
        mpath = tmp / 'manifest.json'
        mpath.write_text(json.dumps(manifest))
        r = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'a19_preprocess.py'),
             str(dump), str(index), str(mpath), str(tmp)],
            capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        GOLDEN.write_bytes((tmp / 'corpus.ndjson').read_bytes())
        print('golden written:', GOLDEN)
        print((tmp / 'corpus.ndjson').read_text())


if __name__ == '__main__':
    if '--write-golden' in sys.argv:
        write_golden()
    else:
        main()
