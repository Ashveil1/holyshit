#!/usr/bin/env python3
"""Draft standalone Oracle for the W1 claims contract
(docs/agent/w1-claims-contract-v1.md). Runs the fixture set
tests/claims/fixtures-w1.json and reports per-case pass/fail.

Pure function semantics: promote(store, batch, policy) -> (store',
report). No clock, no random, no I/O in the gate. Reviewer verdicts
are inputs. Claim ids are assigned in canonical batch order
(source_id, span_start, key), cl-1.. in processing order within the
generation.

AI-authored / not human-validated.
"""
import json
import re
import sys
import unicodedata

PII_PATTERNS = [
    re.compile(r'\b\d{3}-\d{3}-\d{4}\b'),          # phone
    re.compile(r'\b\d{10}\b'),                       # 10-digit id/phone
    re.compile(r'\b\d{13}\b'),                       # Thai national id
    re.compile(r'\b[\w.+-]+@[\w-]+\.[\w.]+\b'),      # email
]
VALUE_CAP = 100
EXCERPT_CAP = 200


def canon(s):
    s = unicodedata.normalize('NFC', s)
    return ''.join(c.lower() if 'A' <= c <= 'Z' else c for c in s)


def is_private(text):
    return any(p.search(text) for p in PII_PATTERNS)


def charset_ok(s):
    for c in s:
        o = ord(c)
        if o < 0x20 or (0x7F <= o < 0xA1):
            return False
    return True


def rank_of(fact):
    return {'taught': 3, 'promoted': fact.get('rank', 1)}.get(fact['origin'], 1) \
        if fact['origin'] != 'taught' else 3


def promote(store, batch, policy):
    """store: {facts: {key: factrec}, claims: [claimrec], sources: {...},
    gen_next: int}. Returns (store', report list of verdicts in input
    order). All-or-nothing on cap."""
    store = json.loads(json.dumps(store))  # deep copy, pure
    store.setdefault('facts', {})
    store.setdefault('claims', [])
    store.setdefault('gen_next', 1)
    K = policy.get('K', 1000)
    reserve = policy.get('reserve', 0)

    # canonical processing order
    order = sorted(range(len(batch)),
                   key=lambda i: (batch[i]['source_id'],
                                  batch[i]['span_start'],
                                  canon(batch[i]['key'])))

    # preflight cap: worst case = current records + batch + tombstones
    worst = (len(store['claims']) + len(batch)) * 2 + len(store['facts'])
    if worst > K - reserve:
        return store, {'verdicts': ['CAP_EXCEEDED'] * len(batch),
                       'generation': 0}

    verdicts = [None] * len(batch)
    gid = store['gen_next']
    committed = False
    next_ids = {}
    seq = 0
    # ids: canonical order across existing claims + this batch
    existing_max = 0
    for c in store['claims']:
        existing_max = max(existing_max, int(c['id'].split('-')[1]))
    for i in order:
        existing_max += 1
        next_ids[i] = 'cl-' + str(existing_max)

    def claim_key(key, value, src, span):
        return (canon(key), canon(value), src, span)

    for i in order:
        r = batch[i]
        key, value = canon(r['key']), canon(r['value'])
        # 1 SPAN
        if (len(r['excerpt']) > EXCERPT_CAP or
                not (r['span_end'] > r['span_start'] >= 0)):
            verdicts[i] = 'REJECT_SPAN'
            continue
        # 2 SOURCE
        src = store['sources'].get(r['source_id'])
        if src is None or src['kind'] not in policy.get(
                'permitted_kinds', ['url', 'corpus', 'text']):
            verdicts[i] = 'REJECT_SOURCE'
            continue
        # 3 SCHEMA
        if (not key or not value or len(r['value']) > VALUE_CAP or
                not charset_ok(r['key']) or not charset_ok(r['value'])):
            verdicts[i] = 'REJECT_SCHEMA'
            continue
        # 4 PRIVACY
        if is_private(r['key']) or is_private(r['value']):
            verdicts[i] = 'REJECT_PRIVACY'
            continue
        # 5 POLARITY
        if r['polarity'] != 'pos':
            verdicts[i] = 'REJECT_POLARITY'
            continue
        # dedup record target (claim kept regardless of promote outcome)
        dup = claim_key(key, value, r['source_id'], r['span_start']) in {
            claim_key(c['key'], c['value'], c['source_id'], c['span_start'])
            for c in store['claims']}
        new_claim = {
            'id': next_ids[i], 'key': r['key'], 'value': r['value'],
            'polarity': 'pos', 'source_id': r['source_id'],
            'span_start': r['span_start'], 'span_end': r['span_end'],
            'excerpt': r['excerpt'], 'revision': r.get('revision', ''),
            'status': 'claim', 'generation_id': gid,
        }
        # 6 REVIEW / two-source auto-pass
        reviewed = r.get('review_verdict') == 'APPROVE_AS_FACT'
        independent = any(
            claim_key(c['key'], c['value'], c['source_id'],
                      c['span_start'])[0:2] == (key, value)
            and (store['sources'][c['source_id']]['host'],
                 store['sources'][c['source_id']]['page_id']) !=
            (src['host'], src['page_id'])
            for c in store['claims'] if c['status'] in ('claim', 'fact'))
        existing_fact = store['facts'].get(key)
        auto_pass = independent and not reviewed
        if not reviewed and not auto_pass:
            if not dup:
                store['claims'].append(new_claim)
                committed = True
            verdicts[i] = 'KEPT_AS_CLAIM'
            continue
        # 7 CONFLICT state machine
        if existing_fact is not None and canon(
                existing_fact['value']) != value:
            fr = 3 if existing_fact['origin'] == 'taught' else \
                existing_fact.get('rank', 1)
            my_rank = 2 if auto_pass else 1
            same_page = (existing_fact.get('source', '') == r['source_id']
                         and r['source_id'] != '')
            if existing_fact['origin'] == 'taught':
                existing_fact.setdefault('dissent', [])
                if r['source_id'] not in existing_fact['dissent']:
                    existing_fact['dissent'].append(r['source_id'])
                if not dup:
                    store['claims'].append(new_claim)
                verdicts[i] = 'REJECT_TAUGHT_WINS'
                continue
            if same_page:
                # newer revision of the same page: supersede + tombstone
                for c in store['claims']:
                    if (c['source_id'] == r['source_id'] and
                            canon(c['key']) == key and c['status'] == 'fact'):
                        c['status'] = 'tombstoned'
                        c['superseded_by'] = next_ids[i]
                new_claim['status'] = 'fact'
                new_claim['review_id'] = r.get('review_id', '')
                store['claims'].append(new_claim)
                store['facts'][key] = {
                    'value': r['value'], 'origin': 'promoted',
                    'rank': my_rank, 'source': r['source_id']}
                committed = True
                verdicts[i] = 'PROMOTED_SUPERSEDES'
                continue
            if my_rank < fr:
                existing_fact.setdefault('dissent', [])
                if r['source_id'] not in existing_fact['dissent']:
                    existing_fact['dissent'].append(r['source_id'])
                if not dup:
                    store['claims'].append(new_claim)
                verdicts[i] = 'REJECT_HIGHER_RANK'
                continue
            # equal or higher rank: keep both, conflicted
            existing_fact['status'] = 'conflicted'
            for c in store['claims']:
                if canon(c['key']) == key and c['status'] == 'fact':
                    c['status'] = 'conflicted'
            new_claim['status'] = 'conflicted'
            new_claim['review_id'] = r.get('review_id', '')
            store['claims'].append(new_claim)
            committed = True
            verdicts[i] = 'PROMOTED_CONFLICTED'
            continue
        # 8 DEDUP no-op against identical accepted fact
        if existing_fact is not None and canon(
                existing_fact['value']) == value:
            if auto_pass:
                srcs = existing_fact['source'].split('+')
                if r['source_id'] not in srcs:
                    srcs.append(r['source_id'])
                    existing_fact['source'] = '+'.join(sorted(srcs))
                existing_fact['rank'] = max(existing_fact.get('rank', 1), 2)
            if not dup:
                new_claim['status'] = 'fact'
                new_claim['review_id'] = r.get('review_id', '')
                store['claims'].append(new_claim)
                committed = True
            verdicts[i] = 'DEDUP_NOOP'
            continue
        # promote
        new_claim['status'] = 'fact'
        new_claim['review_id'] = r.get('review_id', '')
        store['claims'].append(new_claim)
        srcs = [c['source_id'] for c in store['claims']
                if canon(c['key']) == key and canon(c['value']) == value
                and c['status'] in ('claim', 'fact', 'conflicted')]
        rank = 2 if len({(store['sources'][s]['host'],
                          store['sources'][s]['page_id'])
                         for s in srcs}) > 1 else 1
        store['facts'][key] = {
            'value': r['value'], 'origin': 'promoted', 'rank': rank,
            'source': '+'.join(sorted(set(srcs)))}
        committed = True
        verdicts[i] = 'PROMOTED'

    if committed:
        store['gen_next'] = gid + 1
        store.setdefault('generations', []).append(gid)
        gen_out = gid
    else:
        gen_out = 0
    # stable claim order: canonical by id number
    store['claims'].sort(key=lambda c: int(c['id'].split('-')[1]))
    return store, {'verdicts': verdicts, 'generation': gen_out}


def rollback(store, gid):
    """Inverse generation: deactivate exactly the claims generation gid
    introduced, restore what it tombstoned, drop facts that no longer
    have an active claim, and re-derive conflicted marks. Records are
    never physically deleted; history is preserved."""
    store = json.loads(json.dumps(store))
    affected = [c for c in store['claims'] if c['generation_id'] == gid]
    # restore tombstones this generation created
    superseded_ids = {c.get('superseded_by') for c in store['claims']}
    for c in store['claims']:
        if c['status'] == 'tombstoned' and c.get('superseded_by') in \
                {a['id'] for a in affected}:
            c['status'] = 'fact'
            c['superseded_by'] = ''
    for c in affected:
        c['status'] = 'rolled-back'
    if gid in store.get('generations', []):
        store['generations'].remove(gid)
    # re-derive facts from remaining active fact-claims
    active = [c for c in store['claims'] if c['status'] in
              ('fact', 'conflicted')]
    keep = {}
    conflicted_keys = set()
    by_key = {}
    for c in active:
        by_key.setdefault(canon(c['key']), []).append(c)
    for key, cs in by_key.items():
        values = {canon(c['value']) for c in cs}
        if len(values) > 1:
            conflicted_keys.add(key)
        for c in cs:
            keep.setdefault(key, {})[canon(c['value'])] = \
                keep.get(key, {}).get(canon(c['value']), []) + [c]
    new_facts = {}
    for key, fact in store['facts'].items():
        if fact['origin'] == 'taught':
            new_facts[key] = fact
    # rebuild promoted facts from the remaining active claims
    for key, vals in keep.items():
        if key in new_facts:
            continue
        first = sorted((cs[0] for cs in vals.values()),
                       key=lambda c: int(c['id'].split('-')[1]))[0]
        srcs = sorted({c['source_id'] for cs in vals.values()
                       for c in cs})
        rank = 2 if len({(store['sources'][sid]['host'],
                          store['sources'][sid]['page_id'])
                         for sid in srcs}) > 1 else 1
        fact = {'value': first['value'], 'origin': 'promoted',
                'rank': rank, 'source': '+'.join(srcs)}
        if key in conflicted_keys:
            fact['status'] = 'conflicted'
        new_facts[key] = fact
    for c in active:
        c['status'] = 'conflicted' if canon(c['key']) in conflicted_keys \
            else 'fact'
    store['facts'] = new_facts
    return store


def check_case(case, default_policy):
    policy = dict(default_policy)
    policy.update(case.get('policy', {}))
    store = case['store']
    store.setdefault('gen_next',
                     max([c.get('generation_id', 0)
                          for c in store.get('claims', [])] + [0]) + 1)
    out, report = promote(store, case['batch'], policy)
    exp = case['expect']
    errors = []
    if report['verdicts'] != exp['verdicts']:
        errors.append('verdicts: got %s want %s' %
                      (report['verdicts'], exp['verdicts']))
    if report['generation'] != exp['generation']:
        errors.append('generation: got %s want %s' %
                      (report['generation'], exp['generation']))
    if len(out['claims']) != exp['claims_count']:
        errors.append('claims_count: got %d want %d' %
                      (len(out['claims']), exp['claims_count']))
    for key, want in exp.get('facts', {}).items():
        got = out['facts'].get(canon(key))
        if got is None:
            errors.append('fact missing: %s' % key)
            continue
        for f, v in want.items():
            gv = got.get(f, [] if f == 'dissent' else None)
            if f == 'value':
                gv = canon(got['value'])
                v = canon(v)
            if gv != v:
                errors.append('fact %s.%s: got %r want %r' %
                              (key, f, gv, v))
    for key in set(out['facts']) - {canon(k) for k in exp.get('facts', {})}:
        errors.append('unexpected fact: %s' % key)
    for cid in exp.get('tombstoned', []):
        rec = [c for c in out['claims'] if c['id'] == cid]
        if not rec or rec[0]['status'] != 'tombstoned':
            errors.append('not tombstoned: %s' % cid)
    for entry in exp.get('claim_order', []):
        cid, key = entry.split(':', 1)
        rec = [c for c in out['claims'] if c['id'] == cid]
        if not rec or canon(rec[0]['key']) != canon(key):
            errors.append('claim order: %s is not %s' % (cid, key))
    rb = exp.get('rollback_generation')
    if rb is not None:
        out2 = rollback(out, rb)
        want_facts = {canon(k): v for k, v in
                      exp.get('facts_after_rollback', {}).items()}
        if set(out2['facts']) != set(want_facts):
            errors.append('after rollback facts: got %s want %s' %
                          (sorted(out2['facts']), sorted(want_facts)))
        for key, want in want_facts.items():
            got = out2['facts'][key]
            for f, v in want.items():
                gv = got.get(f)
                if f == 'value':
                    gv, v = canon(gv), canon(v)
                if gv != v:
                    errors.append('after rollback fact %s.%s: got %r '
                                  'want %r' % (key, f, gv, v))
        n_active = len([c for c in out2['claims']
                        if c['status'] != 'rolled-back'])
        if 'active_claims_after_rollback' in exp and \
                n_active != exp['active_claims_after_rollback']:
            errors.append('active claims after rollback: got %d want %d'
                          % (n_active,
                             exp['active_claims_after_rollback']))
    return errors


def main():
    data = json.load(open('tests/claims/fixtures-w1.json',
                          encoding='utf-8'))
    fails = 0
    for case in data['cases']:
        errors = check_case(case, data['policy'])
        if errors:
            fails += 1
            print('FAIL %s' % case['name'])
            for e in errors:
                print('  ' + e)
        else:
            print('ok   %s' % case['name'])
    print('%d/%d passed' % (len(data['cases']) - fails, len(data['cases'])))
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
