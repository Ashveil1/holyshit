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
