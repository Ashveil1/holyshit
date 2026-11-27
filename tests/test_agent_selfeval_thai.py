#!/usr/bin/env python3
"""A23.3 Thai dataset format check: owner path (T-SE16) + thai-core
AI-authored path (spec v2.5, GPT GO 26 Nov). ASCII placeholders only:
the checker validates structure and evidence, it creates no labels."""
import copy, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests'))
from test_agent_shadow import run

TEMPLATE = ROOT / 'tests' / 'selfeval' / 'thai-core-v1.pending.json'
CORPUS_TPL = ROOT / 'tests' / 'selfeval' / 'thai-core-v1.corpus.pending.json'
CATS = ['recall', 'unknown', 'contradiction', 'ambiguity', 'teach',
        'forget', 'correction']
L = {'epistemic': 'supported', 'action': 'answer'}
LB2 = {'epistemic': 'unknown', 'action': 'abstain'}
AMB = {'epistemic': 'ambiguous', 'action': 'clarify'}
DISC = ('confirmed under delegated owner authority - reviewer NOT '
        'independent of the annotating families')


# ---------------- owner path (inline base; the file template is AI now)
OWNER_BASE = {
    'id': 'thai-core', 'version': 1, 'kind': 'thai-dataset', 'lang': 'th',
    'tier': 'supported', 'status': 'PENDING_OWNER_LABELING', 'note': 'x',
    'provenance': {'method': 'owner-authored', 'author': 'owner'},
    'acceptance_criteria': {c: 'criterion' for c in CATS}, 'items': []}


def item(i, cat='recall', crit=False, ann=None, adj=None, origin='authored'):
    return {'id': i, 'category': cat, 'input': 'placeholder-' + i,
            'origin': origin, 'critical': crit,
            'annotations': ann if ann is not None else [],
            'adjudication': adj or {'state': 'none'}}


def A(n, lb=L, role='independent'):
    return {'annotator': n, 'role': role, 'label': lb}


# ---------------- AI path builders
def ai_base():
    return {
        'id': 'thai-core', 'version': 1, 'kind': 'thai-dataset',
        'lang': 'th', 'tier': 'supported', 'status': 'AI_AUTHORED_REVIEW',
        'annotation_variant': 'A', 'note': 'x',
        'provenance': {
            'method': 'ai-authored', 'human_validated': False,
            'authors': [
                {'author_id': 'claude-author-01', 'family': 'claude',
                 'model': 'm', 'version': 'unavailable',
                 'session_date': '2026-11-26'},
                {'author_id': 'gpt-author-01', 'family': 'gpt',
                 'model': 'm', 'version': 'unavailable',
                 'session_date': '2026-11-26'}],
            'annotators': [
                {'annotator_id': 'gpt-annotator-01', 'family': 'gpt',
                 'model': 'm', 'version': 'unavailable'},
                {'annotator_id': 'gemini-annotator-01', 'family': 'gemini',
                 'model': 'm', 'version': 'unavailable'},
                {'annotator_id': 'claude-annotator-02', 'family': 'claude',
                 'model': 'm', 'version': 'unavailable'}],
            'annotation_sessions': [],
            'criteria_version': 'cv1', 'variation_plan_hash': 'vph'},
        'corpus': {'file': 'thai-core-v1.corpus.pending.json',
                   'sha256': '', 'note': 'n'},
        'acceptance_criteria': {c: 'criterion' for c in CATS},
        'items': [], 'evidence': {'annotation_log': []}}


def sess(sid, ann, batch='b1', resume=None, pth='1' * 64):
    return {'session_id': sid, 'annotator_id': ann,
            'session_date': '2026-11-26', 'batch_id': batch,
            'resume_of': resume, 'displayed_model_label': 'Gemini',
            'prompt_template_hash': pth, 'item_order_seed': 'seed'}


def annrec(aid, item_id, s, label, role=None, turn=1):
    r = {'annotation_id': aid, 'item_id': item_id, 'batch_id': s['batch_id'],
         'turn': turn,
         'session_id': s['session_id'], 'annotator_id': s['annotator_id'],
         'criteria_version': 'cv1',
         'prompt_template_hash': s['prompt_template_hash'],
         'timestamp': '2026-11-26T00:00:00Z', 'label': label,
         'rationale': 'r', 'response_hash': '2' * 64}
    if role:
        r['role'] = role
    return r


def ai_item(i, cat='recall', crit=False, by='claude-author-01',
            prog='pending', ids=(), disp=None, reason=None, turns=(1,),
            amb=False):
    it = {'id': i, 'category': cat, 'origin': 'authored',
          'authored_by': by, 'ai_authored': True,
          'not_human_validated': True, 'annotation_progress': prog,
          'annotation_ids': list(ids), 'scored_turns': list(turns)}
    if crit is not None:
        it['critical'] = crit
    if amb is not None:
        it['ambiguous'] = amb
    if disp is not None:
        it['disposition'] = disp
    if reason is not None:
        it['unresolved_reason'] = reason
    return it


def attestation(head='c' * 64):
    att = {f: 'a' * 64 for f in
           ['manifest_hash', 'corpus_hash', 'ledger_head_hash',
            'variation_plan_hash', 'criteria_hash', 'session_log_hash',
            'annotation_log_hash', 'raw_responses_hash',
            'overlap_report_hash', 'prompt_templates_hash',
            'harness_build_hash']}
    att['ledger_head_hash'] = head
    att['anchor'] = {'repo': 'Ashveil1/holyshit', 'commit': 'a' * 40}
    return att


def ledger_ok(n=2):
    out = []
    prev = 'a' * 64
    for i in range(n):
        out.append({'item_id': 'x1', 'defect_class': 'duplicate',
                    'evidence_ref': 'ev', 'reviewer': 'gpt-reviewer',
                    'reviewer_family': 'gpt', 'disclosure': DISC,
                    'date': '2026-11-26', 'prev_entry_hash': prev,
                    'entry_hash': chr(ord('b') + i) * 64})
        prev = chr(ord('b') + i) * 64
    return out


def overlap_ok():
    return {'dev_set_hash': 'd' * 64, 'overlap_checker_hash': 'c' * 64,
            'tokenizer_hash': '4' * 64, 'dictionary_hash': 'e' * 64,
            'normalization_config': 'nfc-ws-case',
            'sequence_algorithm': 'lev1', 'min_meaningful_length': 5,
            'thresholds': 'j0.80/0.95',
            'note': 'operational thresholds, not proven '
                    'semantic-duplicate detection'}


def preflight_ok(outcome='pass', tm=4):
    return {'category': 'recall', 'usable_examples': 5,
            'structural_pass': 5, 'instruction_pass': 5,
            'task_matches': tm, 'reviewers': ['claude', 'gpt'],
            'outcome': outcome}


def full_suite(status='AI_AUTHORED_REVIEW'):
    """Three complete items: scored, disagreement, critical-agreement."""
    s = ai_base()
    s['status'] = status
    sg = sess('s-g', 'gpt-annotator-01', 'b1')
    sm = sess('s-m', 'gemini-annotator-01', 'b2')
    s['provenance']['annotation_sessions'] = [sg, sm]
    s['evidence']['annotation_log'] = [
        annrec('an1', 'x1', sg, L), annrec('an2', 'x1', sm, L),
        annrec('an3', 'x2', sg, L), annrec('an4', 'x2', sm, LB2),
        annrec('an5', 'x3', sg, L), annrec('an6', 'x3', sm, L)]
    s['items'] = [
        ai_item('x1', prog='complete', ids=['an1', 'an2'], disp='scored'),
        ai_item('x2', prog='complete', ids=['an3', 'an4'],
                disp='unresolved', reason='annotator-disagreement'),
        ai_item('x3', crit=True, prog='complete', ids=['an5', 'an6'],
                disp='unresolved', reason='no-independent-adjudicator')]
    return s


def frozen_suite():
    s = full_suite(status='AI_AUTHORED_CONTENT_FROZEN')
    s['evidence']['preflight_log'] = [preflight_ok()]
    s['evidence']['overlap_report'] = overlap_ok()
    s['evidence']['exclusion_ledger'] = []
    s['evidence']['freeze_attestation'] = attestation()
    return s


def suite(label, argv, env):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        def chk(suite_obj, name='t.json'):
            (td / name).write_text(json.dumps(suite_obj))
            return run(argv, ['selfeval thai-check ' + name, 'quit'], td,
                       env)

        def ok_ai(s, msg):
            o = chk(s)
            assert msg in o, (msg, o)
            return o

        def bad_ai(s, msg):
            o = chk(s)
            assert msg in o, (msg, o)
            assert 'READY_FOR_CONTENT_FREEZE' not in o
            assert 'CONTENT_FROZEN: evidence complete' not in o

        # ---------- templates
        tpl = json.loads(TEMPLATE.read_text())
        o = chk(tpl, 'tpl.json')
        assert 'AI-authored / not human-validated' in o, o
        assert 'AI_AUTHORED_DRAFT: no items yet' in o, o
        assert 'NEVER a quality claim' in o
        assert tpl['corpus']['file'] == 'thai-core-v1.corpus.pending.json'
        json.loads(CORPUS_TPL.read_text())
        assert 'UTF-8 data artifact' in \
            json.loads(CORPUS_TPL.read_text())['note']
        # a Thai dataset is still not a runnable suite
        o = run(argv, ['selfeval run tpl.json', 'quit'], td, env)
        assert 'suite refused' in o

        # ---------- owner path (unchanged semantics)
        def chk_owner(items=None, **kw):
            s = copy.deepcopy(OWNER_BASE)
            if items is not None:
                s['items'] = items
            s.update(kw)
            return chk(s)

        o = chk_owner([])
        assert 'status PENDING_OWNER_LABELING' in o
        ok = [item('a1', ann=[A('p1'), A('p2')], adj={'state': 'agreed'}),
              item('a2', ann=[A('p1'), A('p2', AMB)], crit=True,
                   adj={'state': 'adjudicated', 'by': 'judge',
                        'final': AMB}),
              item('a3')]
        o = chk_owner(ok)
        assert 'recall: 2 resolved of 3 items TOO_FEW_TO_JUDGE' in o, o
        assert '1 unresolved item(s), 0 problem(s)' in o
        ok[2] = item('a3', ann=[A('p1'), A('p2')], adj={'state': 'agreed'})
        assert 'READY_TO_FREEZE' in chk_owner(ok)

        def bad_owner(it, msg, **kw):
            o = chk_owner([it], **kw)
            assert msg in o, (msg, o)
            assert 'READY_TO_FREEZE' not in o

        bad_owner(item('t1', origin='translated'),
                  't1: translated items are not')
        bad_owner(item('t4', ann=[A('p1')], adj={'state': 'agreed'}),
                  't4: agreed needs two distinct annotators')
        bad_owner(item('t7', crit=True, ann=[A('p1'), A('p2')],
                       adj={'state': 'agreed'}),
                  't7: critical or ambiguous items need an adjudicator')
        bad_owner(item('t9', ann=[A('p1'), A('p2', AMB)],
                       adj={'state': 'adjudicated', 'by': 'p1',
                            'final': L}),
                  't9: the adjudicator cannot be one of the annotators')
        assert 'tier must be' in chk_owner([], tier='future')
        assert 'owner-authored or owner-real' in chk_owner(
            [], provenance={'method': 'synthetic', 'author': 'x'})

        # ---------- AI path: happy flows
        s = full_suite()
        o = ok_ai(s, 'READY_FOR_CONTENT_FREEZE')
        assert 'variant A' in o
        assert 'recall: 1 scored of 3 items, 2 unresolved' in o, o
        o = ok_ai(frozen_suite(), 'CONTENT_FROZEN: evidence complete')
        assert 'execution eligibility is a separate external record' in o
        # a pending item is fine before freeze
        s = full_suite()
        s['items'].append(ai_item('x4'))
        o = ok_ai(s, '1 pending/partial item(s), 0 problems')
        # variant B: one independent + agreeing author-self review
        s = ai_base()
        s['annotation_variant'] = 'B'
        s['provenance']['single_independent_annotator'] = True
        sg = sess('s-g', 'gpt-annotator-01', 'b1')
        sc = sess('s-c', 'claude-annotator-02', 'b2')
        s['provenance']['annotation_sessions'] = [sg, sc]
        s['evidence']['annotation_log'] = [
            annrec('an1', 'x1', sg, L),
            annrec('an2', 'x1', sc, L, role='author-self')]
        s['items'] = [ai_item('x1', prog='complete', ids=['an1', 'an2'],
                              disp='scored')]
        ok_ai(s, 'READY_FOR_CONTENT_FREEZE')

        # ---------- AI path: refusals and problems (spec section 9)
        s = ai_base()
        del s['provenance']['human_validated']
        bad_ai(s, 'human_validated must be the literal false')
        s = ai_base()
        s['provenance']['human_validated'] = True
        bad_ai(s, 'human_validated must be the literal false')
        s = ai_base()
        s['status'] = 'PENDING_OWNER_LABELING'
        bad_ai(s, 'status invalid for the AI-authored path')
        # same-family annotator via DIFFERENT session ids
        s = full_suite()
        sc = sess('s-c', 'claude-annotator-02', 'b3')
        s['provenance']['annotation_sessions'].append(sc)
        s['evidence']['annotation_log'][1] = annrec('an2', 'x1', sc, L)
        bad_ai(s, 'must never annotate its own item')
        # two annotations from one family
        s = full_suite()
        s['provenance']['annotators'].append(
            {'annotator_id': 'gpt-annotator-02', 'family': 'gpt',
             'model': 'm', 'version': 'unavailable'})
        sg2 = sess('s-g2', 'gpt-annotator-02', 'b3')
        s['provenance']['annotation_sessions'].append(sg2)
        s['evidence']['annotation_log'][1] = annrec('an2', 'x1', sg2, L)
        bad_ai(s, 'must come from distinct families')
        # scoring a partial item
        s = ai_base()
        sg = sess('s-g', 'gpt-annotator-01')
        s['provenance']['annotation_sessions'] = [sg]
        s['evidence']['annotation_log'] = [annrec('an1', 'x1', sg, L)]
        s['items'] = [ai_item('x1', prog='partial', ids=['an1'],
                              disp='scored')]
        bad_ai(s, 'becomes scored only from complete')
        # progress mismatch
        s['items'] = [ai_item('x1', prog='complete', ids=['an1'],
                              disp='scored')]
        bad_ai(s, 'does not match 1 annotation record(s)')
        # disagreement declared scored
        s = full_suite()
        s['items'][1]['disposition'] = 'scored'
        del s['items'][1]['unresolved_reason']
        bad_ai(s, 'disposition must be unresolved')
        # critical/ambiguous: no-independent-adjudicator even on agreement
        s = full_suite()
        s['items'][2]['disposition'] = 'scored'
        del s['items'][2]['unresolved_reason']
        bad_ai(s, 'x3: disposition must be unresolved')
        s = full_suite()
        s['items'][2]['unresolved_reason'] = 'annotator-disagreement'
        bad_ai(s, 'unresolved_reason must be no-independent-adjudicator')
        # ---- spec 4.4 A': label value is scored content, never a trigger
        # agreed (ambiguous, clarify) label, no item flag -> SCORED
        # (regression test for the dropped label trigger)
        s = full_suite()
        s['evidence']['annotation_log'][0]['label'] = AMB
        s['evidence']['annotation_log'][1]['label'] = AMB
        o = ok_ai(s, 'READY_FOR_CONTENT_FREEZE')
        assert 'recall: 1 scored of 3 items, 2 unresolved' in o, o
        assert 'problem:' not in o, o
        # declared ambiguous flag, both annotators agree ->
        # unresolved no-independent-adjudicator (even on agreement)
        s = full_suite()
        s['items'][0]['ambiguous'] = True
        s['items'][0]['disposition'] = 'unresolved'
        s['items'][0]['unresolved_reason'] = 'no-independent-adjudicator'
        o = ok_ai(s, 'recall: 0 scored of 3 items, 3 unresolved')
        assert 'problem:' not in o, o
        s = full_suite()
        s['items'][0]['ambiguous'] = True
        bad_ai(s, 'x1: disposition must be unresolved')
        # ---- A' per-(id, turn) rollup
        # multi-turn item: one pair disagrees -> unresolved
        sg = sess('s-g', 'gpt-annotator-01', 'b1')
        sm = sess('s-m', 'gemini-annotator-01', 'b2')
        s = ai_base()
        s['provenance']['annotation_sessions'] = [sg, sm]
        s['evidence']['annotation_log'] = [
            annrec('a1', 'm1', sg, L), annrec('a2', 'm1', sm, L),
            annrec('a3', 'm1', sg, L, turn=2),
            annrec('a4', 'm1', sm, LB2, turn=2)]
        s['items'] = [ai_item('m1', prog='complete',
                              ids=['a1', 'a2', 'a3', 'a4'], turns=(1, 2),
                              disp='unresolved',
                              reason='annotator-disagreement')]
        ok_ai(s, 'recall: 0 scored of 1 items, 1 unresolved')
        # multi-turn item: one pair missing a record -> partial, never
        # scored
        s = ai_base()
        s['provenance']['annotation_sessions'] = [sg, sm]
        s['evidence']['annotation_log'] = [
            annrec('a1', 'm1', sg, L), annrec('a2', 'm1', sm, L),
            annrec('a3', 'm1', sg, L, turn=2)]
        s['items'] = [ai_item('m1', prog='partial', ids=['a1', 'a2', 'a3'],
                              turns=(1, 2))]
        o = ok_ai(s, '1 pending/partial item(s), 0 problems')
        s['items'][0]['annotation_progress'] = 'complete'
        bad_ai(s, 'does not match 3 annotation record(s); expected '
                  'partial')
        # duplicate record on one (id, turn) pair -> problem
        s = ai_base()
        s['provenance']['annotation_sessions'] = [sg, sm]
        s['evidence']['annotation_log'] = [
            annrec('a1', 'm1', sg, L), annrec('a2', 'm1', sm, L),
            annrec('a5', 'm1', sg, L)]
        s['items'] = [ai_item('m1', prog='complete', ids=['a1', 'a2', 'a5'],
                              disp='scored')]
        bad_ai(s, 'duplicate annotation records on (item, turn) 1')
        # legacy item without flag fields -> no declared flag
        s = ai_base()
        s['provenance']['annotation_sessions'] = [sg, sm]
        s['evidence']['annotation_log'] = [
            annrec('a1', 'm1', sg, L), annrec('a2', 'm1', sm, L)]
        it = ai_item('m1', prog='complete', ids=['a1', 'a2'],
                     crit=None, amb=None, disp='scored')
        assert 'critical' not in it and 'ambiguous' not in it
        s['items'] = [it]
        ok_ai(s, 'recall: 1 scored of 1 items')
        # a record on an undeclared turn is never silently ignored
        s['evidence']['annotation_log'].append(
            annrec('a9', 'm1', sg, L, turn=7))
        s['items'][0]['annotation_ids'].append('a9')
        bad_ai(s, 'turn 7 which scored_turns does not declare')
        # ledger: append-only chain + tamper detection
        s = frozen_suite()
        s['evidence']['exclusion_ledger'] = ledger_ok(2)
        ok_ai(s, 'CONTENT_FROZEN: evidence complete')
        s = frozen_suite()
        led = ledger_ok(2)
        led[1]['prev_entry_hash'] = '9' * 64
        s['evidence']['exclusion_ledger'] = led
        bad_ai(s, 'exclusion ledger chain broken')
        s = frozen_suite()
        led = ledger_ok(1)
        led[0]['defect_class'] = 'semantic-dispute'
        s['evidence']['exclusion_ledger'] = led
        bad_ai(s, 'objective defect classes only')
        s = frozen_suite()
        led = ledger_ok(1)
        led[0]['defect_class'] = 'wrong-category'
        led[0]['evidence_ref'] = ''
        s['evidence']['exclusion_ledger'] = led
        bad_ai(s, 'wrong-category needs evidence_ref')
        s = frozen_suite()
        led = ledger_ok(1)
        del led[0]['disclosure']
        s['evidence']['exclusion_ledger'] = led
        bad_ai(s, 'literal delegated-authority label')
        # attestation coverage
        s = frozen_suite()
        del s['evidence']['freeze_attestation']['corpus_hash']
        bad_ai(s, 'corpus_hash missing or not 64-hex')
        s = frozen_suite()
        del s['evidence']['freeze_attestation']['anchor']['commit']
        bad_ai(s, 'anchor needs repo + 40-hex git commit')
        # duplicate annotator identity
        s = ai_base()
        s['provenance']['annotators'].append(
            {'annotator_id': 'gpt-annotator-01', 'family': 'gpt',
             'model': 'm', 'version': 'unavailable'})
        bad_ai(s, 'duplicate annotator identity gpt-annotator-01')
        # preflight evidence shape
        s = full_suite()
        pf = preflight_ok()
        pf['usable_examples'] = 4
        s['evidence']['preflight_log'] = [pf]
        bad_ai(s, 'exactly 5 usable examples')
        s = full_suite()
        s['evidence']['preflight_log'] = [preflight_ok(tm=3)]
        bad_ai(s, 'outcome pass requires 5 usable, 5/5 structural, '
                  '5/5 instruction, >=4/5 task match')
        s = full_suite()
        pf = preflight_ok()
        pf['reviewers'] = ['claude']
        s['evidence']['preflight_log'] = [pf]
        bad_ai(s, 'the two preflight reviewers are the claude and gpt '
                  'families')
        # fail-pending-reassessment is a valid structural outcome
        s = full_suite()
        s['evidence']['preflight_log'] = [
            preflight_ok(outcome='fail-pending-reassessment', tm=2)]
        ok_ai(s, 'READY_FOR_CONTENT_FREEZE')
        # content freeze gating
        s = frozen_suite()
        s['items'].append(ai_item('x9'))
        bad_ai(s, 'content freeze refused: 1 item(s) not complete')
        s = full_suite(status='AI_AUTHORED_CONTENT_FROZEN')
        bad_ai(s, 'content freeze refused: overlap report missing')
        # misc provenance and item rules
        s = full_suite()
        s['items'][0]['authored_by'] = 'nobody'
        bad_ai(s, 'declared authors.author_id')
        s = full_suite()
        del s['items'][0]['ai_authored']
        bad_ai(s, 'ai_authored must be the literal true')
        s = full_suite()
        s['items'][0]['input'] = 'content in the wrong place'
        bad_ai(s, 'never in the manifest')
        s = full_suite()
        s['items'][0]['annotation_ids'] = ['ghost']
        bad_ai(s, 'unknown annotation id ghost')
        s = full_suite()
        s['provenance']['annotation_sessions'][0]['resume_of'] = 'ghost'
        bad_ai(s, 'resume_of must chain to an earlier session')
        # variant B rules
        s = ai_base()
        s['annotation_variant'] = 'B'
        bad_ai(s, 'single_independent_annotator')
        s = ai_base()
        s['annotation_variant'] = 'B'
        s['provenance']['single_independent_annotator'] = True
        sg = sess('s-g', 'gpt-annotator-01', 'b1')
        sc = sess('s-c', 'claude-annotator-02', 'b2')
        s['provenance']['annotation_sessions'] = [sg, sc]
        s['evidence']['annotation_log'] = [
            annrec('an1', 'x1', sg, L),
            annrec('an2', 'x1', sc, LB2, role='author-self')]
        s['items'] = [ai_item('x1', prog='complete', ids=['an1', 'an2'],
                              disp='unresolved',
                              reason='annotator-disagreement')]
        ok_ai(s, 'READY_FOR_CONTENT_FREEZE')
        # ---- positive end-to-end: the A' derived view validates CLEAN
        view = json.loads((ROOT / 'tests' / 'selfeval' /
                           'thai-core-ai-v1' /
                           'thai-core-ai-v1.derived-view.json').read_text())
        o = chk(view, 'view.json')
        assert 'CONTENT_FROZEN: evidence complete' in o, o
        assert 'problem:' not in o, o
        for line in ['ambiguity: 8 scored of 10 items, 2 unresolved',
                     'contradiction: 10 scored of 10 items',
                     'correction: 8 scored of 10 items, 2 unresolved',
                     'forget: 9 scored of 10 items, 1 unresolved',
                     'recall: 10 scored of 10 items',
                     'teach: 10 scored of 10 items',
                     'unknown: 8 scored of 10 items, 2 unresolved']:
            assert line in o, (line, o)
        print('ok %s: Thai dataset owner path + thai-core AI-authored '
              'evidence rules' % label)


def main():
    env = dict(os.environ)
    env['HSPATH'] = str(ROOT)
    which = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if which in ('both', 'interp'):
        suite('interp', [sys.executable, str(ROOT / 'interp.py'),
                         str(ROOT / 'agent' / 'repl.holy')], env)
    if which in ('both', 'native'):
        with tempfile.TemporaryDirectory() as td:
            img = Path(td) / 'repl'
            r = subprocess.run([sys.executable, str(ROOT / 'hs.py'),
                                'build', str(ROOT / 'agent' / 'repl.holy'),
                                '-o', str(img)],
                               capture_output=True, text=True, env=env)
            assert r.returncode == 0, r.stderr[-400:]
            suite('native', [str(img)], env)
    print('all agent selfeval thai tests passed')


if __name__ == '__main__':
    main()
