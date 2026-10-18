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
