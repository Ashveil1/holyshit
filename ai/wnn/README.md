# ai/wnn — weightless neural network in pure holyshit

A WiSARD-family weightless neural network (WNN): no gradients, no floats,
no matrix math. Learning = incrementing integer counters in RAM lookup
tables; inference = table lookups + a vote. Runs entirely on CPU through
the self-reliant `xbuild` backend (own x86-64 codegen, no gcc, no libc).

This is **not** a new architecture: RAM-based weightless networks go back
to 1959 (Aleksander's WISARD: 1980s), with an active research revival
(Differentiable Weightless Networks, ICML 2024; Google's edge-inference WNN).
This directory is an honest, small, fast implementation in hs, not a
research claim.

## digits.holy — handwritten digit classifier (milestone 1)

Dataset: sklearn digits (1,797 images, 8x8, 16 gray levels), held-out 25%
test split (deterministic shuffle, seed 99991). Design: thermometer-4
encoding (thresholds 1/4/8/12), tuple-16 addressing, 4-bank ensemble,
integer count tables with bleaching (threshold sweep to break ties).

Measured on a 1 GB / 2-core sandbox, `hs.py xbuild` native binary:

| stage | time |
|---|---|
| table alloc (42M cells, 461 MB peak RSS) | ~1.05 s |
| train (1,347 images) | ~37 ms |
| inference (450 images) | ~46 ms (~0.1 ms/image) |

Accuracy: **441/450 = 98.0%** held-out.

Reference points on the same dataset (earlier Python prototype, same
75/25 protocol): WNN in Python 97.3% (~35 ms train, ~0.5 ms/image),
logistic regression 96.2%, 3-NN 98.4%, nearest centroid 87.1%.

Known limits: memory is wasteful (640 full 2^16 tables; a hashed or
packed-counter layout would cut it ~4-16x). Shift augmentation was tested
in the Python prototype and *hurt* accuracy, so it is not used.

## Run

```sh
python3 hs.py xbuild ai/wnn/digits.holy -o /tmp/wnn
/tmp/wnn                      # data path defaults to ai/wnn/data/digits.txt
/tmp/wnn path/to/digits.txt   # or pass a path
```

The interpreter (`python3 interp.py ai/wnn/digits.holy`) runs the same
program ~400x slower; use it only to check semantics, not for benchmarks.


## mnist.holy — MNIST (milestone 2)

Full MNIST (60,000 train / 10,000 test, 28x28 gray). Raw-byte thermometer-8
encoding, tuple-14 tables, 4-bank ensemble, U8 counters, capped-count
summation scoring (beat classic bleaching here: 92.6% vs 91.8%).

Measured (1 GB / 2-core sandbox, xbuild binary):

| stage | time | memory |
|---|---|---|
| train 60,000 images | ~30 s | 636 MB peak RSS incl. 280 MB tables + data |
| test 10,000 images | ~5 s | same process |

Accuracy: **92.6%** (9,262/10,000, best config), 92.2-92.6% across nearby
configs (banks 4-6, tuple 14-16). Honest context: classic WiSARD papers
report ~92-96% on MNIST depending on encoding; reaching 97%+ needs known
extensions (Bloom WiSARD, differentiable WNNs, or richer encodings) - those
are future milestones, not claimed here. k-NN gets ~97%, a small CNN ~99%+,
both far heavier at inference/training than this.

Data: `python3 ai/wnn/prepare_mnist.py /path/to/dir` downloads MNIST and
writes the hex-text files; the model is pure hs.

```sh
python3 hs.py xbuild ai/wnn/mnist.holy -o /tmp/mnist
/tmp/mnist mnist_train_raw.txt mnist_test_raw.txt [ntrain] [ntest]
```


## intent.holy — text intent classification (milestone 3)

SNIPS NLU benchmark (7 intents, 2,100 train / 700 test utterances;
`2017-06-custom-intent-engines` split). Weightless classifier: one 2^16
RAM table per class over hashed (FNV-1a) unigram+bigram features, U8
saturating counters, capped-count scoring normalized by class size.
No floats, no embeddings, no gradients.

Measured (xbuild binary): **98.4% (689/700)** with per-feature averaged scoring
(the first cut normalized by class size - that inflates rare classes;
fixed and noted for honesty), train+test together ~10 ms,
tables 458 KB. Context: classical ML baselines on SNIPS-7 sit ~95-97%,
neural SOTA ~98-99% - this is honestly in the classical band.

Data prep: `python3 ai/wnn/prepare_snips.py /path/to/nlu-benchmark-master/2017-06-custom-intent-engines outdir`
(from https://github.com/sonos/nlu-benchmark).

```sh
python3 hs.py xbuild ai/wnn/intent.holy -o /tmp/intent
/tmp/intent snips_train.txt snips_test.txt
```


## chat.holy — tiny conversational demo (milestone 4)

Console REPL: the same weightless classifier over 10 intents (7 smalltalk +
weather/music/restaurant trained on real SNIPS utterances), per-intent
response templates, and an explicit fallback when confidence is low
("I don't know how to answer that yet"). Byte-level input normalization in
`unsafe:` (lowercase, punctuation), zero model floats, 655 KB of tables,
9.2 MB peak RSS total.

Honest limits: this is intent recognition + canned answers, NOT open
conversation. It cannot compose, reason, remember across turns, or answer
outside its 10 intents. Held-out check on the mixed 10-intent set (351
train / 88 test): 86.4%; 97.7% trained on the full set. A ChatGPT-like open
chat at this size is not achievable with published weightless methods -
see the research summary reported separately.

```sh
python3 hs.py xbuild ai/wnn/chat.holy -o /tmp/chat
cd ai/wnn && /tmp/chat    # or: printf 'hello\nquit\n' | /tmp/chat
```


## Brain-inspired phase (P0-P4): the C. elegans connectome in holyshit

- `prepare_connectome.py` / `data/connectome.txt` - real worm wiring
  (Cook et al. 2019, wormwiring.org SI 5): 473 cells, 5914 connections.
- `worm.holy` - graded-neuron simulation of the real circuit. 3/4
  tap-circuit checks match published neurobiology; the 4th (absolute PVC
  dominance) needs synaptic signs EM data does not have (open research).
- `worm_learn.holy` - the circuit as a frozen reservoir + one-pass
  weightless readout + episodic 1-NN memory. Class-incremental MNIST:
  learns 0-4 (95.6%), then 5-8, RETAINS 89.6% of 0-4 (MLP baseline:
  0.0% - catastrophic forgetting). One-shot new class: 66% from ONE
  example (MLP: 0%).
- `worm_plastic.holy`, `worm_spike.holy`, `worm_plastic_mnist.holy` -
  plastic wiring (Hebbian/STDP/STD/GABA signs). Hebbian association
  forms (+18% cross-pathway); spiking variant is bistable (documented
  dead-end); plastic vs frozen wiring head-to-head: accuracy-neutral
  statistically, +8 pts one-shot episodic recall (74%).
- `facts.holy` - hyperdimensional (HDC) one-shot fact memory: 70 facts
  in a fixed 4KB vector, 70/70 recall both directions, no training loop.
- `chat_learn.holy` - the chatbot that LEARNS: "learn: my name -> Ash"
  once, then "what is my name?" or "my name" answers "Ash" forever
  (paraphrase-tolerant, 31 facts tested, 9.4MB RAM).

Honest summary: this system learns in one pass, never catastrophically
forgets, and picks up new facts in one shot - things LLMs cannot do
without retraining. It is NOT smarter than an LLM and does not reason
or generate free text.


## logic.holy / logic_hdc.holy — logic and math (P5)

Question: can training on logic and mathematics "develop the logic" of the
connectome system? Measured answer: **no for learned reasoning, yes for
memory- and symbol-based exact operations** — details below, nothing hidden.

Same machinery as P1: frozen C. elegans reservoir + one-pass weightless
readout, plus an ablation that skips the reservoir (raw encoded bits) and
MLP / lookup baselines (`logic_baseline.py`, same splits, same encodings).
All data is generated programmatically; splits are deterministic.

### E1 — boolean functions, 8-bit inputs (train 188 patterns, held-out 68)

| function | worm+WNN train | worm held-out | raw+WNN train | raw held-out | MLP held-out | lookup held-out |
|---|---|---|---|---|---|---|
| MAJORITY8 (>=4 ones) | 172/188 (91%) | 55/68 (81%) | 188/188 | 61/68 (90%) | 100% | 65% |
| PARITY8 | 118/188 (63%) | 16/68 (24%) | 141/188 (75%) | 0/68 (0%) | 60% | 49% |
| DNF4 (OR of 4 ANDs) | 164/188 (87%) | 56/68 (82%) | 188/188 | 65/68 (96%) | 100% | 68% |

Reading: where input similarity aligns with the target (majority, DNF),
the one-pass readout generalizes. Parity is the classic failure: held-out
accuracy is at/below chance — the readout **anti-generalizes**, because a
pattern's nearest neighbors always have the opposite parity. No local
similarity method can beat this; an MLP barely can (60%).

### E2/E3 — arithmetic and sequence rules: no generalization, for anyone

Addition a+b (a,b in 0..15 -> 31 sums) and next-in-sequence
(given a, a+d predict a+2d mod 32), held-out pairs AND a systematic split
(train a<8, test a>=8; unseen step d=7), one-hot and thermometer encodings:

- held-out accuracy is **0/68, 0/128, 0/59, 0/32 for worm+WNN, raw+WNN AND
  the MLP** (MLP train accuracy: 100%). Lookup baseline: ~1.5% (chance).
- Exact arithmetic from examples is memorization, not rule extraction, for
  every method tested here. Even memorization is imperfect for the WNN:
  42-66% training accuracy on 256 arbitrary pair->sum rows (local 8-bit
  tuples can't isolate the pair interaction), while it memorizes 2-class
  boolean functions at 75-100%.

### E4 — continual logic: learn AND, then OR, then PARITY (retention)

Function selected by 2 extra input bits; each function learned on all 256
patterns, one pass, same tables:

| after learning | WNN (worm and raw): AND | OR | PARITY | MLP: AND | OR | PARITY |
|---|---|---|---|---|---|---|
| AND | 255/256 | - | - | 255/256 | - | - |
| + OR | 255/256 | 255/256 | - | 2/256 (0.8%) | 255/256 | - |
| + PARITY | 255/256 | 255/256 | 132/256 (52%) | 1/256 | 255/256 | 151/256 (59%) |

The standing result holds for logic too: tables never forget (AND survives
two later functions); sequential gradient training destroys AND. Parity
stays hard for both even with full data (WNN random 8-bit tuples rarely
cover exactly the 8 data bits).

### E5 — the symbolic route is exact (logic_hdc.holy, HDC memory)

| test | result |
|---|---|
| T1 arithmetic by chaining: store x->x+1 (0..99), compute a+k by k recalls | 475/475 (100%) |
| T2 transitive inference: store A->B->C->D chains, query A, follow 2 hops | 50/50 (100%) |
| T3 XOR learned one-shot (4 facts, one write each) | 4/4 |
| T4 3-bit parity, 7 of 8 rows stored, query the unseen 8th row | wrong - an unseen row cannot be inferred |

Two honest implementation lessons: commutative XOR binding is ambiguous on
interior chain nodes (a node that is both value and key unbinds to a 50/50
mix; T1 scored 13%, T2 2-hop 60% before the fix); directional
(permutation) binding fixes it (both 100%) at the cost of free reverse
recall. And the symbolic route only ever works for what was stored — T4.

### Conclusion (P5)

The connectome reservoir does not "grow logic" from data — if anything it
blurs small structured inputs (raw beats worm on every E1 row). What the
system genuinely has: (a) one-pass similarity-based generalization where
the function respects similarity, (b) perfect retention across continual
learning, (c) exact symbolic arithmetic/inference through one-shot HDC
chaining — but only over stored relations. This is not reasoning and is
nowhere near LLM competence; it is also not nothing: 475/475 chained
additions on a 16KB fixed memory with one integer-XOR write per fact.

```sh
python3 hs.py xbuild ai/wnn/logic.holy -o /tmp/logic
/tmp/logic ai/wnn/data/connectome.txt      # ~90 s: E1-E4
python3 hs.py xbuild ai/wnn/logic_hdc.holy -o /tmp/logic_hdc
/tmp/logic_hdc                             # ~75 s: T1-T4
python3 ai/wnn/logic_baseline.py           # MLP + lookup baselines
```

## P6: procedures instead of answers (working memory + learned rules)

P5 showed the system memorizes. P6 tests the other route from the survey
(scratchpads, ACT-R style production systems): learn a PROCEDURE and run it
step by step in a working memory, so the answer is computed, not recalled.
Files: `reason.py` (all experiments T1-T5 + baselines, deterministic),
`reason.holy` (native port of the core: add + sub, matches reason.py's
numbers on 1-3 digits and fact counts exactly).

**Given (hand-built):** primitive actions READ / FACT / WRITE / ADV / HALT;
digit tapes (LSB first); the carry abstraction (zero/nonzero) in the policy
observation; the teacher that emits demonstration traces; counting demos
0..9; "add/sub = count forward/back" and "mul = repeated addition" as
derivation procedures; for word problems the sentence template, number
extraction and the verb position. **Learned:** the policy (observation ->
next action, majority vote over trace steps), the (op,x,y,carry) -> (digit,
carry') fact table, and the verb -> operation map. The learning itself is
tabular; nothing here discovers arithmetic from scratch.

Measured (`python3 ai/wnn/reason.py`; native: `hs.py xbuild ai/wnn/reason.holy`):

| test | result |
|---|---|
| T1 held-out digit facts (56/200 unseen) | lookup 0%, MLP 0% (train 100%), + counting derivation 100% |
| T2 add, 200 traces, unseen operand pairs 1-3 digits | 100% |
| T2 length generalization 4/6/10/20/50 digits | 100% (native holy: 300/300 each) |
| T2 baseline direct MLP (3000 pairs) | train 100%, held-out 57%, 4+ digits cannot be encoded |
| T2 baseline gradient step-net inside the same loop | 100% - the structure generalizes, not the WNN |
| demos needed (6-digit acc) | 5 traces 82%, 10 traces 100% with counting; lookup-only needs >200 |
| T3 sub 2-30 digits | 100% (with counting) |
| T3 mul by 1 digit | 100% with repeated-addition derivation; ~86-98% with 8000 traces and no derivation (missing facts) |
| T3 compare | 94-100% only with 8000 traces (300/300 facts stored); no derivation rule, so low with few demos |
| T4 2-step word problems, new names/numbers, seen verbs | 100% (always-add baseline ~25%) |
| T4 unseen verbs (char-trigram nearest neighbour) | 25%, at chance: spelling similarity is not meaning |
| T5 drop carry rule | wrong on 98%; failure iff operands generate a carry (100% predictable) |
| T5 corrupt carry at step k | first wrong digit is k+1 in 87% of cases |

Reading it honestly: it generalizes to unseen operands and to much longer
numbers because the controller is length-free (its observation is local) and
the facts are exact. That is the scratchpad result from the literature
reproduced in a tiny system, and a plain gradient net does equally well once
it is placed in the same loop. What is NOT shown: reasoning, discovering a
new algorithm, general word problems (unseen words fail), or any role for the
connectome reservoir (it is not used; P5 found it does not help logic). The
facts that generalize do so only where a counting/derivation procedure was
given. Not run: grokking-style gradient training with weight decay.

## P7: procedures induced from end-to-end examples (feasibility)

`induce.py` learns step-programs from I/O pairs only (20-40 examples, 1-4 digits): no demo traces, no hand-given READ/FACT/WRITE/ADV/HALT, carry abstraction or derivation rules.
GIVEN: a scan machine (walk the tape, one integer register r, per step output f(x,y,r) and update r=g(x,y,r)) and an arithmetic DSL (+ - * // % < > == min max ite; consts 0 1 2 3 10).
LEARNED by shortest-first enumerative search: read/write direction, output mode, f and g.
Result (unseen inputs, 200 each at 4/6/10/20/50 digits, all 100%): copy, +1/digit, reverse, count of 3s, digit sum, max, parity of sum, add (found f=(x+y+r)%10, g=(x+y+r)//10, i.e. the carry), sub (borrow), compare.
Caveat: with few easy examples the search returns a shorter wrong program (sub 12% at 50 digits, compare ~50%); adversarial examples (borrow chains, prefix ties) fixed both. Search is brute force; programs of size >~9 need ~minutes and more memory. This is program search over a hand-picked DSL, not discovery of primitives.
Run: `python3 induce.py 7 [task ...]` (needs ~1.5 GB RAM).

## P8: library learning over the P7 search (`lib.py`, `lib_run.py`)

Solve base tasks (inc, add, sub) with the raw DSL, mine repeated (op, const) patterns from the solved programs' text (`%10` x3, `//10` x1), add them as primitives that cost +1 over the child, then search again with a smaller bank.
Measured (same 40-example training sets, unseen 4-50 digit tests, all found programs 100%):
- raw bank size<=6: add, sub, mul-by-digit NOT found. Library bank size<=6 (31.8k exprs vs 16.6k): add 0s, sub 29s, mul1 0s, all found.
- Raw size<=7 (76.6k exprs) also finds add (1s), mul1 (1s) and sub (202s). So at this scale the library is a speed/size gain (sub 7x faster), not a new capability.
- Mining is crude (regex over program text, threshold set by hand: with threshold 2 only `%10` was adopted and add was still out of reach; `//10` needed threshold 1).
Not done: searching the skeleton itself (number of registers, loops). Two registers makes the joint search square the cost; not feasible with this enumerator on CPU.

## P9: evolutionary search over K-register machines (`gp.py`)

GIVEN: scan machine, K integer registers (init 0), arithmetic DSL, output mode read off the example shape. LEARNED: directions, per-register update trees, output tree. Fitness = partial credit on end-to-end examples; mutation can wrap a subtree in the mined library ops `%10`/`//10` (P8). Tested on unseen lengths 4/6/10/20/50; "ok" = train-perfect AND >=99% at every length. Seeds are independent runs; 6 seeds x 30,000 evals unless noted (K=1 rows marked * were 8 seeds x 60,000 evals).

| task | K=1 GP | K=3 GP | K=3 random |
|---|---|---|---|
| second_max | 0/6, 0/8* | 3/6 | 0/6 |
| alt_sum (needs position parity) | 3/6, 7/8* | 6/6 | 5/6 |
| count_max | 0/6 | 0/6 | 0/6 |
| count_gt_first | 0/6 | 0/6 | 0/6 |
| max_minus_min | 0/6 | 0/6 | 0/6 |
| add | 0/6, 6/8* | 0/6 | 0/6 |
| sub | 2/6, 3/8* | 1/6 | 0/6 |
| compare | 5/6, 7/8* | 2/6 | 0/6 |
| run_parity | 4/6 | 2/6 | 0/6 |
| mul1 | 0/6 | 0/6 | 0/6 |

Reading: extra registers let GP find tasks one register cannot (second_max 3/6 vs 0/14; alt_sum), and GP beats random search at equal budget. But success rates are modest and noisy: more registers makes already-solvable tasks (add, compare, sub) harder at a fixed budget, and count_max, count_gt_first, max_minus_min, mul1 are not solved at all here. Budgets differ between table cells (see above) so K=1* vs K=3 is not a clean comparison. The exhaustive search in P7/P8 still solves add/sub/compare/mul1 reliably and faster. The scan idea, registers-as-state and the arithmetic DSL are still given; this does not discover them. Not done: learned neural scorer (only the hand-set `%10`/`//10` wrap mutation is used), DSL-ablation sweep.

## P10: learned proposer + curriculum/transfer (`proposer.py`, `exp_prop.py`, `curr.py`)

**Proposer.** Small numpy MLP (43 hand-designed example features -> which ops/constants/leaves the hidden program uses), trained on 20k random synthetic programs, never on the eval tasks. On held-out random programs it is barely better than base rates (logloss 0.548 vs 0.574; strong only for "uses y" and a little for "uses x"/constants), because many ops in random programs are dead code. Used as sampling weights in the GP (K=3, 6 seeds x 20k evals), generalizing solves guided vs unguided: second_max 3/6 vs 3/6, count_max 0 vs 0, max_minus_min 0 vs 0, count_gt_first 0 vs 0, mul1 0 vs 0, alt_sum 5/6 vs 6/6, compare 3/6 vs 2/6, run_parity 1/6 vs 2/6. Net effect: no measurable gain. The features are hand-designed (they encode tasks like sum/max/compare), so even this much is not "learned from scratch".

**Curriculum.** Learn skill A with GP, mine its subtrees (size 3-9) as macros, then learn B with macros available (6 seeds x 20k evals, generalizing solves). Skills learned: sumdigits, max, count3, parity_sum, compare; add and sub FAILED at this budget (so the add -> mul1 chain had 0 macros). Learned skill programs are messy (dead code), so macros are noisy.
- second_max: alone 3/6; after max 4/6 (mean evals 12.4k -> 6.5k); after all skills mixed 5/6.
- alt_sum: alone 6/6; after sumdigits+parity 5/6; mixed 5/6 (slightly worse).
- count_max, max_minus_min, count_gt_first, mul1: 0/6 in every condition.
Reading: a hint of transfer on one task (second_max, builds on max) that is within noise at n=6; no transfer elsewhere. Mixed-task libraries did not connect skills on their own here. Honest conclusion: with this DSL and budget, neither a learned proposer nor curriculum macros produced a clear capability gain; the exhaustive search (P7/P8) remains the reliable component.

## P11: stair-step curriculum with the exhaustive learner (`cur1.py`, `cur2.py`, `cur2_test.py`)

**Level 1: base skills learned from examples (20 different random training sets each, tested 4-50 digits).** lib6 = bank<=6 with mined `%10`/`//10` (P8); raw7 = raw bank<=7.
- add: found 20/20, correct 11/20 (both banks; the other 9 training sets underdetermine the carry, so a validated set must be chosen), mul1 20/20, shift (x10) 20/20, compare 20/20, addmod 20/20 (lib6). raw7: add 11/20, mul1 20/20, shift 20/20 (mean search 1.3s / 0.9s vs 0.5s / 0.4s for lib6). sub: learned from seed 0 (borrow), not run over 20 seeds.

**Level 2: compose the learned procedures** (library: learned add, sub, mul1, shift, compare, run as the induced programs on digit tapes). Level-1 programs used were the first training set passing held-out validation at 4-30 digits. Level-2 search = enumeration of typed compositions over the whole library at once (no hint which skill is needed), fitted on 25 examples of 1-3 digits, then tested on 60 unseen pairs at each of 4/8/15/30 digits:
- |a-b|: `ite(cmp(x,y), sub(x,y), sub(y,x))` found (763 candidates), 60/60 at every length.
- a*b: FOLD over digits of b: `acc <- add(shift(acc), mul1(x,d))` (Horner) found (2502 candidates, 26.7k expressions in the library), 60/60 at every length up to 30x30 digits.
- a mod b (quotient <= 9): `while not cmp(y,acc): acc <- sub(acc,y)` found (439 candidates), 60/60 at every length.
- Ablation (remove one primitive): mul fails without add, without shift, or without mul1; |a-b| fails without ite or without sub; mod fails without sub. Every link of the chain is needed.

**What is still given:** the level-1 scan machine and arithmetic DSL, digit-tape glue (pad, strip, broadcast), the constant [1], `ite`, `not`, and the three loop skeletons (direct, fold over digits of the second number, while-condition). The level-2 program shapes are small (<=6 nodes) because the primitives do the work. Not done: integer division (needs a counter register), a separate test of interleaved training order (the mixed library was searched all at once, not trained in an order), skeleton discovery. Level-2 tasks are impossible for the level-1 search alone (nested loops), so "alone" is not a baseline here; the ablation shows dependence instead.

## P12: level 3 of the curriculum (cur3.py)

Re-learn mul and mod from level 2 (as in P11), then enumerate a two-variable WHILE loop on top of them.
Given: the loop skeleton, inits from {x,y,1}, conditions from cmp/not/0, updates of size <=3 over {add,sub,mul,mod,shift}.
Train on 25 examples; test on 40 unseen per digit length 2/4/6/8.

| task | result | candidates | unseen 2/4/6/8 digits |
|---|---|---|---|
| gcd | FOUND: init (x,y); while cmp(s0,0): s0<-mod(s1,s0); s1<-s0; result s1 (Euclid) | 598k | 40/40 each |
| power | FOUND: init (1,1); while not cmp(s0,y): s0<-s0+1; s1<-mul(s1,x); result s1 | 431k | 40/40 each |

Ablations:
- gcd without mod: NOT FOUND (1.59M candidates, whole space).
- power without mul: NOT FOUND (1.59M candidates, whole space).
- gcd without sub: still found (361k). Caveat: this only removes sub from the top-level loop updates; the learned mod still uses sub inside, so this is not a real ablation of sub. Not re-run with sub removed from level 1.
- Not run: without cmp, level-1-only library.

Honest limits: the scan machine, arithmetic DSL, loop skeletons, constants and glue are still hand-given. The search space is small and hand-picked, so a hit is not surprising once the right pieces exist; the ablations show mod and mul are needed. mod relies on small quotients, there is no division, and the power test exponent range is small (not checked precisely). Search effort is hundreds of thousands of candidates, so this does not scale far.

## P12b: level 4 (cur4.py): div and lcm

- div (quotient <= 9) FOUND by the same loop search with 0 added to the inits: init (y,0); while not cmp(s0,x): s0<-s0+y; s1<-s1+1; result s1. 447k candidates. Unseen 40/40 at 2/4/6/8 digits (quotients <= 9 in the test too).
- gcd re-learned (598k candidates, 40/40).
- lcm: straight-line search over learned {mul, div, gcd}, expressions up to nesting 2. Picked div(mul(x,y), gcd(x,y)) after 139 expressions (the intended composition, from 25 training pairs of 1-2 digits).
- lcm held-out accuracy is poor beyond tiny sizes: 39/40 at 2 digits, 5/40 at 4, 0/40 at 6 and 8. Reason: the learned div only counts up to quotients of 9 (its training range), but lcm needs div(x*y, gcd) with huge quotients. The composition is right; the learned div does not generalise. Fixing it needs a learned long division (nested loop), not done.
- Ablations: lcm without mul, div or gcd: NOT FOUND (62/122/122 expressions, whole space).
- Hand-given as before, plus 0 as an extra init constant.

## P13: S1 basics library + S2 unhinted composition (cur5.py)

S1, learned from examples: max/min (ite over learned cmp, found at once); is-prime: fold over d=2..x-1 with acc<-mul(acc,mod(x,d)), result nonzero(acc) (1605 candidates; 200/200 on unseen x<2000, but only trained on x>=2, so is-prime(1) is wrong, and the product grows to thousands of digits). div, gcd, mul, mod come from P11/P12 (div only for quotients <=9, mod only for modest quotients).
Given: iszero as glue, the loop/fold skeletons, the tape machine, "(x,y)->number" signature.

S2: for each unseen task the system sees only 25 (x,y)->out pairs (1-2 digits). It searches expressions up to depth 2 over all library ops, shortest first, and I test on 40 fresh pairs at 1/2/3 digits.
Result: 6/10 generalise (>=38/40 at every size):
- found: divisible(x by y) = div(gcd(x,y),y); larger-smaller = sub(max,min); larger mod smaller = mod(x+y, min) (equivalent function, not the "natural" form); x^2+y^2; coprime = div(1, gcd(x,y)); gcd+larger. Several are clever equivalents (floor-division tricks), not the textbook program.
- is (x+y) prime: right composition isprime(add(x,y)) chosen, but 35/40 at 3 digits (not diagnosed).
- NOT found / fail: lcm (right composition div(mul,gcd) exists in the space but learned div breaks on large quotients, so it was never consistent with the training pairs); x*x mod y (mod limit); "both prime" (training pairs include x=1, where the learned is-prime is wrong).
- Ablation (library op removed): without gcd 4/10 (coprime lost too), without mod 5/10. without mul 5/10, without max+min 3/10, without div 5/10 (divisible is then found as iszero(mod x y), the textbook form). Caveat: ablation removes an op from the expression grammar only; is-prime still uses mod and mul inside, and the floor-division tricks (coprime = div(1,gcd)) survive when mod/mul go.
Honest limits: this is NOT word problems; the "format" is numeric pairs only. The ops, depth bound, expression grammar and the 0/1 convention are hand-given; the task pool is small and chosen by me; the search is plain enumeration, so "solves problems itself" means "finds a short composition of learned skills that fits the examples". Failures come from learned skills with narrow training ranges.

## P14: learn the loop skeleton itself (cur6.py)

Instead of the hand-given direct / fold / while skeletons of P11-P13, ONE generic linear-recursion schema is searched:
f(a,b) = base if cond(a,b) else comb(a,b, f(step0(a,b), step1(a,b))); answer = post(f(x, init)), init in {y,1,0,2}, post in {id, iszero, nonzero}. Tail loops, counting loops, folds and accumulator loops are instances (comb = identity for tail loops). The search picks cond, base, both step expressions, comb, init and post from 25 examples (1-2 digits). Each learned function enters the library as a new op (curriculum order mod, mul, div, power, gcd, is-prime, factorial, sum-to-n).

Seed 0 (all 8 learned, each 40/40 on unseen at 1,2,3,4 digit scales except where noted):
- mod: if a<b then a else mod(a-b,b) (642 candidates)
- mul: if b<1 then 0 else a+mul(a,b-1) (repeated addition)
- div: if a<b then 0 else 1+div(a-b,b), 40/40 even for LARGE quotients (the quotient<=9 limit of P12b is gone; by-product "long division" but still repeated subtraction, cost O(quotient), not digit-wise)
- power: if b<1 then 1 else a*power(a,b-1) (2.4M candidates)
- gcd: f(a,b) with step (b mod a, a): Euclid, found as a tail loop (60k candidates)
- is-prime: init b=2; if not(b<a) -> a else step (a,b+1); comb val*(a mod b); post nonzero (24.7M candidates; found after the combine order was allowed to be either way)
- factorial: tail loop with accumulator, step (a-1, b*a)
- sum 1..n: tail loop step (a-1, a+b)
Seed 1 (7 tasks without is-prime): all found, 40/40 at all scales except sum-to-n 37/39/40/40 (the found program starts its accumulator at 1 so n=0 is wrong; training set lacked n=0).
Ablations (seed 0): no-combine (tail loops only): mod, gcd, sum-to-n still found; mul, div, power, factorial NOT found (whole space searched). Pair-step off (only one state variable changes per step): mod, mul, div, power, sum-to-n found, gcd NOT found (21.7M candidates, whole space), factorial found but only 32/40 and 34/40 at 3 and 4 digits (a different, weaker program: it is not tail with accumulator, and the mul recursion hits its depth cap). No learned ops in the grammar (only add/sub): mod, mul, div, sum-to-n found; power, gcd, factorial NOT found. So each of the three given-by-search ingredients (combine, two-variable step, library growth) is needed for some skill. Seed 2 (7 tasks without is-prime): all found, 40/40 at every scale.
Honest limits: given are the recursion schema itself (two args, one recursive call), the expression grammar (leaves a,b,1,0 and one binary op), the cond forms, post set, int-level add/sub/lt, curriculum order, the (x,y)->out format. The recursion depth is capped (400 during search, 20000 at test), so learned mul/div are repeated addition/subtraction: correct but slow, and power training values had to stay small for that reason. Search cost is millions of candidates for the later tasks, so it will not scale to longer programs. Some programs have training-range blind spots (sum-to-n at n=0, is-prime at x<2).

## P15: learn simple text commands (English + Thai) -> program (text2prog.py)

Learned from (sentence, answer) pairs only; nobody says which operation a sentence means. For each training pair the learner finds which (op, argument order) hypotheses reproduce the answer, splits credit across them, and learns word / char-n-gram -> hypothesis weights (naive Bayes with soft counts; ambiguity from coinciding numbers is resolved across examples). 12 ops (add sub mul div mod power gcd max min is-prime factorial sum-to-n), 21 hypotheses (op x forward/reverse; "subtract 3 from 10" and "ลบ 3 ออกจาก 10" need the reverse order, which is learned).
Data: per op 4-5 training templates, 4 new-frame templates (same keywords, new wording, extra filler such as "please"/"ช่วย"), 2 new-synonym templates (words never seen), English and Thai mixed. Test numbers are always unseen (31-99 vs 2-30 in training). 5 seeds, mean [min-max], answer accuracy:

| features | n train | unseen numbers | unseen frames | unseen synonyms |
|---|---|---|---|---|
| word tokens + bigrams | 24 / 60 / 150 / 400 | .42 / .78 / .94 / .99 | .43 / .73 / .82 / .84 | .12 / .15 / .20 / .20 |
| char 2-3-grams | 24 / 60 / 150 / 400 | .43 / .77 / .94 / .98 | .42 / .70 / .78 / .77 | .18 / .28 / .41 / .40 |

- Thai written WITHOUT spaces, char n-grams, n=400: unseen frames 0.80 [0.77-0.84], so no tokenizer is needed.
- Unseen frames are the weak point (~0.8): per-op failures are mul 23/55, add 22/50, sub 23/45, mod 34/56, gcd 19/37, min 30/57; the cause is spurious associations (e.g. "what is" / "please" / "ช่วย" were seen with other ops during training), not a bug. max, isprime, power, sumto are perfect.
- Unseen synonyms: ~0.2 (tokens) / ~0.4 (chars) with zero examples, which is near chance and what a lexicon learner should do. Fast mapping: after k labelled examples with the new wording, accuracy is k=1 .89 (tok) / .90 (char), k=2 .97 / .95, k=4 and 8 1.00.
GIVEN: skill library and hypothesis space (op x order, variadic fold), digit extraction by regex, feature extractors, and the templates themselves (my own synthetic sentences, not real user text). NOT covered: number words ("three"), sentences with more structure than one op, multi-step problems, real free text. Accuracy counts the final number matching, so yes/no answers (is-prime) have a high chance baseline.

## P16: number words and two-step sentences (text2prog2.py)

(a) Number WORDS (one..ten, หนึ่ง..สิบ) with values learned, not given. Stage A learns ops from digit sentences (P15 learner, 300 sentences). Stage B sees sentences where number slots are sometimes words; for every token and each value 1..10 it checks whether rewriting that token as that digit reproduces the answer under the stage-A learner (4 rounds, learned words are substituted first so two-word sentences become one-word sentences). Tokens whose vote is clear (>=3 votes, >=25% of their sentences, top value >=2.5x the runner-up) enter the lexicon. 5 seeds, answer accuracy on unseen frames with words:
- n=150 stage-B sentences: 6.8/20 words learned (0.4 spurious entries), accuracy .37
- n=400: 12.4/20 (1.4 spurious), .54
- n=1000: 17.6/20 (1.2 spurious), .74
- reference: gold lexicon .85, no lexicon .18. So the learner closes most of the gap to a hand-written lexicon, but needs ~1000 examples; the spurious entries are real errors.
(b) Two-step sentences ("gcd of 21 and 9 then subtract 11"): the learner sees only (sentence, answer). It explains each sentence by (split point, op1 on the left clause, op2 on the right clause applied to the first result) or by a single op (Occam: single-op explanations win), and learns left-clause words, right-clause words and which token pairs mark a boundary. 5 seeds [min-max]:
- same phrasing: .46 / .64 / .82 with 100 / 300 / 1000 sentences
- new connectors and frames ("after that", "afterwards", "then also ... please"): .25 / .36 / .44
It learns the structure, but the new-phrasing numbers are poor. Errors come from left-clause misreads, wrong cut points inside a single clause, and mixed Thai/English sentences in my own templates.
GIVEN: skill library, hypothesis space (op x order; second-step op over the first result), digit regex, whitespace tokens, the candidate number-word values 1..10, and the templates (synthetic). Not covered: larger numbers as words, three or more steps, real text. Note: factorial is capped at 20 in text2prog.py (an unbounded factorial hung the two-step explanation search).

## P17 (nulls, text2prog3.py)
Three ideas tested, none beat P16: slot-context candidates for number words (no gain), a type-based cut model for two-step sentences (worse: .33/.43/.51 vs .46/.64/.82), and joint explanation of number words (near 0 words learned with my thresholds). P16 stays the baseline.

## P18 (null, text2prog4.py)
EM reweighting of two-step explanations (soft weights from the current model instead of uniform) slightly hurt: same phrasing n=100/300 .46/.64 (no EM) vs .40/.61 (2 iters); new phrasing unchanged (.25/.36 vs .25/.34). The uniform Occam rule of P16 stays.

## P19: skills not in the original curriculum (cur6.py, seed 0 only)
The same generic recursion schema and search (P14), with the learned mod/mul/div/power/gcd in the library, was given 7 new tasks (25 examples each, no hint): absdiff, max, min, square, cube, even, choose2 (x(x-1)/2).
- Found and 40/40 at all 4 scales: max, min, square (reuses learned `power`: power(a,2)), cube (counting loop with learned mul), choose2 (35 s... 480 s search, 3.3M programs).
- even: found but overfit, 38/40 at 1 digit, 26/40 at 4 digits (the program uses power(0,y) as a toggle that fits the 25 examples).
- absdiff: NOT FOUND after 32.6M programs (about 83 min). I did not check whether the grammar can express it.
Caveats: single seed; the schema, cond forms, expression grammar and library order are hand-given; max/min programs are odd (accepted because they pass 40/40 unseen, not because they read naturally); search times are CPU minutes on one core.

## P19b: more seeds (cur6.py)
Full prerequisite library (mod, mul, div, power, gcd learned first) then the new skills, no hints.
- seed 1: max, min 40/40 (min 39/40 at 1 digit), cube 40/40, choose2 40/40, square FOUND BUT WEAK (35/38/39/37 of 40 by scale; the program uses (div a b),(mul a b), which fits the 25 examples but is not x*x), even overfit (37/40/40/27).
- seed 2 (partial, still running when written): max 36/40/40/40 at scales 1-4, min 39/40/40/40, square weak (38/37/38/39). cube, even, choose2 not finished yet.
- absdiff, seed 0 with learned max/min in the library: still NOT FOUND after 36.6M programs (about 5.6 h CPU); the grammar has no depth-2 expression at the base or step, so this is a limit of my hand-given grammar, not evidence the data is hard.
Summary: new skills are learned most reliably when they are a loop over an already learned op (cube, choose2, max, min). Square and even depend on the seed: the search accepts the first program that fits 25 examples, and with weak coverage of the example set a wrong short program wins. A validation step with adversarial examples would be the natural fix (not done here).

## P20: acceptance test with extra labelled examples (cur6.py, ablation `val`, seeds 1 and 2)
The search still takes the first program that fits 25 training examples, but now also requires it to match 32 extra labelled examples (scales 1 and 2, drawn with a different seed than the test set). This is more labelled data (57 examples in total), not a free fix. Whole library re-learned first (mod, mul, div, power, gcd, max, min), then square and even.
- square: seed 1 and seed 2 both found `square = power(a, 2)` (via the learned `power`), 40/40 at scales 1-4. Without the extra examples (P19b) the same seeds gave a wrong program (div a b, mul a b), 35-39/40.
- even: unchanged, same program in both seeds, 37/40/40/27 (seed 1) and 40/40/40/28 (seed 2) at scales 1-4. The failures are only at 4 digits (x up to 30000, where a count-down loop needs more steps than the evaluation cap of 20000), so this is probably a step-cap limit and not a wrong program, but I did not verify that.
- max, min: found in both seeds, 39-40/40.
- Failed first attempt: the first run validated at scale 4 and killed mul (mul by repeated addition exceeds the recursion cap in search), so the search never finished; I restarted with scales 1-2.
- Search cost: square took 2.6 to 3.1 hours CPU (4.3M programs); the library search is unchanged.
Caveats: 2 seeds, hand-given schema/grammar, the validation examples come from the same oracle that labels the training data.

## P21: three-step sentences, zero-shot (text2prog5.py)
Model: the P16 TwoStep model trained ONLY on 1- and 2-step sentences (n=300/1000), no 3-step training sentence. The solver chains it: it tries every pair of cut points, reads the left clause with the op learner, and each later clause with the right-clause learner applied to the previous result, scoring with the learned boundary model.
Answer accuracy on 3-step sentences ("<op> ... then <op2 c> then <op3 c>"), 5 seeds, 200 test sentences each, mean [min-max]:
- same phrasing: n=300 .35 [.20-.58], n=1000 .53 [.46-.62] (the same model reads 2-step sentences at .64 and .82)
- new connectors and frames: .13 and .15
So a model that only saw up to two steps solves about half of the 3-step sentences with the same wording, which is roughly what chaining its 2-step reading accuracy would predict. It does not transfer to new wording. Hand-given: the clause grammar (left clause plus right-clause templates), the op library, the sentence templates (my own synthetic text), whitespace tokens. Answers are exact numbers, so chance is low, but I did not measure a baseline for 3-step. No 'it' references yet. Real free text is not covered.

## P22: teaching a new wording by paraphrase (text2prog6.py)
Zero-shot on new wordings stays weak (P15: .18 tokens, .41 char n-grams on unseen synonyms; P21: .15 for 3 steps), so this tests the cheapest teaching signal: a definition "NEW sentence means KNOWN sentence" (same numbers, no answer given). The learner answers the known side with what it already knows and fits the new side to that pseudo label. Compared with P15 fast mapping (the true answer is given). 3 seeds, 14 unseen-synonym templates, 40 unseen-number test sentences each.
Accuracy on the new wording after k definitions / k labelled answers:
- tokens: k=1 .75 / .83, k=2 .96 / .97, k=4 .96 / .97, k=8 .99 / .99 (k=0: .18)
- char n-grams: k=1 .76 / .83, k=2 .92 / .94, k=4 .93 / .96, k=8 .97 / .99 (k=0: .41)
The pseudo label (the learner's own reading of the known side) was right 91-95% of the time, which is why paraphrase teaching is a little behind answer teaching at k=1 and almost equal at k>=2.
Not shown: any zero-shot gain. A new wording still needs 1-2 examples (by answer or by paraphrase). Hand-given: the split of a definition at 'means' (the learner does not learn that construction), the known-side templates, the synthetic text. The known side must already be in a wording the learner reads well.

## P23 (mostly null, text2prog7.py): fewer examples for a new wording
Tried to close the k=1 gap of paraphrase teaching (.75 vs .83 with a true answer; pseudo label right ~91%, so ~16 points are lost in feature learning, not labeling). 3 seeds, same protocol as P22.
- Alignment weight transfer (new side's unseen content tokens inherit the op-weights of the known side's distinctive tokens): k=1 .79 (tokens, +.04), no change for char n-grams, no change at k=2. Not enough to matter.
- Confidence gating (skip the definition when the known-side reading is ambiguous, margin < 2): HURTS, k=1 .68, k=2 .73 - gating throws away too many of the few definitions.
Conclusion: with 1-2 examples the P22 paraphrase recipe is about as good as this learner gets; the remaining k=1 gap is mostly the 9% pseudo-label noise. Zero-shot on unseen wordings is unchanged (.18 tokens / .41 char).

## Priors/experience audit (F-7, Chollet-style; applies to all sections above)
Format: result | priors handed in | experience consumed
- P7-P14 induction (mod..sumto) | recursion schema, cond forms, depth-1 expression grammar, add/sub primitives, post set, curriculum order, I/O format | 25 examples per skill
- P15 text commands | op library, hypothesis space (op x order), digit regex, whitespace tokens, sentence templates (own synthetic text) | 24-400 sentences
- P16 number words + 2-step | above + value range 1..10, clause templates, connectors | 150-1000 (words), 100-1000 (2-step) sentences
- P20 validation acceptance | above + 32 extra labelled validation examples | 57 examples per skill
- P21 3-step zero-shot | above + chaining solver (cut-pair search) | 0 three-step sentences
- P22 paraphrase teaching | the definition split at "means" (hand-split), known-side templates | 1-8 definitions per wording
Claim rule going forward (from Chollet 2019): every new result states its priors and experience in this form, and uses EVALPACK.md v1 unless stated.

## P25 (F-5, text2prog8.py): soft Occam / 2^-ops weighting on two-step sentences
P16 drops every 2-step explanation of a training sentence when a single-op explanation exists (categorical Occam). F-5 (Solomonoff-flavored) keeps all explanations and weights each by 2^-(number of ops). Same EVALPACK protocol as P16(b), 5 seeds.
- n=100: same phrasing .68 vs P16 .46; new connectors/frames .42 vs .25
- n=300: .77 vs .64; .46 vs .36
- n=1000: .73 vs .82 (WORSE); .41 vs .44 (worse)
Mixed result: soft Occam is much better with little data (roughly matches P16's n=1000 performance using 300 sentences) but the categorical rule wins at n=1000, where accumulated soft credit for spurious 2-step readings hurts. A schedule (soft early, categorical late) is an untested option. Priors/experience as in P16.

## P26 (baby2.py): caregiver-baby first-word experiment (Ash's design)
World: 6 Thai situation types (แม่ พ่อ นม ลูกบอล แมว หมา), one primary + 30% noise co-present object per scene, 100 scenes/day. Two scripted caregivers talk to EACH OTHER about the scene (2-4 word lines, echo replies, correct word 70% of the time); the baby overhears. Baby: from-scratch Hebbian word<->situation association counts, no pretrained anything. Once the baby produces a word, caregivers reply as they reply to each other (echo line; plus association boost/penalty = Turing 1948 pleasure-pain channel). FIRST-WORD criterion (pre-stated): >=80% of 200 held-out mother scenes get แม่ and <=20% of other scenes. 5 seeds.
Results:
- Informative words (any feedback mode): first word day 1-4 in 28/30 runs; all-6-word held-out accuracy .84-.88 (chance ~0.17). Dialogue (overheard 2-person speech) works as well as single-word utterances.
- SHUFFLED words (word stream carries no information) + contingent correct/wrong feedback: a first word STILL emerges (day 1-10 in 7/10 runs, all-word acc .74-.76). The correctness feedback is itself an information channel - this is exactly Turing's 1948 P-type mechanism (tentative entries fixed by pleasure, cancelled by pain) working as he intended, and it means "first word emerges" alone does not prove word learning.
- Shuffled words + random feedback: nothing learned (acc .13-.22, criterion never met). True negative control passes.
Honest scope: this is cross-situational associative grounding (Smith & Yu 2008 style), not understanding, grammar, or conversation. Joint attention is given for free (the scene is perfectly shared); babbling is modeled only as early production. 24h expectation set in the report to main; nothing beyond single-word grounding should be expected from this learner without new machinery (segmentation, word order, reference to absent things).

## P24 (cur7.py, seed 0): library learning via mined step-pair macros - NULL
Hypothesis: step pairs shared by >=2 learned skills (mined after sumto) are useful macros; trying them first on held-out tasks should cut search cost. Training set: mod,mul,div,power,gcd,fact,sumto,max,min (isprime NOT FOUND at 6M cap in both arms, recorded, excluded from restart). Held out: square, choose2, sumsq, dblfact. Mined macros: ((sub a b), b) and (a, (sub b one)) - the repeated-subtract and countdown pairs. Macro arm reorders only the comb=None step-pair phase.
- square: macro 4313812 tried = base 4313812 (same program, 40/40 all scales)
- choose2: macro 5199852 vs base 5199851 (same program, 40/40)
- sumsq: both NOT FOUND at 6M cap
- dblfact: macro 5480577 vs base 5480597 (same program; unseen 40/40/29/33 in BOTH arms - partial generalization is a property of the found program, not the arm)
Verdict: null. Differences of +1/-20 candidates in 4-6M are noise. The mined pairs do not occur in the held-out solutions, so reordering changes nothing; and the macro bias only touches one search phase. Next variants (backlog): apply macro bias to the comb phase, mine from >=3 tasks, mine pairs including the comb template, or grow the training set first so mined structure is richer. Fixed en route: mine_macros crashed on bare-variable steps (eval of str keys); keys are hashable, no eval needed.
Priors/experience: as in P7-P14 audit line; mined macros are experience-derived (from the run's own found programs), not hand-given.
