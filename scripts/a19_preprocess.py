#!/usr/bin/env python3
"""A19.1 corpus preprocessing stage (design note A19 v9 sections 2-3).

PINNED CONVERSION PIPELINE: Simple English Wikipedia multistream XML
dump -> frozen plain-text intermediate corpus, format contract
"ndjson-utf8-lead-v1": one JSON object per line, UTF-8, LF endings, no
BOM, fixed field set and order (title, page_id, revision_id,
revision_timestamp, lead_text).

Deterministic: same dump + same manifest + same converter version and
config => byte-identical output. The converter version and config hash
are emitted into the identity block (section 2's IMMEDIATE-CORPUS
IDENTITY). Every wikitext-stripping decision lives HERE; hs itself only
parses flat NDJSON.

Acquisition is out-of-band (see PROVENANCE.md next to the dump). This
tool never downloads anything.

    python3 scripts/a19_preprocess.py DUMP INDEX MANIFEST OUTDIR

Writes OUTDIR/corpus.ndjson, OUTDIR/corpus.fnv (FNV-1a + byte length
sidecar, the in-hs accident check), OUTDIR/corpus.identity.json.
"""
import bz2
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET

CONVERTER_NAME = 'a19-wiki-to-ndjson'
CONVERTER_VERSION = '1.0.0'
# Every stripping rule below is part of the pinned configuration.
CONFIG = {
    'lead': 'text before the first level-2 heading (== ... ==)',
    'strip': [
        'html comments', 'ref tags (paired and self-closing)',
        'balanced {{...}} templates', '{| ... |} tables',
        '[[File:...]]/[[Image:...]]/[[Category:...]] links',
        'external [url label] links keep the label',
        "''' bold and '' italic markers", '<...> html tags',
    ],
    'link_rule': '[[a|b]] -> b; [[a]] -> a',
    'whitespace': 'paragraphs separated by blank lines; lines stripped; '
                  'runs of spaces folded',
    'record_fields': ['title', 'page_id', 'revision_id',
                      'revision_timestamp', 'lead_text'],
    'record_order': 'as listed',
    'article_order': 'manifest order',
    'max_line_bytes': 64 * 1024 + 1024,
}
FORMAT_CONTRACT = 'ndjson-utf8-lead-v1'


def fnv1a(data: bytes) -> int:
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def load_index(path):
    """offset -> [(page_id, title)] from the multistream index."""
    by_offset = {}
    with bz2.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            off, pid, title = line.rstrip('\n').split(':', 2)
            by_offset.setdefault(int(off), []).append((int(pid), title))
    return by_offset


def load_title_map(path):
    """title -> page_id from the multistream index."""
    out = {}
    with bz2.open(path, 'rt', encoding='utf-8') as f:
        for line in f:
            _, pid, title = line.rstrip('\n').split(':', 2)
            out[title] = int(pid)
    return out


RE_REDIRECT = re.compile(r'^\s*#REDIRECT\s*\[\[([^\]]+)\]\]',
                         re.I)


def read_stream(dump_path, offset):
    """Decompress the single multistream block at byte offset."""
    with open(dump_path, 'rb') as f:
        f.seek(offset)
        d = bz2.BZ2Decompressor()
        out = []
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            try:
                out.append(d.decompress(chunk))
            except OSError:
                break
            if d.eof:
                break
        return b''.join(out)


def pages_of(stream_bytes):
    """Yield (page_id, title, revision_id, timestamp, text) per page."""
    root = ET.fromstring(b'<root>' + stream_bytes + b'</root>')
    for page in root.iter('page'):
        pid = int(page.findtext('id'))
        title = page.findtext('title') or ''
        rev = page.find('revision')
        rid = int(rev.findtext('id')) if rev is not None else 0
        ts = rev.findtext('timestamp') or '' if rev is not None else ''
        text = rev.findtext('text') or '' if rev is not None else ''
        yield pid, title, rid, ts, text


# --- pinned wikitext -> plain lead text ---

RE_COMMENT = re.compile(r'<!--.*?-->', re.S)
RE_REF_PAIR = re.compile(r'<ref\b[^>]*>.*?</ref\s*>', re.S | re.I)
RE_REF_SELF = re.compile(r'<ref\b[^>]*/\s*>', re.I)
RE_HEADING = re.compile(r'^==[^=].*?==\s*$', re.M)
RE_TABLE = re.compile(r'^\{\|.*?^\|\}', re.S | re.M)
RE_TAG = re.compile(r'</?[a-zA-Z][^>]*>')
RE_LINK = re.compile(r'\[\[([^\]|]*)(?:\|([^\]]*))?\]\]')
RE_EXT = re.compile(r'\[(https?://\S+)(?:\s+([^\]]*))?\]')


def _strip_templates(text):
    """Remove balanced {{...}} (nested), longest spans first-safe."""
    out = []
    i = 0
    depth = 0
    n = len(text)
    while i < n:
        two = text[i:i + 2]
        if two == '{{':
            depth += 1
            i += 2
        elif two == '}}' and depth > 0:
            depth -= 1
            i += 2
        elif depth == 0:
            out.append(text[i])
            i += 1
        else:
            i += 1
    return ''.join(out)


def _link_sub(m):
    target, label = m.group(1), m.group(2)
    if label:
        return label
    return target


def _link_drop(m):
    return ''


def lead_text(wikitext):
    """Pinned stripping pipeline; approximate BY DESIGN and documented
    as such - this is extraction-measurement input, never knowledge."""
    t = RE_COMMENT.sub('', wikitext)
    t = RE_REF_SELF.sub('', t)
    t = RE_REF_PAIR.sub('', t)
    m = RE_HEADING.search(t)
    if m:
        t = t[:m.start()]
    t = RE_TABLE.sub('', t)
    t = _strip_templates(t)
    # drop file/image/category links, keep other links' label text
    t = RE_LINK.sub(lambda m: _link_drop(m) if m.group(1).lower().startswith(
        ('file:', 'image:', 'category:')) else _link_sub(m), t)
    t = RE_EXT.sub(lambda m: m.group(2) or '', t)
    t = t.replace("'''", '').replace("''", '')
    t = RE_TAG.sub('', t)
    paras = []
    for para in t.split('\n\n'):
        lines = [re.sub(r' +', ' ', ln).strip() for ln in para.split('\n')]
        body = ' '.join(l for l in lines if l)
        if body:
            paras.append(body)
    return '\n\n'.join(paras).strip()


def extract_articles(dump_path, index_path, wanted_pids):
    """pid -> (title, revision_id, timestamp, lead_text) for the wanted
    page IDs, reading only the stream blocks that contain them."""
    by_offset = load_index(index_path)
    need = {}
    for off, pages in by_offset.items():
        hits = [(pid, title) for pid, title in pages if pid in wanted_pids]
        if hits:
            need[off] = hits
    out = {}
    for off in sorted(need):
        for pid, title, rid, ts, text in pages_of(read_stream(dump_path, off)):
            if pid in wanted_pids and pid not in out:
                out[pid] = (title, rid, ts, lead_text(text), text)
    return out


def main(argv):
    if len(argv) != 5:
        raise SystemExit(__doc__)
    dump_path, index_path, manifest_path, outdir = argv[1:]
    from pathlib import Path
    outdir = Path(outdir)
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    wanted = [a['page_id'] for a in manifest['articles']]
    articles = extract_articles(dump_path, index_path, set(wanted))
    missing = [p for p in wanted if p not in articles]
    if missing:
        raise SystemExit(f'manifest page IDs not found in dump: {missing}')

    # Redirect resolution (deterministic, recorded): a manifest entry
    # that is a redirect page is replaced by its target article, up to
    # 2 hops. The record carries the TARGET identity (title, page_id,
    # revision); the resolution is logged in the identity block.
    title2pid = load_title_map(index_path)
    resolutions = {}
    extra = set()
    for pid in wanted:
        raw = articles[pid][4]
        hops = 0
        cur = raw
        cur_pid = pid
        chain = []
        while hops < 2:
            m = RE_REDIRECT.match(cur)
            if not m:
                break
            tpid = title2pid.get(m.group(1))
            chain.append(m.group(1))
            if tpid is None or tpid == cur_pid:
                break
            cur_pid = tpid
            hops += 1
            if tpid in articles:
                cur = articles[tpid][4]
            else:
                extra.add(tpid)
                break
        if hops and cur_pid != pid:
            resolutions[pid] = {'target_page_id': cur_pid,
                                'chain': chain}
    if extra:
        articles.update(extract_articles(dump_path, index_path, extra))
    skipped = []
    lines = []
    emitted = set()
    for a in manifest['articles']:
        pid = a['page_id']
        use = resolutions.get(pid)
        if use:
            tpid = use['target_page_id']
            if tpid not in articles:
                skipped.append({'page_id': pid, 'title': articles[pid][0],
                                'reason': 'redirect target not in dump'})
                continue
            if tpid in emitted:
                skipped.append({'page_id': pid, 'title': articles[pid][0],
                                'reason': 'redirect to already-included '
                                          'article'})
                continue
            pid = tpid
        title, rid, ts, lead, raw = articles[pid]
        if RE_REDIRECT.match(raw):
            skipped.append({'page_id': pid, 'title': title,
                            'reason': 'unresolved redirect page'})
            continue
        if pid in emitted:
            continue
        if not lead.strip():
            skipped.append({'page_id': pid, 'title': title,
                            'reason': 'empty lead after stripping '
                                      '(infobox-only or empty page)'})
            continue
        rec = {'title': title, 'page_id': pid, 'revision_id': rid,
               'revision_timestamp': ts, 'lead_text': lead}
        line = json.dumps(rec, ensure_ascii=False,
                          separators=(',', ':')).encode('utf-8')
        if len(line) > CONFIG['max_line_bytes']:
            skipped.append({'page_id': pid, 'title': title,
                            'reason': f"record {len(line)} B > "
                                      f"{CONFIG['max_line_bytes']} B cap"})
            continue
        emitted.add(pid)
        lines.append(line)
    blob = b'\n'.join(lines) + b'\n'
    (outdir / 'corpus.ndjson').write_bytes(blob)
    digest = fnv1a(blob)
    (outdir / 'corpus.fnv').write_text(
        f'fnv1a {digest:08x}\nbytes {len(blob)}\n', encoding='ascii')

    config_json = json.dumps(
        {'name': CONVERTER_NAME, 'version': CONVERTER_VERSION,
         'config': CONFIG, 'format': FORMAT_CONTRACT},
        sort_keys=True, separators=(',', ':'))
    identity = {
        'format_contract': FORMAT_CONTRACT,
        'intermediate_id': hashlib.sha256(blob).hexdigest(),
        'output_sha256': hashlib.sha256(blob).hexdigest(),
        'output_bytes': len(blob),
        'output_fnv1a': f'{digest:08x}',
        'records': len(lines),
        'skipped': skipped,
        'redirect_resolutions': resolutions,
        'converter': {'name': CONVERTER_NAME,
                      'version': CONVERTER_VERSION,
                      'config_sha256':
                          hashlib.sha256(config_json.encode()).hexdigest()},
        'dump': manifest['source'],
        'manifest_id': manifest['manifest_id'],
        'manifest_sha256': hashlib.sha256(
            Path(manifest_path).read_bytes()).hexdigest(),
    }
    (outdir / 'corpus.identity.json').write_text(
        json.dumps(identity, indent=1, ensure_ascii=False) + '\n',
        encoding='utf-8')
    print(f"records {len(lines)} skipped {len(skipped)} "
          f"bytes {len(blob)} sha256 {identity['output_sha256']}")
    for s in skipped:
        print('SKIP', s['page_id'], s['title'], '-', s['reason'])


if __name__ == '__main__':
    main(sys.argv)
