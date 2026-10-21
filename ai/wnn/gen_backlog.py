"""Generates BACKLOG.md: ~500 candidate experiments, ranked cheap-first. Deterministic."""
import itertools
T = []  # (theme, priority, [(method, [tasks], tier, baseline, criterion)])
T.append(('T1 induction-search', 1, [
 ('macro-first ordering from mined step patterns', ['square','choose2','sumsq','dblfact'], 'M', 'P14 ordering, same seed/cap', 'finds same program in <50% tried, or finds one baseline missed'),
 ('mine cond+step macros (not just steps)', ['square','choose2','sumsq'], 'M', 'P14 ordering', 'same as above'),
 ('beam over combs ranked by frequency in learned programs', ['square','choose2'], 'M', 'uniform order', '<50% tried'),
 ('iterative deepening on expression depth (allow depth-2, cost-ordered)', ['absdiff','lcm'], 'L', 'depth-1 6M cap', 'finds a correct program baseline misses'),
 ('simplify-first: prefer programs with fewer nodes on tie', ['all new'], 'S', 'first-found', 'equal accuracy, shorter program, no time loss >10%'),
 ('seed-parallel racing (3 seeds, first hit wins)', ['square','absdiff'], 'M', 'single seed same CPU-min', 'finds with less wall CPU per success'),
 ('example subsampling during search then full check', ['square','choose2'], 'S', 'full-set check every candidate', 'same found programs, <70% time'),
 ('adversarial example generation for acceptance (boundary x=0,1,large)', ['square','even','sumto'], 'S', '25 random examples (P19b)', 'kills wrong-short programs without extra hand labels'),
 ('cache run() traces across candidate programs', ['square'], 'M', 'no cache', '>2x throughput, same result'),
 ('prune combs that type-fail on first example', ['choose2'], 'S', 'no prune', 'same result, <80% time'),
]))
T.append(('T2 library-learning', 2, [
 ('anti-unify pairs of learned programs into partial schemas', ['curriculum8'], 'M', 'no schemas', 'a schema reused by >=2 held-out tasks cuts tried >50%'),
 ('add learned fn as leaf only after 40/40 validation (P20 gate)', ['new skills'], 'S', 'add-if-36/40', 'no skill poisoned by a wrong library entry'),
 ('compress: shortest re-derivation of each learned skill via library', ['curriculum8'], 'S', 'P14 programs', 'total description length drops'),
 ('fragment = depth-2 expression mined from pairs of used depth-1 exprs', ['absdiff'], 'L', 'depth-1', 'absdiff found or honest expressivity proof'),
 ('forget-and-relearn: relearn a skill from library+3 examples', ['mod','gcd'], 'S', 'from-scratch 25 examples', 'found with <=3 examples'),
]))
T.append(('T3 text-to-program', 3, [
 ('it-references: "add 3 and 5 then double it"', ['2-step'], 'M', 'explicit number version', 'acc within 5 pts of explicit'),
 ('3-step with mixed connectors en/th', ['3-step'], 'M', 'P21 same-conn', 'no more than 5 pts below same-conn'),
 ('Thai no-space char model for 2-step', ['2-step th'], 'M', 'spaced Thai', '>=.8 of spaced accuracy'),
 ('active clarification: ask which of top-2 readings (simulated user)', ['1-step unseen'], 'S', 'no clarification', 'acc of k=2 with k=1 + 1 question'),
 ('paraphrase teaching for 2-step glue words', ['new connectors'], 'S', 'P16 .44 baseline', '> .6 on new connectors with 4 definitions'),
 ('learn number words jointly with 2-step (combined stage B)', ['words+2step'], 'L', 'separate stages P16', 'no loss vs separate'),
 ('typing: restrict candidates by arg-count signature', ['all'], 'S', 'no typing', 'same acc, faster fit'),
 ('curriculum: frames ordered by similarity to unseen test frames', ['unseen synonyms'], 'S', 'random order', 'higher acc at n=60'),
 ('digit-free numbers: learn from word-only training', ['words'], 'M', 'P16 mixed', 'report honest acc'),
 ('negative examples: sentences with no op (chit-chat) rejected', ['mixed'], 'S', 'always-answer', 'false-answer rate < 10%, op acc -2 pts max'),
]))
T.append(('T4 baselines+harness', 4, [
 ('MLP baseline harness on every numeric task (sklearn-free, pure py)', ['all numeric'], 'S', 'n/a', 'harness runs, numbers recorded'),
 ('kNN baseline on same features', ['all numeric'], 'S', 'n/a', 'recorded'),
 ('majority/mean baseline', ['all numeric'], 'S', 'n/a', 'recorded'),
 ('chance baselines for yes/no and exact-number answers', ['all'], 'S', 'n/a', 'recorded in README'),
 ('tiny transformer in pure numpy as reference point', ['synonym task'], 'L', 'n/a', 'runs CPU in <2h, acc recorded'),
 ('fixed eval pack v1 frozen for all future comparisons', ['-'], 'S', 'n/a', 'file committed'),
]))
T.append(('T5 weightless/HDC learners', 5, [
 ('WiSARD on MNIST 1-pass vs MLP 1-pass', ['mnist'], 'M', 'MLP baseline', 'within 3 pts, and no forgetting where MLP forgets'),
 ('bloom WiSARD memory scaling', ['mnist'], 'S', 'WiSARD', 'same acc <= half RAM'),
 ('HDC binding for 2-hop inference at 10x facts', ['facts'], 'S', 'P5 T2 numbers', '>= P5 accuracy at 700 facts'),
 ('HDC + program library: recall program by task description', ['12 ops'], 'S', 'random recall', '>90% top-1'),
 ('DWSA/thermometer encoding for numbers in HDC', ['arith'], 'S', 'level encoding', 'better interpolation on unseen operands'),
]))
T.append(('T6 connectome variants (low priority, P5 was negative)', 6, [
 ('connectome reservoir with trained linear readout (ridge, pure py)', ['mnist-1shot'], 'M', 'raw-pixels same readout', 'beats raw or honest null'),
 ('degree/spectral features of wiring as static embeddings', ['mnist'], 'M', 'raw', 'honest null or win'),
 ('STDP on tap circuit with reward gate', ['tap'], 'L', 'no reward', 'learned association > Hebbian P3'),
 ('subsampled connectome (sensory->interneuron core) speed test', ['mnist'], 'S', 'full', '<50% time, <-2 pts acc'),
 ('signed-synapse hand annotation from literature (AIY/AVA signs)', ['tap'], 'M', 'unsigned', '4/4 neurobiology checks'),
]))
T.append(('T7 continual/few-shot', 7, [
 ('class-incremental MNIST 10-class full run, ours vs MLP', ['mnist'], 'M', 'MLP', 'retain >50 pts gap'),
 ('permuted MNIST x5 tasks retention', ['pmnist'], 'M', 'MLP', 'retention gap'),
 ('one-shot per class sweep 1/5/20 examples', ['mnist'], 'S', 'MLP', 'gap at 1 shot'),
 ('few-shot on text intents (SNIPS) vs NB baseline', ['snips'], 'M', 'NB', 'win at <=5 shots'),
 ('episodic recall of named facts after 1000 distractors', ['facts'], 'S', 'no distractors', 'recall unchanged'),
]))
T.append(('T8 neurosymbolic-exact', 8, [
 ('exact chained arithmetic 10x longer than P5 (4750 ops)', ['arith'], 'M', 'P5 475', 'same 100% at 16KB? honest RAM report'),
 ('store-and-derive: transitivity chains depth 10', ['logic'], 'S', 'P5 depth2', 'depth 10 exact'),
 ('mixed radix and negative numbers in HDC arithmetic', ['arith'], 'S', 'positive only', 'exact'),
 ('symbolic unit conversion word problems (template)', ['word problems'], 'M', 'MLP text baseline', 'exact where MLP fails'),
 ('grid transforms: learn 3 ARC-like ops by induction', ['mini-arc'], 'L', 'random search', 'finds 3/3, honest scope note'),
]))
T.append(('T9 test-time-compute analogs', 9, [
 ('self-consistency: run induction on 5 example subsets, vote', ['square','even'], 'S', 'single run', 'kills overfit programs'),
 ('verify-then-accept: learned program must pass fresh random tests', ['all skills'], 'S', 'P20 gate', 'wrong-program rate to ~0'),
 ('search budget as function of example count (adaptive)', ['mod..sumto'], 'S', 'fixed cap', 'same acc less CPU'),
 ('ensemble of learner hypotheses with execution agreement', ['text2prog'], 'S', 'top-1', '+3 pts unseen frames'),
 ('repair: on test failure, resume search from best partial', ['square'], 'M', 'from scratch', 'recovers in <30% extra time'),
]))
T.append(('T10 data efficiency', 10, [
 ('choose training examples to maximize hypothesis pruning', ['mod','mul'], 'S', 'random 25', 'same success with <=15 examples'),
 ('fewest-examples curve for each curriculum skill', ['8 skills'], 'M', '25-example baseline', 'curve in README'),
 ('near-miss examples (answers off by one) value', ['square'], 'S', 'random', 'faster acceptance of correct program'),
 ('duplicate/ambiguous example detection and removal', ['all'], 'S', 'keep all', 'no acc loss, fewer examples'),
 ('cross-seed example-set transfer: do good sets generalize', ['square'], 'S', 'fresh random', 'chosen set helps new seed'),
]))
GRIDS = [
 ('T1 induction-search', 1, 'search cap {cap} tried, comb set {comb}', {'cap': ['1M','3M','6M'], 'comb': ['full','leaf-only','freq-ranked']}, ['square','choose2','sumsq'], 'S', 'P14 default', 'same success, <=60% tried'),
 ('T3 text-to-program', 3, 'features {feat}, credit {credit}, n={n}', {'feat': ['tok','char','tokuni'], 'credit': ['soft','hard'], 'n': ['24','60','150','400']}, ['unseen-frames','unseen-synonyms'], 'S', 'P15 tok-soft numbers', 'higher acc at same n'),
 ('T3 text-to-program', 3, 'bigram {bg}, lowercase {lc}, min-count {mc}', {'bg': ['on','off'], 'lc': ['on'], 'mc': ['1','2','4']}, ['unseen-frames','unseen-synonyms','2-step'], 'S', 'P15 default', 'higher acc at n=150'),
 ('T5 weightless/HDC learners', 5, 'HDC dim {dim}, encoding {enc}', {'dim': ['1k','4k','16k'], 'enc': ['level','thermo','random-proj']}, ['arith','facts','2-hop'], 'S', 'P5 4KB config', 'same acc less RAM or better acc same RAM'),
 ('T7 continual/few-shot', 7, 'readout {ro}, shots {k}', {'ro': ['1nn','centroid','wiSARD'], 'k': ['1','5','20']}, ['mnist','pmnist','snips'], 'M', 'MLP same shots', 'retention/acc gap'),
 ('T9 test-time-compute analogs', 9, 'vote k={k}, subset {frac}', {'k': ['3','5','9'], 'frac': ['0.5','0.8']}, ['square','even','sumto','choose2'], 'S', 'single run', 'wrong-program rate down, success same'),
 ('T2 library-learning', 2, 'macro min-count {mc}, order {ord}', {'mc': ['2','3'], 'ord': ['mine-first','mine-only','interleave']}, ['square','choose2','sumsq','dblfact'], 'M', 'P14 ordering', '<50% tried same success'),
 ('T10 data efficiency', 10, 'selection {sel}, n={n}', {'sel': ['random','maxdisagree','boundary','covering'], 'n': ['5','10','15','25']}, ['mod','mul','square','even'], 'S', 'random 25', 'same success fewer examples'),
 ('T4 baselines+harness', 4, 'baseline {bl}', {'bl': ['mlp','knn','majority','linreg']}, ['square','even','sumto','absdiff'], 'S', 'n/a', 'recorded'),
 ('T8 neurosymbolic-exact', 8, 'HDC chain depth {d}, facts {f}', {'d': ['2','5','10'], 'f': ['70','300','1000']}, ['logic','arith'], 'S', 'P5 numbers', 'exact at larger scale or honest limit'),
]
rows = []
n = 0
for theme, pri, tmpl, axes, tasks, tier, base, crit in GRIDS:
    keys = list(axes); combos = list(__import__('itertools').product(*[axes[k] for k in keys]))
    for c in combos:
        m = tmpl.format(**dict(zip(keys, c)))
        for task in tasks:
            n += 1; rows.append((tier, pri, n, theme, m, task, base, crit))
for theme, pri, items in sorted(T, key=lambda t: t[1]):
    for i, (m, tasks, tier, base, crit) in enumerate(items):
        for task in tasks:
            n += 1
            rows.append((tier, pri, n, theme, m, task, base, crit))
order = {'S': 0, 'M': 1, 'L': 2}
rows.sort(key=lambda r: (order[r[0]], r[1], r[2]))
out = ['# Exploration backlog (generated by gen_backlog.py, deterministic)', '',
 'Ranking: cost tier S (<2 min) before M (<15 min) before L (<2 h), then theme priority.',
 'Every candidate carries its baseline and pre-stated success criterion. Results (including failures) go to README P-sections; mark done in LEDGER.md.', '',
 'Pre-stated global rules: 3+ seeds where stochastic; "promising" = beats its baseline on the stated metric at the stated tolerance; a win over transformers must name the transformer-class baseline actually run (or a published number with the same data/protocol, cited).', '']
tier_name = {'S': 'S (under 2 min)', 'M': 'M (under 15 min)', 'L': 'L (under 2 h)'}
for i, (tier, pri, n0, theme, m, task, base, crit) in enumerate(rows, 1):
    out.append(f'- [ ] B-{i:03d} [{tier_name[tier]}] ({theme}) {m} -- task: {task} -- baseline: {base} -- success: {crit}')
open('BACKLOG.md', 'w').write('\n'.join(out) + '\n')
print(len(rows))
