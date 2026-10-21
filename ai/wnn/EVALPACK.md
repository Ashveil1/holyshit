# Eval pack v1 (frozen Oct 21, 2026). All future results compare under this protocol unless a section says otherwise.
- Numeric induction (cur6/cur7): 25 training examples from the task generator at scales 1-2 (generator seeds = run seed); acceptance = exact match on all 25 (+32 validation examples at scales 1-2, seed 5000+seed, when ablation 'val'); test = 40 fresh examples per scale 1-4, test seed 1000+seed. A "learned" program must match exactly; accuracy reported per scale as x/40. Recursion cap 400 during search, 20000 during test.
- Text-to-program (text2prog*): training sentences from template sets T[op][0] (seed = run seed); test = 300 sentences from T[op][1] (new frames) or T[op][2] (new synonyms), big numbers, test seed 100+seed. Accuracy = exact final answer. 5 seeds unless stated.
- Number words: GOLD = the 20 English+Thai words for 1..10; stage B sentences as in text2prog2.word_data.
- Two/three-step: as in text2prog2.two_step / text2prog5.three_step, 300/200 test sentences, 5 seeds.
- Baselines required for any "beats X" claim: majority/mean, kNN or MLP (T4 harness), or a cited published number with the same data/protocol.
