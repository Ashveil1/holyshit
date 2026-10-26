"""B-558 SEALED held-out probe generator (sealed held-out protocol 2026-10-26):
the 15 probes in b558.py are DEV probes (their baseline behavior was inspected).
Final quality claims come ONLY from this generator's output, materialized and
printed solely at final-eval time by the sealed harness - never read or iterated
against during development. Frozen seed + template family B, whose surface
constructions are disjoint from the dev set's. HONEST LIMIT (recorded): the
template FAMILY is human-authored and visible here, so family-level design bias
is possible; only the realizations (nonce names, template-to-fact assignment,
surface choices) are unseen until the final run. Strongest future validation:
phrasings authored by the requester himself (steering paraphrased)."""
import random

SEED = 55801  # rotated 2026-10-26: mechanism v4 (claim-marker block + multi-entity abstain) changed AFTER the 55800 one-shot eval - per protocol, tuning requires a new recorded evaluation. 55800 result stands in LEDGER for v3.

_SYL = ['มิ','โร','เค','ฟา','ลู','เซ','ทะ','ปิ','เง','จุ','บ๊','ดี','โย','ซ่','ฮิ','เอ']
_ATTR = ['ฝุ่','แจ๊','โถ่','คิ','เล๊','วั','ซิ','โบะ','เฟิ','หยิ','แช่','โต๊ะ','นิ','ผึ','แม๊','จี้']

TEMPLATES_TH = ['อยากรู้ว่า {n} มีอะไร', '{n} น่ะมีอะไรบ้าง', 'ช่วยบอกของ {n} หน่อย',
                'บอกหน่อย {n} มีอะไรกัน', '{n}ถืออะไรอยู่', '{n} มีของอะไร']
TEMPLATES_EN = ['do you know what {n} has', '{n} has what exactly',
                'what stuff does {n} have', 'what belongs to {n}']

def generate(n_facts=12, n_neg=6, n_conflict=4, n_retract=3):
    rng = random.Random(SEED)
    names = rng.sample(_SYL, n_facts)
    attrs = rng.sample(_ATTR, n_facts)
    facts = list(zip(names, attrs))
    templates = TEMPLATES_TH + TEMPLATES_EN
    probes = []
    for i, (n, a) in enumerate(facts):
        t = templates[rng.randrange(len(templates))]
        probes.append(('paraphrase', n, a, t.format(n=n)))
    neg_names = [s for s in _SYL if s not in names][:n_neg]
    for n in neg_names:
        t = templates[rng.randrange(len(templates))]
        probes.append(('unanswerable', n, None, t.format(n=n)))
    # conflict: probe text names N1 but its phrasing shares more surface with N2's attr region
    for i in range(n_conflict):
        n1, n2 = names[i], names[(i + 3) % len(names)]
        a2 = attrs[(i + 3) % len(attrs)]
        probes.append(('conflict', n1, attrs[i], f'{n1} มี {a2} หรือเปล่า มีอะไรอีก', a2))
    retract = [(names[i], attrs[i]) for i in range(n_facts - n_retract, n_facts)]
    return {'facts': facts, 'probes': probes, 'retract': retract}

if __name__ == '__main__':
    import json
    print(json.dumps(generate(), ensure_ascii=False, indent=1))
