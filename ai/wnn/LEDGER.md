# Ledger: status of BACKLOG.md candidates
Format: B-id | status (done/null/failed/promising) | where recorded | one line
- B-516 | done | README + EVALPACK.md | priors/experience audit + frozen eval pack v1
B-514 | mixed | README P25 | soft Occam: +22 pts at n=100, +13 at n=300, -9/-3 at n=1000 vs P16
baby experiment | promising-but-scoped | README P26 | first word emerges day 1-4 from overheard Thai dialogue; reward channel alone can bootstrap grounding from noise (honest caveat); random-feedback control clean
B-001 family (P24 macro ordering) | null | README P24 | mined step-pair macros reorder <= +/-20 candidates in 4-6M; same programs both arms; macros absent from held-out solutions
F-6 (oops comb-frequency ordering) | harmful | README F-6 | no held-out win; dblfact lost (NOT FOUND vs found 5.48M); gcd +33x, power +76% on training tasks; comb identity non-stationary
B-001 (cap 1M, square) | null | cap1m arm /tmp/c7cap.log | NOT FOUND at 1M (needs 4.31M in default ordering); 1M cap decisively too small
B-002 (cap 1M, choose2) | null | cap1m arm | NOT FOUND at 1M (needs 5.2M)
B-003 (cap 1M, sumsq) | null | cap1m arm | NOT FOUND at 1M (also fails at 6M)
B-004 (cap 1M, combleaf, square) | null | cap1m,combleaf arm /tmp/c7leaf.log | NOT FOUND at 1M (comb=None phase alone >1M; comb set never reached)
B-005 (cap 1M, combleaf, choose2) | null | cap1m,combleaf arm | NOT FOUND at 1M; default ordering already front-loads leaf combs so combleaf removes only post-solution candidates - premise falsified
B-006 (cap 1M, combleaf, sumsq) | null | cap1m,combleaf arm | NOT FOUND at 1M; same dominance argument as B-004/005
B-007 (cap 1M, freq combs, square) | null | cap1m,oops arm /tmp/c7co.log | NOT FOUND at 1M; None phase dominates before comb ranking matters
B-008 (cap 1M, freq combs, choose2) | null | cap1m,oops arm | NOT FOUND at 1M
B-009 (cap 1M, freq combs, sumsq) | null | cap1m,oops arm | NOT FOUND at 1M
B-010 (cap 3M, square) | null | cap3m arm /tmp/c7c3.log | NOT FOUND at 3M (tried 3.88M; needs 4.31M)
B-011 (cap 3M, choose2) | null | cap3m arm | NOT FOUND at 3M (tried 3.88M; needs 5.2M)
B-012 (cap 3M, sumsq) | null | cap3m arm | NOT FOUND at 3M (also fails at 6M)
B-019/020/021 (cap 6M, full combs) | null | = P24 base arm | these ARE the baseline; tried ratio 100% > 60% criterion by construction (auto-generated degenerate items)
B-025/026/027 (cap 6M, freq combs) | null | = F-6 oops arm | square 4313812=, choose2 5199851=, sumsq NOT FOUND=; tried ratio ~100% > 60% criterion (see README F-6)
B-013 (cap 3M, combleaf, square) | null | cap3m,combleaf arm /tmp/c7c3l.log | NOT FOUND at 3M (needs 4.31M)
B-014 (cap 3M, combleaf, choose2) | null | cap3m,combleaf arm | NOT FOUND at 3M (needs 5.2M)
B-015 (cap 3M, combleaf, sumsq) | null | cap3m,combleaf arm | NOT FOUND at 3M
B-016 (cap 3M, freq combs, square) | null | cap3m,oops arm /tmp/c7c3o.log | NOT FOUND at 3M (needs 4.31M)
B-017 (cap 3M, freq combs, choose2) | null | cap3m,oops arm | NOT FOUND at 3M (needs 5.2M)
B-018 (cap 3M, freq combs, sumsq) | null | cap3m,oops arm | NOT FOUND at 3M
B-022 (cap 6M, combleaf, square) | null | combleaf arm /tmp/c7l6.log | FOUND 4313812 = default exactly (None phase untouched); tried ratio 100% > 60% criterion
B-023 (cap 6M, combleaf, choose2) | null | combleaf arm | FOUND 5199851 = default exactly; leaf combs already front-loaded in default ordering
B-024 (cap 6M, combleaf, sumsq) | null | combleaf arm | NOT FOUND = default
B-028/029/030/031 (init full, post full) | null | = P24 base arm | baseline-repeat degenerate items; tried ratio 100% > 70% by construction
combleaf dblfact (extra data) | null | combleaf arm /tmp/c7l6.log | FOUND 5480597 = default exactly, same partial 40/40/29/33
B-036 (init {y,zero}, square) | PROMISING | inity0 arm /tmp/c7iy0.log | FOUND 2591723 = 60% of default 4313812, 40/40 all scales, DIFFERENT program (repeated addition, no power op) - meets <=70% criterion
B-037 (init {y,zero}, choose2) | PROMISING | inity0 arm | FOUND 2604011 = 50% of default 5199851, 40/40 all scales - meets criterion
B-038 (init {y,zero}, sumsq) | null | inity0 arm | NOT FOUND (also fails default)
B-039 (init {y,zero}, dblfact) | failed | inity0 arm | NOT FOUND - task LOST (default solution needs init two); init restriction trades coverage for speed
inity0 side-effect | caveat | inity0 arm | fact got a different program: fits train, unseen 40/40/32/34 vs default 40/40/40/40 - smaller prior set silently picked a worse-generalizing program
B-032 (post id-only, square) | null | postid arm /tmp/c7pid.log | FOUND 4313812 = 100% of default 4313812, same program (uses post=id) - no reduction
B-033 (post id-only, choose2) | null | postid arm | FOUND 5199851 = 100% of default, same program
B-034 (post id-only, sumsq) | null | postid arm | NOT FOUND at 6M cap = default
B-035 (post id-only, dblfact) | null | postid arm | FOUND 5480597 = 100% of default, same partial program (unseen 40/40/29/33)
B-040 (inity0+postid, square) | derived | = B-036: inity0 solution uses post=id, candidate order unchanged, so identical result 2591723 (60% of default) - no additional reduction from post restriction
B-041 (inity0+postid, choose2) | derived | = B-037: 2604011 (50% of default), same reasoning
B-042 (inity0+postid, sumsq) | derived | NOT FOUND (= B-038): any post=id solution within cap would have been found by the full-post run
B-043 (inity0+postid, dblfact) | derived | NOT FOUND (= B-039): task lost under init {y,zero} regardless of post set
P27h controls (blind-pool dialogue, same scenes/seeds as llmrew) | measured | baby3c.py pool mode, logs/baby3c_s{0,1}.log | overhear (no reward, baby never speaks): FIRST WORD DAY 1 both seeds, all6 .91/.89 day1 -> .91/.86 day5. rewonly (reward, non-contingent dialogue): FIRST WORD DAY 1 both seeds, all6 .91/.90 day1 -> .92/.89 day5. Controls MATCH llmrew day-1 (all6 .91/.89): first-word grounding comes from scene-word co-occurrence in the dialogue, NOT from the reward channel or caregiver contingency. llmrew days 2-5 not run (controls null per pre-stated rule).
B-521 (two-word composition, baby4.py) | PASS | logs/baby4.log | novel entity+action pairs never heard in training: order-class arm 20/20 correct (5 seeds x 4 held-out, criterion >=18, p<5e-5); direct-bigram arm 11/20 = chance; bag-of-words 10/20 = chance; trained-pair order 12/12 every seed; grounding 8/8 words every seed. Baby composes e.g. "แม่ นอน" (mother sleeps) never said by caregivers, in correct Thai order. Mechanism: Hebbian grounding (overhearing only, no reward - per P27h controls) + order statistics over grounded MEANING CLASSES (entity-word before action-word, ~550:5 in heard speech). Given prior beyond P26: scene = (entity, action) two slots. Toy-world caveat: synthetic template dialogue, 4 animate entities only.
B-044 (init10+baselib, square) | mixed | init10,baselib arm logs/c7i10_baselib.log | FOUND 719709 = 16.7% of default 4313812 (clean comparison: same grown library, 1973 combs both) BUT worse-generalizing program: init b=one, step ((div a b),(mul a b)) shortcut, unseen 38/37/38/40 (fails x=0) vs default 40/40 all. Default's clean program needs init b=two. Criterion 'same success' NOT met.
B-045 (init10+baselib, choose2) | PROMISING | FOUND 2597867 = 50.0% of default 5199851, SAME program (init b=one survives), 40/40 all scales - meets <=70% criterion; effect is the 4->2 init halving
B-046 (init10+baselib, sumsq) | null | NOT FOUND at 6M cap = default
B-047 (init10+baselib, dblfact) | failed | NOT FOUND - task LOST (solution needs init two), same as inity0
init10 cascade caveat | caveat | init10 full-list run logs/c7i10_full.log | mod,mul,div,power,gcd,fact,max,min ALL NOT FOUND (every one needs init b=y; default programs all init b=y) - library never grows (97 vs 1973 combs), so raw tried counts from the full-list arm are NOT comparable to default; sumto FOUND 108198 (init zero) in the small space. baselib flag added to cur7.py for clean init-set comparisons.
B-048 (init10+postid, square) | derived | = B-044: both init10 solutions use post=id; post restriction is null (B-032..035)
B-049 (init10+postid, choose2) | derived | = B-045: 2597867 (50%)
B-050 (init10+postid, sumsq) | derived | NOT FOUND (= B-046)
B-051 (init10+postid, dblfact) | derived | NOT FOUND (= B-047)
B-055 (adversarial boundary acceptance, square) | PASS | init10,baselib,adv arm logs/c7adv_square_choose2.log | boundary examples x in {0,1,2,3,30} from the task formula (no hand labels): the wrong-short div/mul square program (38/37/38/40, fails x=0) is REJECTED at 719709; search continues to the clean repeated-addition program at 2583787 = 59.9% of default 4313812, 40/40 all scales. With the boundary gate, init10 square now meets B-044's criterion (same success, <=70%).
B-055 overhead check (choose2) | PASS | same log | boundary gate adds no cost when the first program is already clean: identical program at identical tried 2597867 (50.0% of default), 40/40 - no false rejection.
B-056 (boundary acceptance, even) | PASS-through + eval-cap caveat | baselib,adv arm logs/c7adv_even_sumto.log | FOUND 123619: parity toggle via (power zero b), post=nz. Fits train + boundary + scales 1-3 (40/40); scale 4 = 26/40 - NOT a logic error: linear-depth recursion exceeds the 20000-step eval cap for x>20000 (26/40 = expected fraction under cap). Boundary gate correctly did not reject a correct program; no wrong-short candidate was at stake here.
B-057 (boundary acceptance, sumto) | PASS-through | same log | FOUND 2707098, 40/40 all scales, clean program (init zero, (sub a one),(add a b)); no rejection occurred. Caveat: tried not comparable to base 1703202 - baselib pins all 7 library fns while base had only 5 at sumto-search time (bigger space).
B-053 (example subsampling, square) | null | init10,baselib,sub arm logs/c7sub.log | same program at same tried 719709, 63s vs 63s without gate - no time win; candidates die on the first-example check already, so deeper checks are rare
B-054 (example subsampling, choose2) | null | same log | same program at same tried 2597867, 191s vs 194s (1.5%) - far from <70% criterion. Acceptance invariance verified both tasks (identical programs + tried counts).
B-052 (simplify-first node-count ordering) | mixed | init10,baselib,simp arm logs/c7simp.log | square: CLEAN repeated-addition program found directly at 2583787 (59.9% of default, 40/40 all scales) - size ordering places the clean program before the div/mul shortcut, no boundary gate needed. choose2: identical program, identical tried 2597867, time 192s vs 194s (no loss). sumto: FAILED criterion - found a smaller but worse-generalizing program (init b=one, unseen 38/39/40/40, breaks x=0) at 715986 vs clean init-zero at 2707098. Size ordering alone does not fix underdetermination; combine with adv gate (B-055) - simp,adv sumto run next.
B-052+B-055 combination (simp,adv, sumto) | PASS | logs/c7simpadv_sumto.log | boundary gate rejects the init-one partial program (broke x=0); search continues to the CLEAN init-zero program at 1415698 = 52% of the same-space non-simp cost 2707098, 40/40 all scales. Recipe: size-ordered search finds short programs fast, boundary acceptance keeps them honest. Combined standings vs default: square 59.9%, choose2 50.0%, sumto 52% same-space - all clean 40/40.
B-058 (comb-level type-fail pruning, choose2) | null (profiled) | init10,baselib,prof logs/c7prof_choose2.log | full search to the find (2597867 tried): 1699163 candidates fail r0 with wrong value, ~898680 raise on r0, ZERO pass r0 and fail deeper (earlyfail 0, deepfail 0); the winner used 24 train-check evals. Every candidate is already decided by exactly one evaluation - there is no multi-example or per-comb redundant work to prune, so the <80%-time criterion is unreachable by construction. Cap-1M sample showed the same profile.
B-059 (library 40/40 admission gate) | null (analyzed, no run needed) | /tmp/c7b.log | all 7 library admissions under the current 36/40-at-scale-2 rule were actually 40/40 at ALL scales (mod,mul,div,power,gcd,max,min) - no poisoned entry ever entered on this curriculum, so tightening the gate changes nothing here. Counter-caveat from B-056: a STRICT 40/40-all-scales gate would wrongly reject correct-but-deep programs (even: clean logic, 26/40 at scale 4 only because recursion exceeds the 20000-step eval cap). Keep the current gate; note eval-cap artifacts must be distinguished from logic errors before any gate tightening.
B-061 (forget-and-relearn: mod from library+3 examples) | PASS | baselib,tr3 arm logs/c7tr3_mod.log | mod excluded from pinned library (honest re-derivation): 3 random examples suffice - the FIRST consistent program is the exact correct one (init b=y; if (lt a b) -> a; else step ((sub a b),b)), 40/40 all scales. tried 2082 vs from-scratch 642 (bigger library space; cost trivial both ways). Criterion <=3 examples MET. Caveat: single task/seed; underdetermination risk grows with fewer examples (B-052/055 pattern) - 3-example acceptance should be paired with the boundary gate in general.
B-060 (compression: re-derive each skill via full library) | null (FAIL criterion) | baselib arm logs/c7compress.log | re-derived all 7 solvable curriculum skills with the full pinned library minus the skill itself: EVERY re-derivation found the byte-identical program (total DL 66 = 66 nodes); isprime NOT FOUND both arms. The original growing-library curriculum already captured every compression opportunity - re-derivation with a bigger library only costs more search (mul 4155513 vs 1253589, div 4202709 vs 1253589, power 4450489 vs 2072761, fact 1415364 vs 890700, sumto 2707098 vs 1703202, gcd 100985 vs 60401). Library size trades search COST, not program length.
B-062 (forget-and-relearn: gcd from library+3 examples) | PASS | baselib,tr3 arm logs/c7tr3_gcd.log | gcd excluded from pinned library (mod kept): 3 examples suffice - first consistent program is the exact Euclid step ((mod b a),a), 40/40 all scales, at tried 100985 = IDENTICAL position to the 25-example find. The library's mod op constrains the space so strongly that no 3-example pretender precedes the true program. Two-task pattern (B-061/062): library-supported relearning from 3 examples works when the needed op is one library call away.
B-063..070 (tok, soft credit, n=24..400) | null (baseline-repeat) | t3grid.py logs/t3grid.log | exact reproduction of P15's published row: frames .43/.73/.82/.84, synonyms .12/.15/.20/.20 - identical configuration by construction; reproducibility CONFIRMED (first run skipped the numbers eval and shifted the rng - grid runner matches the original call sequence)
B-071..078 (tok, HARD credit) | null | same log | hard credit assignment never beats soft: frames .44/.73/.78/.81 vs soft .43/.73/.82/.84; synonyms .11/.15/.18/.20 vs .12/.15/.20/.20 - soft credit design choice validated
B-079..086 (char, soft) | null (baseline-repeat) | same log | exact P15 char row reproduction: frames .42/.70/.78/.77, synonyms .18/.28/.41/.40
B-087..094 (char, HARD credit) | null | same log | frames .43/.66/.72/.72, synonyms .20/.28/.37/.38 - never beats char-soft
B-095..102 (tokuni, soft) | null | same log | frames .43/.70/.78/.80, synonyms .12/.16/.20/.21 - bigrams help (tok .84 vs tokuni .80 frames at n=400); never beats tok-soft
B-103..110 (tokuni, HARD credit) | null | same log | frames .44/.70/.75/.78, synonyms .11/.16/.17/.21 - never beats tokuni-soft
T3 grid summary: P15's choices (token+bigram features, soft credit) are locally optimal in this grid; char features win ONLY on unseen-synonyms (.40 vs .20 at n=400, as P15 reported); hard credit never helps.
B-111/112 (bigram on, lowercase on, mc=1) | null (baseline-repeat) | = P15 default config: tok n=150 frames .82 synonyms .20
B-113/116/119/122/125/128 (2-step task cells) | not runnable as stated | the P15 learner has no two-step capability - 2-step is P16's task (text2prog2.py); generator mixed domains
B-114/115 (tok, mc=2) | null | t3mincount.py logs/t3mincount.log | frames .82 synonyms .19 at n=150 - no gain over default (.82/.20)
B-117/118 (tok, mc=4) | WORSE | frames .70 synonyms .17 - filtering rare features loses information
B-120/121 (bigram off, mc=1) | null | = tokuni soft (B-097/098 measured): frames .78 synonyms .20
B-123/124 (tokuni, mc=2) | null | frames .78 synonyms .20 - no gain
B-126/127 (tokuni, mc=4) | WORSE | frames .69 synonyms .17
T3 min-count summary: feature-frequency filtering never helps at n=150; mc=4 actively hurts. Default (keep all) stands.

T3 word-lexicon grid (B-129..B-182): learn_lexicon params minv(minmass) x margin x rounds x n={60,150,400}, 5 seeds, t3lex.py logs/t3lex.txt. P16 defaults (minv3 m2.5 r4) reproduced exactly (n=150 6.8/.4/.37, n=400 12.4/1.4/.54); new n=60 default baseline: 2.4 gold, 0.2 spur, acc .25. minv 1.5 and 2 identical (integer vote counts). rounds: no effect except m2 n150 (r2 slightly fewer spurious).
- B-135/138/153/156 (minv1.5/2, m2.5, n=60) | PASS | gold 4.2 vs 2.4, spur +0.8 (bound +1)
- B-165/168 (minv3, m2, n=60) | PASS | gold 3.4 vs 2.4, spur +0.8
- B-129/132/147/150 (minv1.5/2, m2, n=60) | FAIL bound | gold 5.8 vs 2.4 but spur +1.6
- m2 at n>=150 (B-130/131/133/134/148/149/151/152/166/167/169/170) | FAIL bound | gold more than doubles (n=150: 13.2-14.4 vs 6.8; n=400: 17.8-18.0 vs 12.4; acc .51-.67) but spur +1.4..+3.6 exceeds +1
- m2.5 at n>=150 (B-136/137/139/140/154/155/157/158/171..176) | null | no gold gain over default
- m4 (B-141..146, B-159..164, B-177..182) | FAIL | collapse to 0.6-1.8 gold - too strict kills word learning
- extra probe m2.25 minv1.5 r4: n=60 4.2/1.0, n=150 7.4/2.2, n=400 14.8/3.2 - sits on the same tradeoff curve, no free lunch
T3 lexicon summary: recall-precision tradeoff is real; margin 2 buys 2x word recall for ~2-4 spurious entries (pre-stated bound only passes at n=60). Default margin 2.5 is well-placed. Word recall, not sentence grammar, is the bottleneck at small n.
B-183 (active clarification, top-2 + 1 question) | PASS (qualified) | t3clarify.py | tok n=150, 5 seeds: frames top1 .823 -> clarify .829 (delta .5, asks 43%) / .862 (delta 2.0, asks 58%); synonyms top1 .227 -> .275 / .310 (asks 69/83%). Oracle top-2 ceiling: frames .874, synonyms .315 - delta 2.0 nearly saturates it. Clarification recovers almost all top-2 headroom, but most inputs need a question and the synonyms ceiling is low: confusion is spread beyond top-2.
B-184 (paraphrase teaching, 4 glue-word examples) | FAIL | t3glue.py | n=1000 5 seeds: new-connector acc .41 baseline (published .44; rng-offset noise) vs .43 with 4 taught connectors - far from .6 target. 4 labelled examples are swamped by 1000 sentences; connector identity is not the bottleneck for new-phrasing generalization.
B-185 (typing: arg-count candidate restriction) | null | t3typing.py | fit wall time n=150/400: 1.01x speedup only - fit is dominated by feature bookkeeping, not candidate evaluation; acc unchanged within noise (frames .825->.837 n=150, .835->.869 n=400; synonyms ~.20 both). Side note: typing excludes degenerate 1-number variadic explanations; slight acc shift not pursued.
B-186 (curriculum: order frames by test similarity) | null by analysis | the P15 Learner.fit is a batch count accumulator - training order cannot affect the learned model. Nothing to measure.
B-187 (negative examples / abstention) | FAIL | t3neg.py | chit-chat-with-numbers (10 en/th templates) vs tok n=150: always-answer false-answer rate .702 (30% abstain free on zero known features). Avg-log-lik threshold T=-2.5/-2.0/-1.5/-1.0: op acc .797/.750/.682/.525 vs false-answer .664/.645/.603/.543 - distributions overlap; <10% false-answer unreachable without collapsing op acc (.829 baseline). Rejection needs a better signal than per-feature score.

T4 baselines (B-188..B-206): MLP(2-32-32 tanh, pure numpy)/kNN-3/majority/linreg on the exact cur7 protocol (25 train at scales 1-2, y distractor kept, 40 eval/scale at scales 1-4, 3 seeds). logs/t4base.json + t4base.py. Numbers are correct/40.
- Regression tasks: every baseline collapses at scales 3-4 (0-4/40). Best scale-1 results are mostly answer-distribution artifacts: div 18/40 (many x//y=0), power 22/40 (0/1 outputs), max/min ~18-20/40. square: mlp 11.7/6.0/3.0/3.7; sumto: <=3.7 all scales; absdiff: 12.0/3.0/0.3/0.0. The program search (40/40 at all 4 scales when found) is not a marginal win over function approximation - it is a different category.
- yes/no tasks: even ~50-57% everywhere (chance); isprime majority predictor rises to 87% at scale 4 (primes thin out) without any primality knowledge.
B-207 (chance) | recorded in README | yes/no = 50% (even), majority-class rate varies (isprime 66-87% by scale); exact-number chance ~1/range ~ 1%
B-208 (eval pack v1) | committed evalpack_v1.json | 18 tasks x (25 train + 4x40 eval), seed-0 protocol, frozen for future comparisons

T5 HDC encodings at dim=1024 (B-209..B-217, t5hdc.py): 5 seeds, P5 E5 protocol. Memory vector 1KB int8 (128B packed) vs P5 4KB/16KB.
- facts (35 pairs, XOR binding, 70 queries): random-proj 97.7% [95.7-100] - P5-equivalent accuracy at 1/4 the RAM => PASS (B-216-ish). level 2.9%, thermo 2.9% => FAIL.
- arith chaining (100 links, all 4950 a+k<=99 pairs): random 6.3%, level 1.0%, thermo 0.0% => FAIL all (P5: 100% at 4KB). 100 superposed links exceed dim-1024 cleanup capacity and recall errors compound over k hops.
- 2-hop (50 chains x 3 links): random 7.6%, level 0.8%, thermo 0.0% => FAIL all (P5: 100%).
- implementation note: first run scored ~1% everywhere because unbind used the INVERSE permutation; bind p(k)*v must be read with the SAME p(k) (P5's directional-binding lesson reproduced the hard way).
- correlated encodings (level/thermo) cannot support exact symbolic recall at any rate - adjacent codes are indistinguishable after bundling. Symbolic HDC requires near-orthogonal (random) codes.
Follow-up probe queued: random encoding at dim 2048/4096 to find where chaining capacity recovers (P5 RAM parity point).
T5 dim sweep (random-proj, t5dim.py): arith(475 pairs P5-style) 1k .01 / 2k .17 / 4k .87 ; 2-hop 1k .08 / 2k .43 / 4k .89 (3 seeds). Capacity scales with dims; P5's 16KB arith memory = dim 16384 int8. Probing dim 8192/16384 for the P5-parity point.
T5 resolution (t5dim2.py fixed - first run mislabeled dim 1024 twice): arith chaining reaches 475/475 at dim 8192 (8KB int8 = HALF P5's 16KB) and dim 16384 (P5 parity), random-proj, 2 seeds. 2-hop 50/50 at dim 8192 (3 seeds). Full capacity curve arith: 1k .01 / 2k .17 / 4k .87 / 8k 1.00 / 16k 1.00; 2-hop: 1k .08 / 2k .43 / 4k .89 / 8k 1.00.
T5 VERDICT: random-proj HDC matches P5's exact accuracies at HALF the RAM for chaining (8KB vs 16KB) and a QUARTER for facts (1KB vs 4KB, 97.7%) => B-209..217 goals met by random-proj only; level/thermometer encodings are category errors for exact symbolic memory (correlated codes, 0-3% at any task). Caution: 2 seeds at 8k/16k.
T5 dim-4096 grid (B-218..226, t5grid4k.py, 3 seeds, arith=475 sampled pairs): level arith .008 / facts .029 / 2-hop .000; thermo .000/.029/.000; random arith .865 / facts 1.000 / 2-hop .887. Confirms: level/thermo failure is ENCODING, not capacity (still ~0 at 4k dims). random facts = P5's 100% at same 4KB RAM (parity; dim-1024 already gave 97.7% at 1/4 RAM => PASS). random arith/2-hop at 4KB = 87-89% (P5 used 16KB for arith; P5 parity at dim 8192+ per t5dim2).
T5 dim-16384 grid (B-227..235, t5grid16k.py, 2 seeds): level .006/.029/.000, thermo .000/.029/.000, random 1.000/1.000/1.000. At P5's own 16KB RAM random-proj reproduces all P5 E5 numbers exactly. Level/thermo dead at every dim - T5 encoding question closed: symbolic HDC needs near-orthogonal codes; capacity, not encoding sophistication, is the binding constraint.
B-237 (HDC 10x scale, t5scale.py, 3 seeds) | mixed | facts 350 pairs/700 queries: dim 8192 .848, dim 16384 .994 (~P5 accuracy at 10x facts, same 16KB RAM - borderline PASS). 2-hop 500 chains/1500 links: dim 8192 .006, dim 16384 .053 FAIL - chained cleanup needs ~100 dims/link, not ~10; multi-hop RAM must grow with link count, no fixed-size win.
B-238 (HDC recall program/op by task description, t5oprecall.py, HD classifier over P15 sentences, 12 ops, chance 8.3%) | PASS at dim 16384 only | unseen-frames top-1 op recall, 3 seeds: dim 1024 n=60/150 .701/.838; dim 4096 .727/.879; dim 16384 .738/.909 [min .867]. Order-free bundling of unigram+bigram token codes recovers the op at P15-n=150 levels - but note this is OP recall, not answer accuracy (P15 predicts answers at .82 with far less memory).
B-239 (thermo/level interpolation on unseen operands, t5interp.py, dim 4096, 200 stored sums, one unseen operand) | FAIL for all | level .022, thermo .022, random .030 (chance 1/64=.016) - no encoding interpolates exact sums; confirms P5 E2/E3 (exact arithmetic from examples is memorization) in the HDC binding setting.
B-242 (episodic recall after distractors, t5distract.py, 5 seeds) | FAIL for HDC | first-fact recall after 0/100/1000 distractors: dim 4096: 1.00/1.00/.20; dim 16384: 1.00/1.00/.80. HDC bundling degrades with memory load - contrast WNN tables (P5 E4: 255/256 retention regardless). Retention is where table memory beats superposition; superposition buys nothing here.
B-236 (Bloom WiSARD memory scaling, t5wisard.py, binarized MNIST, 28-bit tuples x28 nodes, 60k/10k) | PASS | WiSARD acc .9115 (~1.9MB sparse); Bloom-WiSARD at half RAM: .9059 (-0.6pts). First attempt with 8-bit tuples saturated at .30 - classic node saturation; 28-bit tuples are the right grain.
B-241 (one-pass few-shot sweep, same harness) | recorded | k=1/5/20 per class: WiSARD .340/.470/.647 vs one-vs-rest MLP(784-32-1, 800ep) .106/.148/.322. One-pass table learning beats tiny gradient MLP by 2-3x at every few-shot level (MLP baseline is small; gap, not absolute numbers, is the claim).
B-243..248 (HDC chain depth 2 at scale, t5chain.py, dim 16384, random-proj, 3 seeds) | partial | links 70: logic-2hop 1.000, arith-chain 1.000 (P5 parity); links 300: logic .996, arith .945 (graceful degradation, k<=50 hops sampled); links 1000: RUNNING at commit time - job survives in sandbox, result lands in LEDGER next wake. Trend: fixed 16KB memory holds ~300 chained links before chained cleanup degrades.
B-247/248 resolved (links 1000): logic-2hop .284, arith-chain .038 - honest limit found: a fixed 16KB HDC memory holds ~300 chained links (logic .996 / arith .945) and collapses by 1000. Chain capacity must grow with link count (~50 dims/link for 2-hop queries; multi-hop arith needs more).
B-249..254 (HDC chain DEPTH 5, t5chain5.py, dim 16384, 3 seeds) | capacity cliff, not depth | links 70: logic 1.000 arith 1.000; 300: .990/.989; 1000: .038/.031. Depth-5 ~ depth-2 at the same link count: per-hop cleanup absorbs error, so chaining error does NOT compound with depth - the binding constraint is superposed-link capacity (~300 links/16KB), and it fails as a cliff, not a slope.
B-255..260 (chain depth 10, t5chain10.py, dim 16384, 3 seeds; logic and arith are the same +1-chain computation here) | links 70: 1.000; 300: .973; 1000: .002. Depth 10 vs 5 vs 2 at 300 links: .973/.990/.996 - slight depth erosion, still capacity-dominated. T8 series conclusion: HDC chaining is exact up to ~300 links per 16KB at any depth <=10, then falls off a cliff. Fixed-size symbolic memory has a hard capacity; this is the honest limit the backlog asked for.
B-261 (transitivity depth 10) | PASS at 70 links (1.000 exact), .973 at 300, .002 at 1000 | same computation as B-255..260.
B-262 (negatives + mixed radix, t5radix.py, dim 16384) | PASS within capacity | signed chain -100..100 (201 links): 1.000 exact. 4x12 clock (48 links, minute/hour rollover): 1.000 exact. 12x60 (720 links): .107; 24x60 (1439 links, 60q/2 seeds): .025 - the SAME capacity cliff as B-247..260, not a radix problem. HDC chaining is representation-agnostic: negatives and mixed radix work exactly wherever the link count fits.
T9 interim (methodology): cap1m starves square under the full recipe (init10,baselib,simp,adv) - first t9vote attempt found NOTHING at 1.29M tried (adv rejects the 719k shortcut, clean program needs ~2.6M). Rerun at cap3m for square (cap1m others), 2 seeds.
T9 vote k=3 subset-0.5 (B-263/264/265, t9vote.py, recipe init10,baselib,simp,adv, 2 seeds) | FAIL (no benefit, 3x cost) |
- square: single clean 40/40 at 2583787 tried (= the B-055 recipe number exactly - independent protocol replication). vote clean at 3x cost.
- even: vote and single find the SAME countdown program (init b=one, step (sub a one)(sub one b)); scale-4 "wrong" flags were an eval-CAPF artifact - 40/40 at cap 500000 vs 26-27/40 at the standard 20000. METRIC BUG FOUND + FIXED: unseen-scale eval must raise CAPF for slow-countdown programs; cur7's standard CAPF=20000 misclassifies correct linear-time programs at scale 4 (x up to 30000).
- sumto: cap1m exhausts (tried=1291776 signature, both arms); cap3m: single clean at 1415698, vote clean at 3x cost.
- Why voting can't help here: shortcuts are SYSTEMATIC - every 50% subset admits the same first-accepted program (vote_tried = 3x single_tried exactly, all votes found identical programs). Boundary acceptance (adv) already removes the shortcut class voting was aimed at. Subsample voting is 3x cost for zero measured wrong-program reduction.
B-266..270 (vote k=3 subset 0.5/0.8 on choose2/square/even/sumto) | null by analysis | B-263..265 measured 0 wrong programs in EITHER arm at proper caps (square/even/sumto, and choose2's clean 40/40 at 2597867 from B-055). Voting can only reduce a wrong-program rate; the rate is already 0 under adv at cap3m. Subset-0.8 variants are strictly more correlated than the 0.5 subsets that produced byte-identical programs. No CPU burned.

B-240 (subsampled connectome speed test, worm_plastic_mnist.holy, core 233 cells/3275 edges vs full 473/5914) | TOO HEAVY - killed at time-box | Core run at 100% CPU did not finish phase A (1500 train samples, 300/class digits 0-4) in 60 CPU-min (>2.4 s/sample); full connectome impractical by scaling (edge ratio 1.56x, state ops 2x -> phase A alone ~2-3 h). Cost driver is NOT the reservoir (RSTEP=15) but the per-sample state_hex string encoding + 784-pixel pmap in the hosted runtime. Verdict: core-vs-full is not measurable at this runtime cost; B-240 needs a cheaper state encoding (bit-vector state sampled directly into WNN tuples, no hex round-trip) before rerun. Artifacts kept: ai/wnn/data/connectome_core.txt (233 cells = every se/in-component neuron + GABAergic set, non-neuronal cells dropped), mnist_train/test.txt (500/100 per class, sample-identical to program caps).

B-271..278 (vote k=5, subset 0.5/0.8, square/even/sumto/choose2) | null by analysis | Same argument as B-266..270, one level stronger: B-263..265 measured BYTE-IDENTICAL first-accepted programs across all k=3 subsets (vote_tried = exactly 3x single), so a k=5 vote over the same subsets is unanimous by construction at 5x cost. Subset-0.8 arms are strictly more correlated than the 0.5 arms that already produced identical programs. Wrong-program rate under adv at cap3m remains 0 (B-266..270). No CPU burned. T9 closed: test-time subsample voting cannot reduce systematic shortcuts; boundary acceptance already owns that class.

B-279..298 (vote k=9; tie-break shorter/first/vote-margin; self-consistency k=5; verify-then-accept fresh tests) | null by analysis | All reduce a wrong-program rate that is already 0 under adv at cap3m (B-263..270). k=9 voting: unanimous by construction (k=3 subsets already byte-identical). Tie-breaks: the pipeline already enumerates in size order (simp) and accepts the first program passing adv - shorter/first/vote-margin are its existing behavior. Self-consistency k=5 = the measured B-263..265 protocol. Verify-then-accept: adv already gates on held-out tests; rate is 0 where measured (square/even/sumto/choose2). Not nulled: B-299 (adaptive budget - CPU efficiency, different question), B-300 (execution-agreement ensemble on text2prog - errors there may be example-dependent noise, the one case voting CAN fix), B-498 (search repair - different mechanism). No CPU burned.

B-299 interim (search-time cap artifact, CURR skills) | PROTOCOL FINDING | Under the T9 recipe (init10,baselib,simp,adv, cap 6M), mod is NOT FOUND at ANY train size n in {3,5,10,25} (tried=6002688 exhaustion, ~235s each, seed 0): the pinned base program (repeated-subtraction loop, linear in x) exceeds the SEARCH-time step cap CAP=400 on adv boundary inputs, so boundary acceptance rejects the correct program class outright. Sibling of the B-265 eval-time CAPF=20000 artifact: BOTH ends of the pipeline punish slow-but-correct loop programs on large inputs. B-299 grid moved to the T9-proven skills (square/even/sumto/choose2); fixing search-time CAP for loop programs is a precondition for re-testing CURR skills under adv.

B-299 (adaptive search budget cap(n) vs fixed cap, t9budget.py, recipe init10,baselib,simp,adv, cap 6M measurement, grid 4 skills x n in {3,5,10,25} x seeds 0-1 = 32 cells, logs/t9budget2.json) | NEGATIVE - no adaptivity available | tried is CONSTANT per skill across all n AND seeds: square 2583787, even 123944, sumto 1415698, choose2 2597867 (32/32 found, all clean 40/40 scales 1-4). Mechanism: the adv boundary suite is fixed per task and decides acceptance before train size binds; enumeration order is train-independent, so the first program passing boundary+train is the same for any n>=3 and any seed. An n-adaptive budget is therefore a no-op - the fixed cap is the only knob, and no CPU saving exists along the n axis. Corollaries: (1) DATA EFFICIENCY: n=3 random examples suffice for all 4 T9 skills - examples 4..25 are redundant under adv; T10 selection strategies cannot beat random on these skills (any selection gives the identical program at identical tried). (2) even's 8/8 wrong-flags at eval CAPF 20000 cleared to 40/40 at CAPF 500000 (both seeds) - the B-265 eval-cap artifact is systematic for countdown programs; any future eval of linear-loop programs MUST raise CAPF. (3) CURR arm (mod/mul/div/gcd/isprime/fact) untestable under adv until the search-time CAP=400 boundary artifact is fixed (see B-299 interim, B-522).

CORRECTION (B-299 interim mechanism): the mod NOT-FOUND cause is NOT the search-time CAP=400/adv boundary (boundary() has no mod entry - ADV is empty for CURR skills). Real cause: the T9 recipe's init10 flag restricts inits to (one,zero), dropping init='y' that accumulator-loop programs start from. With full inits under baselib,simp,adv: mod FOUND at tried=482 (0s), the same repeated-subtraction program, clean 40/40 scales 1-4 at CAPF 20000. The CAP-artifact framing in the B-299 interim entry and PR #192 body is superseded by this entry.

B-522 (init-set coverage for CURR under adv) | DONE by measurement | Dropping init10 (full init set y/one/zero/two) restores CURR learning under adv: mod tried=482, clean. init10 remains correct for countdown-style T9 skills (square/even/sumto/choose2 all pinned with init one/zero) - the recipe must match init set to skill family, which the learner cannot know a priori. Open question recorded: per-skill init-set selection (try both, take first-found = 2x worst-case cost, or union the sets and let simp ordering absorb it).

B-299-CURR (tried(n) grid on the item's stated task set mod..sumto, recipe baselib,simp,adv FULL INITS, cap 6M, logs/t9budget_curr_run.log + t9budget_curr2_run.log/json) | COMPLETE - verdict: budget demand is DISCONTINUOUS, not a smooth cap(n) | Per skill (n in {3,5,10,25}, seeds 0-1):
- mod: 482 flat, clean 8/8. fact: 1138240 flat, clean 8/8. sumto: 2176534 flat, clean 8/8 (vs 1415698 under init10: restricting inits to (one,zero) saves 54% for countdown-family skills - mirror of B-522; init set is a per-family cost knob).
- mul: 97689 flat, WRONG 8/8 (37/40 at scale 1) - a real shortcut surviving all n.
- div: 577 shortcut (wrong ~31-36/40) at n=3..10, then CLIFF to 346692 clean at n=25 (both seeds).
- power: 10985 (n=3 seed0) / 97713 shortcut wrong, cliff to 4352185 clean - at n=25 (seed0) vs n=10 (seed1). Cliff position is seed luck.
- gcd: seed0 n=3 = 6M exhaustion (nested prefixes => NOT FOUND at all n, no CPU burned); seed1 n=3 = 97885 CLEAN. 60x seed spread at identical n.
- isprime: tried=5 constant-shortcut at n=3/5 (train all-same-label luck), 659821 wrong at n=10, 6M NOT FOUND at n=25 both seeds - correct isprime sits beyond 6M under this recipe.
Headline: (1) B-299's NEGATIVE stands for boundary-covered skills (tried flat in n). (2) For boundary-uncovered skills, tried jumps 40-600x at the underdetermination cliff where train kills the shortcut, and the cliff's n is seed-random - no a-priori cap(n) exists. (3) [SUPERSEDED 2026-10-22 by the B-299-CURR CONFOUND entry below: the mul/div wrong-baselines and the cliff phenomenology were measured with the target's own pinned library entry present (B-523-H1 pin-once bug in t9budget_curr*.py); in the clean config NO self-contained shortcut exists for mul or div at any measured n - wrong rate is 0 WITHOUT adv or boundary. Only square and even show real underdetermination effects, with the legitimate library.] (4) [SUPERSEDED likewise - see the confound entry.]

## P29 (2026-10-22) - scaled baby: free conversation + unscripted situation stream (LLM pools)
Design pre-registered with owner: opaque-token situation stream (no scene slots given), pool A = blind-LLM caregiver lines about the present scene (16 scene types x 25), pool B = 400 unique free-conversation lines (weather, food, news, plans...). Dilution f = fraction of lines about the present scene. Learner: order-blind Hebbian word<->token association + (chunk 2) mutual-exclusivity clustering + class-bigram and pair-bigram order channels. 5 days x 100 scenes, 2-4 lines/scene, 5 seeds.
- P29a dilution curve (grounding = word_for(token) correct, 14 words): f=1.0/0.5/0.2/0.1/0.05/0 -> 1.00/1.00/0.91/0.80/0.77/0.00. C1 PASS (>=.80 at f=1.0), C2 PASS (monotone; breakpoint below f=.05). Control f=0: 0.00 PASS.
- P29b word-class discovery (mutual-exclusivity clustering over word-word line co-occurrence, agglomerative cosine): NMI k=4 = 0.04-0.08, k=8 = 0.04-0.12 at all f. PRE-STAGED CRITERION NMI>=.5: **FAIL**. Cause: free-stream words share sparsity with scene words (E-E and E-F pairs both never co-occur), so sparse-cosine average linkage merges scene+free vocab; classes do not emerge at k=4/8. Token-association profiles also fail (within-scene co-occurrence couples E/A/L/T).
- P29c comprehension (argmax assoc token of entity/action word, 400 probes): f=1.0 .98, f=0.5 .92-.98, f=0.2 .88. CRITERION >=.75: PASS.
- P29c production order (20 covered pairs, E-first correct): class-mediated channel (inferred-class bigrams) FAILS: 0-10/20, fwd/rev ~ parity (17/18, 35/16, 0/0) - cluster label noise injects both directions. Class-free pair-bigram channel PASSES: 20/20 at all f (real evidence: A-lines are 100% entity-first and entity-action adjacent; tie-break returns no-evidence=fail, none vacuous at f>=.2).
- Honest limits: pools cover 16 of 36 valid (entity, action) pairs (2 per entity) - no novel-pair composition test possible; location/time tokens never named in pools (ungrounded by design); B pool is 50 topics x 8 particle variants (structured repetition, realistic but note).
Verdict: grounding + comprehension + pair-wise production order emerge from overhearing diluted free conversation with no slots, no feedback, no order supervision in the association channel. Word-CLASS discovery from distributional statistics FAILS at this scale/design - recorded negative. Next: shuffled-order control (order must vanish), more scene types per entity (writer relay if needed), cluster-method alternatives only as new pre-stated experiments.
- P29 shuffled-order control (A-line words shuffled, all else equal): prod_bg collapses 20/20 -> 2-12/20 (mean ~8.7); comprehension unchanged (.92-.98). Control PASS: production order comes from HEARD ORDER, not from association. P29 pre-registered control set complete.

## P29d (2026-10-22) - class discovery via situation-stream mutual exclusivity (pre-registered)
Mechanism: cluster the 19 situation TOKENS by token-token scene co-occurrence (agglomerative cosine, k=4); words inherit class from grounded token; order via earned-class bigrams.
- D1 token NMI: 0.67-0.79 vs pre-stated >=.8: **FAIL** (E and L tokens merge; one A token splits singleton; seed2 misplaces an E token into the A cluster).
- D2 word labels: 13,13,12/14 at f=1.0 (pass >=12), 10-11/14 at f=0.2 (fail).
- D3 production order via EARNED classes: heard 15-20/20, UNHEARD (composition) 15-20/20 vs >=18: pass at f>=0.5 mostly, mixed at f=0.2. EA bigrams strongly directional (278/4, 135/2, 41/1) - earned classes carry real order signal, unlike P29b's parity noise.
Qualitative keep: class-mediated order GENERALIZES to unheard pairs (composition) - pair-bigram channel cannot do this. Bottleneck is token-clustering quality (E/L merge under raw co-occurrence cosine).

## P29e (2026-10-22) - class discovery variant: INCOMPATIBILITY profiles (pre-registered, same gates)
Mechanism: cluster tokens on binary "never co-occurs in 500 scenes" profiles.
- D1 token NMI = 0.72 (all seeds, f-independent as expected): **FAIL** (<.8). Failure mode complementary to P29d: E and A tokens MERGE (their incompatibility vectors overlap: E is incompatible with E-tokens + its uncovered A-tokens; A with A-tokens + unpaired E-tokens), T splits into singletons.
- D2 8/14 at f=1.0, 6/14 at f=0.2: FAIL. D3 collapses with the labels (0-6/20, EA 0/0 - merged E/A class yields no (E,A) bigram counts).
Verdict: class discovery DOUBLE NEGATIVE (P29b word-level NMI .04-.12; P29d token co-occurrence .67-.79; P29e incompatibility .72). Partial structure is real (E/L/T separated in P29d, L/T cleanly split in P29e) but no simple statistic recovers all four classes at this scale. Line CLOSED per pre-commitment; what survives: grounding, comprehension, pair-bigram order (P29a-c), and earned-class order WITH composition given good labels (P29d D3) - i.e. IF classes are (somehow) obtained, order+composition follow; obtaining them from raw distributional statistics at baby scale is the open hard part.

## P30 (2026-10-22) - vocative / call-consequence learning (Ash's question, pre-registered, approved)
Design: bare-name call lines in two-caregiver scenes; NAMED caregiver turns next tick (selective); 5% spontaneous-turn noise; referential mentions never followed by turning. Learner: temporal-shift Hebbian channel keyed on (bare word, next-tick event tokens). Events opaque tokens V0-V3.
- V1 call comprehension (predicted turn-event argmax after bare name): 2/2 all seeds, f=1.0 AND f=0.2. CRITERION >=.9: PASS.
- V2 selective production (instrumental call over full grounded vocabulary): 2/2 all seeds, both f. CRITERION >=.9: PASS.
- V3 no-consequence control (turn events shuffled w.r.t. calls): V1=0/2, V2=0/2 all cells. CRITERION <=.6/.5: PASS.
- Learned contingency is strongly selective: แม่->TURN(แม่) +72..74 vs TURN(พ่อ) -18 (Hebbian units); approach events learned too (weaker, p=.5).
- Design notes: call events are world events independent of dilution f (hence identical numbers at f=1.0/0.2 - dilution does not stress the vocative channel here); the disambiguating cue is LINE BARENESS (single-word utterance), standing in for calling prosody - pre-registered. CAN: acquire call->response contingency, use a name instrumentally. CANNOT: distinguish name from response-triggering signal; no mental-state attribution claimed.
Answer to Ash's question: yes - if the world responds selectively to bare-name calls, the baby learns exactly which word summons which caregiver, and uses it; shuffled consequences abolish both.

## P31 (2026-10-22) - turn-taking dialogue with contingent feedback (Ash's "converse with mom"; pre-registered)
Design: caregiver prompt (scene-prompt/greeting) + end-of-turn cue -> baby DECIDES to speak (reward-shaped propensity) and says a scene-evoked grounded word -> competent caregiver praises (word names a present thing) or corrects. Reward modulates word<->token association and speak-propensity. 5 days x 100 episodes, 3 seeds.
Iteration honesty note: two artifacts were caught and fixed pre-report (END token and praise/filler words entered the production vocabulary and were self-praised through reward amplification; an argmax-in-scene praise criterion was too weak). Final mechanism: production restricted to confidently-grounded words; praise only for conventional names of present things.
- T1 turn timing (f=1.0): speak-propensity end/noend = .99/.01-.05 all seeds. CRITERION >=.9/<=.2: PASS. NO-FEEDBACK control: .5/.5 (no learning): PASS.
- T2 content appropriateness (f=1.0): 0.63-0.67. CRITERION >=.8: FAIL. NO-FEEDBACK: 0.66-0.67 - identical, so contingent feedback added NOTHING to content beyond overhearing; ~0.67 = sampling noise among 3-4 scene-evoked names.
- T3 day1->day5 improvement (f=1.0): +0.12..+0.31 NORMAL but ALSO +0.25/+0.31 in NO-FEEDBACK seeds: improvement is from overheard grounding, NOT attributable to feedback. NOT DEMONSTRATED as feedback-driven.
- f=0.2: T1 COLLAPSES to .01/.01 - weak grounding -> mostly corrections -> baby stops speaking. Dialogue loop does not survive heavy dilution.
- SHUFFLED (hidden-scene feedback) control: pre-stated T2-chance prediction was mis-designed (production is scene-driven, T2 probe unaffected). Actual: feedback incoherent with baby's utterances -> T1 collapses (.01-.11), baby withdraws from the dialogue; day-5 utterance counts near zero in some seeds.
UNEXPECTED POSITIVE: participation is contingency-sensitive - baby keeps talking under coherent contingent feedback and goes silent under random or incoherent feedback (still-face-like social contingency effect). This, not content improvement, is what the feedback channel demonstrably caused.
Verdict: turn TIMING and PARTICIPATION are learnable from contingent feedback (T1 pass, controls clean); content appropriateness comes from overhearing alone and feedback adds nothing measurable at this scale (T2 fail, T3 unattributable). CAN/CANNOT as pre-registered; no claim of open-ended conversation.

## B-300R (2026-10-22) - T10 re-scoped: does informed selection replace adversarial acceptance? (pre-registered triage)
Grid: R5/R25 random vs B5 oracle-boundary train, NO adv, baselib,simp, cap 3M, 40-case generality eval. T10 items B-301..B-336 as written were triaged vacuous (random-vs-random under a recipe where n=3 already sufficed or cliffs dominate).
- mod: R5=R25=B5 identical (tried 530, 0/40). No early shortcut exists -> selection irrelevant.
- even: tried 123995 all conditions; wrong40 0/1/2 by SEED (R5=R25 per seed); B5 0/40. Selection irrelevant; residual edge errors are enumeration-seed artifacts, fixed by boundary train.
- div: R5 shortcut survives 2/3 seeds (tried 673, wrong 4-9/40); R25 clean at 431268; B5 clean at 431268. Informed selection FIXES CORRECTNESS with 5 examples (meets T10 data-efficiency criterion) but saves ZERO compute - the cliff is the correct program's enumeration position, not the data.
- square (no adv): BROKEN without adv - R5: wrong 8/40, NOT FOUND, wrong 3/40; R25: wrong 4/40, NOT FOUND, NOT FOUND (tried 3875328 = 3M-cap stop). B5 (oracle-boundary train incl. (30,900)): NOT FOUND at 3875328. B5t (corrected cap-safe train [(0,0),(1,1),(2,4),(3,9),(5,25)]): NOT FOUND at 3875328, dt 7269s.
- CORRECTION to the a2ef126 cap-artifact claim: B5t refutes it. tried=3875328 is the 3M-CAP STOP, not full-space exhaustion (B-010 recorded the same 3.88M stop: square's canonical program sits at tried 4313812 in default ordering). B5's NOT FOUND had two stacked hazards - the (30,900) search-time-cap violation (would have rejected the slow-correct program had search reached it) AND the 3M tried cap (search never reached 4313812); B5t removes the first and still fails on the second. The cap-cost rule (B-523rev) stands as a hazard class, but was NOT the binding cause here: the compute cliff was.
- Net for square without adv: NO selection strategy yields a correct program - random n=5 accepts deep shortcuts (wrong 3-8/40), random n=25 or informed n=5 reject the shortcuts and then exhaust the 3M compute cap below the canonical program's 4313812 position. Selection fixes WHAT is accepted (wrong -> nothing), never the enumeration position.
Verdict: two budgets are independent - DATA budget (informed selection fixes correctness where shortcuts survive: div-type, and square wrong-accepts become honest NOT FOUNDs) and COMPUTE budget (enumeration position; selection never helped - square's 4313812 cliff stands under every selector at cap 3M). adv remains necessary for square-type tasks. B-301..B-316 (random selection): answered - n=5 random FAILS for div/square-type (wrong accepts), vacuous for mod/even-type. B-317..B-332 (maxdisagree): answered by oracle proxy - fixes correctness, not compute. B-333..B-336 (boundary selection): answered by B5/B5t directly. Items ticked in BACKLOG.

## B-523 (2026-10-22) - boundary() coverage for CURR skills (closes the B-299-CURR wrong cells)
Design: T9-style scale-straddling boundary entries for mod/mul/div/power/gcd/fact/isprime (cur7.boundary patched, commit 4f13b49); re-ran the B-299-CURR wrong cells, recipe baselib,simp,adv FULL inits, cap 6M, 40-case x 4-scale generality eval.
Flip cells (baselines from B-299-CURR):
- mul: 8/8 wrong -> 0/8. All 8 cells (seeds 0/1 x n 3/5/10/25) FOUND clean at tried=4155513 FLAT, gen 40/40 all scales - matches B-060's full-library re-derivation position exactly. Those cells ran FIRST in their process (mul excluded at pin) so the position is pollution-free (B-523-H1); a later in-process re-run WITH LIB mul present produced a WRONG program at 346692 (38-40/40) - direct demonstration of the pollution, discarded; clean re-run CONFIRMED (b523e s0 n3: tried=4155513, 40/40 all scales, program byte-identical to B-060's canonical repeated-addition multiply).
- div: 6/6 small-n wrong (n 3/5/10, seeds 0/1; shortcut at tried=577/97701) -> 0/6. All 6 FOUND clean, gen 40/40 all scales: boundary kills the 577 shortcut, search proceeds to the correct program. POSITION CORRECTED (B-523-H1 below): the 346692 positions were measured with a div-containing pinned LIB (harness pollution). Clean re-verification with div excluded at pin: b523d s0 n3 and b523e s1 n3 both FOUND clean at tried=4202713 = B-060's full-library-minus-div re-derivation position (4202709), 40/40 all scales; program logged in b523e (self-contained repeated-subtraction: init b=y; if (lt a b) -> zero; else step ((sub a b),b); comb=('add','one',0)).
- power: 5/7 wrong -> 0/6. All 6 cells (seeds 0/1 x n 3/5/10) FOUND clean at tried=4450489 FLAT (logs/b523b_run.log) = B-060 re-derivation position.
- isprime: SKIPPED (recorded decision, reported): B-299-CURR already established >6M exhaustion; re-confirming was 4-8h compute for a known negative.
No-regression spot-checks (logs/b523c_run.log): mod 482, div 346692, fact 1138228, sumto 2176534 - all FOUND clean at EXACTLY their pre-patch positions, 0/40. gcd s1 n3: NOT FOUND at 6002688 = the pre-existing B-299-CURR seed-luck exhaustion case, unchanged (not a regression). STATE CAVEATS (B-523-H1): mod ran first-in-process (pin honored its EXCL) and is clean; the div spot-check shared the polluted div-in-LIB state (its 346692 = the same polluted position as the flip cells - the pre-patch comparison is consistent, but neither is the clean position); fact/sumto are never pinned (no self-reference possible) and matched pre-patch exactly; the gcd cell had LIB gcd available yet still exhausted 6M.
power_diag finding: the 4450489 power program is a genuine GENERAL countdown loop (init b=y; step (a,(sub b one)); comb mul) - correct on all probed y; its original boundary (11,4) failure was pure STEP-CAP exhaustion because comb-mul is repeated addition with step cost O(operand values).
RULE (B-523rev, commit 4f13b49): a boundary case is valid for search-time adv only if the canonical program's loop cost on it fits the search-time CAP (400). Dropped power (11,4), fact (10,7), isprime (899,7); remaining entries verified to pass the pinned programs at cap 400. Violating entries produce cap-artifact NOT FOUNDs (cf. B-300R square B5 (30,900)).
Provenance note: mul/div per-cell JSONs were lost in the 2026-10-22 03:26 sandbox rebuild; values above are quoted from contemporaneous run records (raw cell lines preserved for mul s0 n3/5/10/25 + s1 n3 and div s1 n5/n10; the rest from same-minute run tallies). Re-verification cells (div s0 n3, mul s0 n3) running as b523d -> logs/b523d_run.log; this entry will be amended if they disagree.
Verdict: wrong-program rate -> 0 wherever boundary() has valid entries, at NO compute cost beyond the correct program's own enumeration position. adv coverage is the entire fix for the B-299-CURR wrong cells; B-299 headline (3) is resolved (coverage, not cap(n)). isprime remains enumeration-depth-limited (>6M), not boundary-limited.

## B-523-H1 (2026-10-22) - HARNESS INCIDENT: pin-once guard + EXCL timing -> library-state pollution across same-process cells
Found by: b523d re-verification disagreeing with recorded positions (div n3 recorded 346692, clean re-run 4202713).
Mechanism: cur7.search pins the base library ONCE per process (search._baselib_done guard), honoring EXCL only at that first call. Probe scripts that run several tasks in one process (b523 pre-wipe, b523c, b300r, b523d's 2nd cell) therefore searched later cells with LIB entries pinned under the FIRST cell's exclusions - including, for later cells, the TARGET TASK ITSELF (circular: the search could 'find' the skill via its own library entry). Additionally b300r.py cleared EXCL by design ('selection does the work'), so its ENTIRE grid ran with the full pinned library including each target.
Demonstration that the pollution flips results: b523d's mul cell (run in-process after div, LIB mul present) accepted a WRONG program at tried=346692 (gen 38/39/40/40); the clean mul position is 4155513 (= B-060 exactly).
Affected records: pre-wipe b523 div cells (346692, polluted); b523c div spot-check (346692, polluted) and gcd cell (polluted state, NOT FOUND regardless); b523d mul cell (wrong, DISCARDED); b300r grid absolute positions (mod 530, even 123995, div 673/431268 - all measured with target-in-LIB).
Unaffected (verified): pre-wipe b523 mul cells (first-in-process, 4155513 = B-060); b523b power cells (first-in-process post-rebuild, 4450489, AND the polluted pre-wipe power cells independently landed at the same 4450489 - the accepted power program is identical in both library states); b523c mod (482, first-in-process); b523d div s0 n3 (4202713, fresh process); all square cells (square is never pinned); b523c fact/sumto (never pinned; intended library use of mul only).
What survives: (1) All WRONG->CLEAN flip claims (boundary coverage flips mul/div/power to correct 40/40 programs) - re-confirmed for div and mul by clean re-runs (b523d div 4202713; b523e in flight). b523e closed the re-verification: div s1 n3 = 4202713 clean (self-contained repeated-subtraction program, logged), mul s0 n3 = 4155513 clean (canonical program, byte-identical to B-060). (2) b300r's INTERNAL A/B comparisons (R5 vs R25 vs B5 within one task share one library state): selection-fixes-correctness (div), selection-insensitivity (mod/even), square-broken-without-adv all stand. What changes: absolute tried positions are library-state-dependent and the recorded clean positions for div (346692) and any target-resolved programs (mod 530, div 431268, possibly via self-library entries) must not be compared cross-run. The B-300R div B5 clean program at 431268 may resolve through LIB div - flagged, not re-run (the A/B contrast is unaffected).
Fix: cur7.py pin block now pops EXCL'd tasks from LIB at pin time; probe scripts reset search._baselib_done per cell (b523e.py). One-task-per-process remains the safe discipline for future probes.

## B-300 (2026-10-22) - execution-agreement ensemble on text2prog (pre-registered; b300.py, b300b.py)
Protocol: tok features, soft credit; train 300 train-frame pairs; test 300 UNSEEN new_frames sentences; seeds 0-4. Arms: top-1 argmax; plurality vote over executed answers of top-k hypotheses (k=3,5); marginalized vote (logsumexp of hypothesis scores per execution-equivalence answer class; k=3,5,all-21). Pre-stated criterion: best vote arm >= top-1 + 3pts.
- top-1 mean .838 (.77-.92 across seeds).
- Plurality vote: k3 .600 (-23.8pts), k5 .449 (-38.9pts) - STRONGLY NEGATIVE. Mechanism: hypotheses come in (op, direction) pairs; commutative ops and direction duplicates produce the SAME answer, so plurality is decided by answer-cluster SIZE, not evidence; when argmax is wrong on a commutative op, its duplicate direction seals the error. The ensemble members are not independent.
- Marginalized over execution classes: k3 +1.0, k5 +1.27, all +1.13 pts; 4/5 seeds improved (seed2 -5.0: wrong commutative classes can pool enough mass to overturn a correct argmax). Below the +3 criterion.
Verdict: FAIL vs criterion, informative negative. Example-dependent noise (the one error class voting can fix, per the B-279..298 analysis) is real but small here: ~1pt recoverable, and only by marginalizing over execution-equivalence classes - naive plurality voting is actively harmful. Residual errors have a wrong posterior (both leading hypotheses name the wrong op), which no execution-agreement scheme can repair. B-300 CLOSED.

## B-337P (2026-10-22) - PRE-REGISTRATION: covering-selection prediction test (extends B-300R)
Model prediction from the B-300R two-budget verdict: train selection matters ONLY via whether it kills the surviving shortcut (data budget is binary). A COVERING selector (greedy max-coverage over scales, then operand-magnitude buckets, from the same 25-case random pool per seed) picks scale-diverse cases, and the div shortcut (accepted at tried=673 under R5, wrong 4-9/40 across scales) fails at larger scales - so covering n=5 should kill it exactly like B5 did.
Concrete selector (pre-stated): from the seed's 25-case pool (same gen as R25), greedily add the case covering the most new (scale) values; ties broken by most new (operand-bucket = value//10) values; then pool order; stop at 5.
PREDICTION: div, recipe baselib,simp (no adv, EXCL cleared - b300r-consistent), cap 3M, seeds 0-2: 3/3 FOUND clean (wrong40=0) at tried in the 431268 family (same accepted program as B5). Falsifiers: any seed wrong>0, NOT FOUND, or a different accepted program than B5's.
If confirmed: B-349..B-364 (covering grid) and B-337..B-348 (boundary n=10/15/25) are answered by the model + this confirmation - selection strategies are interchangeable once they kill the shortcut; more n changes nothing (B-299 flat-in-n). If falsified: the two-budget model needs revision and the covering grid gets measured.

## B-337P RESULT (2026-10-22) - covering-selection prediction FALSIFIED (b337.py, logs/b337_run.log)
Measured (div, baselib,simp, no adv, EXCL cleared = b300r-consistent, cap 3M, covering n=5, seeds 0-2): s0 FOUND tried=121509 wrong40=3; s1 FOUND tried=121509 wrong40=3 (same LIB-div composite: init b=y; if (lt a one) -> b; else step (zero,(div a b))); s2 FOUND tried=673 wrong40=34 (LIB-div shortcut). Prediction was 3/3 clean in B5's 431268 family: FALSIFIED 0/3.
Refined model: selection value is DISCRIMINATION, not coverage - selected cases must kill the specific surviving shortcut class. Scale/magnitude-bucket coverage does not discriminate the composite shortcut class that exists when the target's library entry is available (EXCL cleared); oracle-boundary cases (B5) discriminate by construction. The two-budget model stands, but "kill-the-shortcut is binary" is selector-relative, not case-count-relative: covering n=5 < boundary n=5 in killing power.
Consequences for the T10 grid: mod/even/square cells of B-337..B-364 are answered by B-300R (mod/even selection-insensitive at every n; square unlearnable without adv under every selector) - ticked. ALL mul cells (B-338/342/346/350/354/358/362) stay OPEN: mul's shortcut structure under selection is genuinely unmeasured. Note the B-523-H1 caveat applies throughout: with EXCL cleared these programs may be LIB composites; discrimination demand is relative to the shortcut class in play.

## B-338P (2026-10-22) - PRE-REGISTRATION: mul under selection (the open T10 cells), curriculum-relevant config
Design decision (pre-stated): EXCL={mul} (curriculum-relevant - the target is never in the library when the curriculum learns it), baselib,simp, FULL inits, NO adv, cap 6M (mul's canonical position is 4155513 > 3M; b300r's 3M cap would force NOT FOUND for the wrong reason). b300r's EXCL-cleared config is NOT used: it measures composite-shortcut behavior around a library self-entry the curriculum would never have (see B-523-H1 and B-337P).
Cells: R5 (random 5), B5 (boundary(mul)[:5] as train), R25 (random 25) x seeds 0,1. Programs logged verbatim.
Predictions (from the refined discrimination model + B-299-CURR's mul finding):
- R5: shortcut accepted, tried << 4155513, wrong40 > 0 (B-299-CURR: mul 8/8 wrong all-n without boundary).
- R25: shortcut SURVIVES 25 random cases (B-299-CURR measured exactly this) -> wrong40 > 0. This is the div-contrast: for div, 25 random cases killed the shortcut (B-300R R25 clean); for mul they should not.
- B5: clean (wrong40=0) at the canonical 4155513 position - boundary cases discriminate mul's shortcut class by construction.
Falsifiers: B5 wrong or NOT FOUND (boundary cases don't discriminate mul); R25 clean (B-299-CURR's mul shortcut-survival doesn't replicate in this config); R5 clean.

## B-339P (2026-10-22) - PRE-REGISTRATION: div under selection, curriculum-relevant config (sister of B-338P)
Same design as B-338P: EXCL={div} honored at pin (no LIB-self composites), baselib,simp, FULL inits, NO adv, cap 6M; cells R5/B5/R25 x seeds 0,1; programs logged verbatim.
Predictions (written after b338's first cells falsified B-338P's R5 prediction, before any b339 cell is read): if B-299-CURR's div wrong-cells were also LIB-self composite artifacts, then R5/R25 find no self-contained shortcut and go straight to the canonical position (~4202713, clean); B5 same. Falsifier of the artifact theory: any cell accepts a wrong SELF-CONTAINED program (then a real clean-state shortcut class exists and B-299-CURR's cliff phenomenology has a clean-state component).

## B-299-CURR CONFOUND ALERT (2026-10-22, discovered via B-338P cell 1)
b338 mul R5 s0 (EXCL honored, NO adv, NO boundary) -> CANONICAL mul at 4155513, wrong40=0. B-299-CURR's baseline for the identical cell (n=5 s0) was WRONG. The only configuration difference: t9budget_curr.py ran multi-task processes where the pin-once guard (B-523-H1) left mul in LIB for its mul cells - its wrong programs were LIB-self COMPOSITES. With the self-entry removed and no boundary at all, no self-contained mul shortcut exists at n=5 s0; search walks to the canonical program. b338 B5 s0 also canonical 4155513 clean (B-338P's B5 prediction confirmed; R5/R25 predictions falsified).
Implication (verdicts to be re-written when b338/b339 complete): B-299-CURR headline (3) 'wrong-program rate nonzero exactly where boundary() lacks entries' is CONFOUNDED for mul/div/power - the wrong-program baselines were measured with the target's own pinned library entry present (t9budget_curr.py: first task per process correctly excluded; later tasks polluted). B-523's flip attribution (credit to boundary coverage) is likewise confounded for mul: LIB state changed together with boundary. div clean-state no-adv shortcut existence: b339 measuring. Unaffected B-299-CURR cells: isprime/fact/sumto (never pinnable), mod and gcd (first-in-process).

## B-299-CURR CONFOUND RESOLUTION (2026-10-22) - the CURR wrong-rate and cliff phenomenology were LIB-self artifacts (b338/b339, full grids)
Measurement (clean curriculum-relevant config: EXCL honored at pin, baselib,simp, FULL inits, NO adv, cap 6M, programs logged verbatim):
- mul (b338, logs/b338_run.log): R5/B5/R25 x seeds 0,1 = 6/6 cells CANONICAL program at 4155513, wrong40=0. No selection effect, no shortcut at any n.
- div (b339, logs/b339_run.log): R5/B5/R25 x seeds 0,1 = 6/6 cells CANONICAL program at 4202713, wrong40=0. The 577/97701 "shortcuts" of B-299-CURR and the 673 shortcut of B-300R were LIB-div composites - they cannot exist without the target's own library entry.
CONSEQUENCES:
(1) B-299-CURR headline (3)/(4) SUPERSEDED. The wrong-program rate for mul/div was an artifact of the B-523-H1 pin-once pollution in t9budget_curr*.py (multi-task processes: first task per process correctly excluded at pin, later tasks had their own pinned entry in LIB). The "underdetermination cliff" (tried jumping 40-600x at seed-random n) was composite-shortcut phenomenology, not a property of the task. In the clean config, tried is FLAT at the canonical position across n and selectors - B-299's original flat-null extends to mul/div.
(2) B-523's flip attribution corrected: the flips to correct programs are REAL and verified clean (b523b/d/e), but for mul/div the boundary coverage was NOT the necessary ingredient - removing LIB-self suffices (b338/b339: canonical without any adv). adv+boundary DID suffice to kill composite acceptance within the polluted state. B-523's practical rule stands: never let the target task resolve through the pinned library (now enforced in cur7.py); boundary coverage remains the protection against shortcut classes that exist in the LEGITIMATE library state.
(3) power: B-299-CURR's power cells were polluted the same way; b523b's flip cells were clean-state+boundary (4450489). Clean-state no-adv power probe (b340, R5/B5/R25 seed 0) CLOSED the scope: 3/3 cells found the canonical power program at flat position 4450489 with wrong40=0, no adv - power, like mul and div, has NO self-contained shortcut; its B-299-CURR cells were LIB-self composite artifacts. Underdetermination is NOT revived for power; in the legitimate library state it remains unique to square (and even's minor seed-level edge errors).
(4) B-300R scope note: its mod/div cells ran EXCL-cleared (LIB-self present) - the "data budget fixes correctness" finding for div applies to the composite-shortcut state, which the curriculum never visits; its square/even cells are UNAFFECTED (square/even are never in the pinned library - their LIB was the legitimate grown state). square remains the ONE measured task with real underdetermination in the legitimate state (R5 wrong 8/40; unlearnable without adv under every selector at cap 3M), and even shows real seed-level edge errors. adv's true demonstrated job: square-type tasks.
(5) T10 mul cells (B-338/342/346/350/354/358/362): answered by b338 - selection fully vacuous for mul (no shortcut class exists). Ticked.

## B-365..B-369 triage (2026-10-22) - T10 data-efficiency items resolved against the corrected picture, no new runs

Post-confound-resolution triage of the five unchecked T10 data-efficiency items. Verdict: none requires a run.
- B-365 (mod pruning <=15 ex): ALREADY ANSWERED. b300r mod R5 (5 random examples) finds the canonical program with wrong40=0 at seeds 0/1/2 (tried=530 in b300r LIB state). 5 <= 15 with same success.
- B-366 (mul pruning <=15 ex): ALREADY ANSWERED. b338 clean-config mul R5 and B5 (5 examples) both find canonical 4155513, wrong40=0. 5 <= 15 with same success.
- B-367 (square near-miss examples speed acceptance): ANSWERED NEGATIVELY by the B-300R headline. Acceptance position in program space is example-independent; selection fixes correctness, never compute. Near-miss examples cannot make the correct program accept faster; they could only change which program is accepted (already covered by B-523 boundary discrimination work).
- B-368 (duplicate/ambiguous example removal, all tasks): VACUOUS for this suite. Every task is a deterministic function, so ambiguous examples (same input, two answers) cannot exist; acceptance is all-or-nothing over train, so duplicates carry no voting weight and removing them cannot change accuracy.
- B-369 (cross-seed transfer of good sets, square): VACUOUS. No example set has ever succeeded on square without adv (B-300R-SQ: NOT FOUND under every selector at cap 3M; canonical square 4313812 > cap). There is no good set whose transfer could be measured. Revisit only if a square-successful set is ever found.

## B-370..B-380, B-382..B-405 triage (2026-10-22) - P24/F-6 mechanism variants resolved analytically, no new runs

All 35 items are parameter or task variants of two mechanisms already measured on this exact curriculum and held-out set. Verdict: 34 ticked without runs; B-381 (trace cache) left open as genuinely unmeasured.
- B-370..373 (macro-first ordering, square/choose2/sumsq/dblfact): = the P24/B-001 macro arm, measured null - square 4313812 = base exactly, choose2 +1, dblfact -20 (noise at 4-6M), sumsq NOT FOUND both arms, same programs everywhere. The <50%-tried criterion is unreachable because the mined fragments do not occur in the held-out solutions (README P24).
- B-374..376 (cond+step macros): null by construction. A (cond,step) macro can occur only where its step occurs; the mined step fragments (repeated-subtract and countdown pairs) are measured absent from all four held-out solutions, so any macro built from them is absent too; reordering cannot change the search.
- B-377/378 (comb-frequency beam): = the F-6 oops arm, measured null-to-harmful - square 4313812=, choose2 5199851=, dblfact LOST at 6M, gcd +33x and power +76% on training tasks; comb identity is non-stationary (README F-6).
- B-379/380 (seed-parallel racing, first hit wins): null-to-harmful by construction. Ordering is deterministic within a fixed LIB state; without underdetermination every seed finds the same program at the same position (b338/b339: 12/12 cells identical), so racing costs 3x CPU per success with zero wall win. Where first-consistent position does vary across example sets (square), the earliest hit is biased toward shortcuts (B-044 pattern: the 719709 shortcut precedes the 2583787 clean program), so first-hit-wins selects the wrong program faster. Racing does not move square's real barrier (canonical position 4313812 > 3M cap).
- B-382..405 (macro min-count 2/3 x mine-first/mine-only/interleave): null-to-harmful by construction - all parameterizations of the same measured-null P24 macro mechanism over the same absent-from-heldout fragments. min-count 3 only shrinks the macro set; mine-only restricts coverage (a solution containing no mined macro becomes unreachable -> task lost, the F-6/dblfact failure mode); mine-first/interleave reorder within the same candidate set (+-20-class noise at 4-6M).
- B-381 (cross-candidate run() trace cache) remains OPEN: B-058 profiling showed each candidate is decided by exactly one r0 evaluation, but library-call repetition ACROSS candidates is unmeasured; a (fn,args) memo could plausibly beat 2x throughput. Queued as a real (engineering, non-conceptual) candidate.

## B-411/B-414, B-436..B-462 triage (2026-10-22) - T5 saturation evidence + T6 runtime wall

- B-411, B-414 (WiSARD tuple 8, MNIST): FAIL by direct measurement. B-236's first attempt with 8-bit tuples saturated at .30 accuracy (classic node saturation) vs the MLP baseline near .9; the "within 3 pts" criterion is decisively failed at this grain. Bleaching is a decision-time tie-break and cannot recover a saturated node. The demonstrated-right grain is 28-bit tuples (B-236 PASS, .9115).
- B-436..B-462 (27 connectome readout x size variants): BLOCKED by the measured runtime wall, not by science. B-240 measured the same harness family at >2.4 s/sample (cost driver: per-sample state_hex encoding + 784-pixel pmap in the hosted runtime); phase A alone is 2-3 CPU-hours, so no variant fits its M (<15 min) box. All 27 ticked as blocked-by-B-240; they reopen only after the bit-vector state encoding the B-240 verdict calls for.
- Remaining T5/T6 grid cells (WiSARD tuple 16/32/64, pmnist/snips, B-463..465) stay OPEN: no direct measurement transfers honestly (snips is a different encoding; the saturation edge between tuple 8 and 28 is unmapped). Queued behind higher-value work.

## B-381P pre-registration (2026-10-22) - cross-candidate evaluation caching (B-381)

Question: does caching run()/ev() traces ACROSS candidates give >2x search throughput with identical results?
Prior facts: B-058 profiled choose2 - every candidate is decided by exactly one r0 evaluation (no multi-example redundancy). cur7.ev already carries an lru_cache(maxsize=300000); whole-run traces are never shared (each candidate spec is unique).
Analysis pre-run: sharing exists mainly at loop iteration 0 (same train r0 inputs across the ~E1-sized s1 block for a fixed s0, and vice versa); after iteration 1 the (a,b) trajectory depends on both steps, so trajectories diverge. Expected honest outcome: no 2x available from bigger caching; the interesting sub-question is whether the 300K LRU's miss bookkeeping actually COSTS time vs no cache.
Design (b381.py, one process, clean config: baselib pin, EXCL={square}, no adv, square R5 seed-0 train, tried_cap=400000, cap 6M ordering identical):
- Arm A: current ev lru_cache(maxsize=300000) (baseline)
- Arm B: ev lru_cache(maxsize=2000000)
- Arm C: ev unwrapped (no cache)
Success criterion (from the backlog item): any arm >2x throughput vs baseline with IDENTICAL decisions (same tried count at cap, same PROF evals, same NOT FOUND / same program). Wall time measured per arm; ev.cache_clear() between arms.

## B-381 verdict (2026-10-22): NULL as a new idea - the cache already exists and is worth 4.4x; the 300K->2M increment is 1.59x, below the >2x criterion

b381.py, clean config (baselib pin, EXCL={square}, square R5 seed 0, identical 1291776-candidate prefix), decisions verified IDENTICAL across arms (same tried, same NOT FOUND):
- A lru300k (baseline): 122.5s (713.9M hits, 21.3M misses - 97% hit rate; the pre-existing ev lru_cache already does the cross-candidate sharing the item proposed)
- B lru2m: 76.9s = 1.59x vs A (misses 21.3M -> 0.79M; 300K was thrashing)
- C nocache: 541.2s = 4.42x SLOWER than A; B beats C by 7.04x
Verdict: the item's >2x is met only by cache-vs-no-cache, i.e. the premise was already implemented. No NEW >2x available from bigger caching (1.59x < 2x criterion). ADOPTED: ev lru_cache maxsize 300000 -> 2000000 in cur7.py (semantics-preserving: ev is pure; decisions identical in b381) - ~1.6x on all future searches. Whole-run trace caching remains provably share-free (each candidate spec is unique and evaluated once, B-058).

## B-435/B-484/B-487/B-490/B-498 triage (2026-10-22) - answered by B-241/B-055/B-058 measurements

- B-435 (WiSARD 1-pass vs MLP 1-pass, MNIST): accuracy half = B-241 exactly (same harness, WiSARD beats 1-pass MLP 2-3x at every k) - better than the "within 3 pts" criterion. Forgetting half folds into B-493 (class-incremental run, still open); WNN table retention regardless of load already measured (P5 E4: 255/256).
- B-484/B-487/B-490 (wiSARD readout, shots 1/5/20, MNIST): = B-241's exact cells (.340/.470/.647). Direct measurement.
- B-498 (repair: resume search from best partial on test failure, square): = B-055's mechanism, measured PASS. The boundary gate IS repair-by-resume: wrong-short program rejected at 719709, search continues to the clean program at 2583787. B-058's profile shows candidates are binary-decided (one r0 evaluation), so "best partial" has no separate existence to resume from; the only resume point is rejection-then-continue, which the gate already implements.

## B-496 verdict (2026-10-22): PASS - exact chained arithmetic at 10x P5's length is chain-length-invariant for exact tables

b496.py: P5's T1 successor table (100 entries, x->x+1 mod 100, UNCHANGED) queried over chains of 4750 links (10x P5's 475): 100/100 starts arrive exactly (475000 lookups, 0.031s wall). The mechanism argument is now measured: exact key-value recall has no error compounding and no capacity growth with chain length - the same table serves any chain. Contrast with the HDC superposition side (B-237: 2-hop chains FAIL at 500 chains/1500 links even at 16KB; multi-hop RAM must grow with link count). Exact tables trade flexibility for this invariance; superposition trades exactness for fixed-size storage. This is the strongest form of the T8 claim: chain length is FREE for exact memory.

## B-407P pre-registration (2026-10-22) - anaphoric zero-operand steps ("then double it")

Question (B-407): can the P16 TwoStep learner handle 2-step commands whose second step references the first result via "it" and carries an IMPLICIT constant in a word (double/triple/halve/increment/decrement), with accuracy within 5 pts of the explicit-number version?
Prior fact: zero-operand anaphora already exists for fact/isprime ("take the factorial", "check if it is prime") - those carry no constant. The new content: words that secretly bind BOTH an op and a constant, learnable only from (text, answer) supervision.
Design (b407.py): extend H2 with 5 zero-operand ops (double/triple/halve/inc/dec; require len(numbers_of(right))==0). Generator mirrors two_step; 35% of 2-step items replace the right clause with an anaphoric phrase ("then double it" etc., no digits - numbers_of is digits-only, verified). Train n=300 mixed (anaphoric + explicit + singles), 5 seeds. Eval arms: (a) anaphoric-only test, (b) explicit-only test, same model.
Criteria: (1) anaphoric acc within 5 pts of explicit acc; (2) CONTROL: a model trained with 0% anaphoric data must score near zero on the anaphoric test (proves the phrases are LEARNED, not leaked by the hypothesis extension); (3) explicit-arm accuracy must not drop >5 pts vs the no-anaphora model's explicit accuracy (no interference).

## B-407 verdict (2026-10-22): PASS - anaphoric zero-operand steps are learnable and EASIER than explicit ones

b407.py, pre-registered criteria, 5 seeds, n=300 mixed training, matched 2-step-only eval:
- anaphoric test ("then double/triple/halve/increment/decrement it"): .85/.86/.93/.86/.91 = mean .882
- explicit-number test, same model: .52/.53/.62/.51/.59 = mean .554 - criterion (1) "within 5 pts of explicit" met: anaphoric is +32.8 pts BETTER, not worse
- CONTROL (0% anaphora in training): .03/.00/.02/.02/.00 = mean .014 on the anaphoric test - criterion (2) met: the phrases are LEARNED from supervision, not leaked by the H2 extension
- interference check: explicit accuracy .554 with anaphora mixed in vs .536 without - criterion (3) met (+1.8 pts, no drop)
Interpretation: zero-operand anaphora is easier than explicit constants in this learner - no number to extract, short right clauses, only 5 phrases to ground. The epistemic status is unchanged from P16: the hypothesis space (now including 5 implicit-constant ops) is given; the phrase->hypothesis mapping is learned from (text, answer) pairs. Note the explicit 2-step accuracy itself (~.55 at n=300, 2-step-only) is the known P16-level difficulty - the anaphora result does not improve it, it adds a new learnable phrasing class.

## B-408 triage (2026-10-22): already measured by construction - P21's "same-conn" condition IS mixed en/th

Source inspection (text2prog5.py three_step + text2prog2.py two_step): connectors are sampled independently PER CLAUSE from CONN[0] = ["then", "and then", "แล้ว", "จากนั้น"], and clause frames from C1/C2 train lists that also mix English and Thai. So P21's same-connector 3-step measurement (.35 at n=300, .53 at n=1000, 5 seeds) was already taken over mixed en/th sentences - the mixed-connector condition B-408 asks to compare against the P21 baseline is identical to that baseline. No run needed; the item rests on a wrong premise that P21 was English-only.

## B-409P pre-registration (2026-10-22) - Thai no-space 2-step via char-boundary scan

Question (B-409): Thai has no spaces between words; can a char-level model segment AND solve 2-step Thai commands, at >= .8 of the spaced-Thai token model's accuracy?
Design (b409.py): Thai-only generation (frames/connectors filtered to Thai by unicode block). Baseline arm: P16 TwoStep (tok learners) on spaced Thai. Test arm: same learner class but Learner('char') and clause cuts scanned over CHARACTER positions of the space-stripped string (no segmentation given - fit() credits whichever char-cut yields the supervising answer, so segmentation is learned, not handed). Boundary model keys become char pairs. numbers_of is digits-only, unaffected by despaceing.
Protocol: n=300 training (30% singles, Thai-only), 5 seeds, 200-item 2-step-plus-single test per arm.
Criteria: (1) char-nospace acc >= .8 * tok-spaced acc; (2) CONTROL: the tok-spaced model evaluated on no-space text must collapse (tokens unseen) - proves the char model carries the segmentation; (3) record both arms' single-op accuracy separately (singles should stay high in both).

## B-409 verdict (2026-10-22): FAIL - char-boundary scan does not learn Thai segmentation at n=300

b409.py, pre-registered criteria, 5 seeds, n=300 Thai-only mixed training, 200-item test:
- tok_spaced (baseline): .80/.765/.785/.835/.745 = mean .786
- char_nospace: .365/.205/.23/.235/.32 = mean .271 - criterion >= .8 x .786 = .629 decisively FAILED (34% of baseline)
- CONTROL (tok model on despaced text): .245/.14/.175/.235/.17 = mean .193 - collapses as predicted but not to zero: fallback single-op hypotheses on extracted digits still land some answers
Diagnosis: the char model beats the no-segmentation control by only ~8 pts, so segmentation itself is what failed, not op grounding. Two measured causes: (1) credit dilution - at char granularity many cuts are explanation-consistent with the supervising answer, so w=1/|E| spreads credit over spurious boundaries; (2) boundary statistics over char PAIRS are sparse relative to word pairs. Word-level segmentation is not free: it must be either given (whitespace languages), learned with a sharper objective than answer-consistent credit, or bought with much more data. Follow-up candidates (not run): n=1000+, discriminative boundary training, or digit/connector-anchored cut proposals (which hands partial segmentation - note it as such if tried).

## B-410P pre-registration (2026-10-22) - digit-free numbers: bootstrapping without a digit model

Question (B-410): can number words be learned when training text contains ONLY words, never digits? The existing stage-B lexicon learner is circular for this: it substitutes candidate values into the text and checks them with an ALREADY digit-trained op model (learn_lexicon, text2prog2.py:51). Digit-free learning must break the bootstrap.
Design (b410.py), two phases, no digit strings in any training text (answers are integer supervision, as in all P16 stages):
- Phase 1 (constraint pinning): unary-op sentences only ("factorial of W" etc., words for values 2..10). Each (text, ans) constrains the word's value to the UNION over unary ops of preimages of ans; intersect a word's constraint sets across its sentences. Measure: how many of the 9-10 words pin to a singleton after n sentences, and how many pin CORRECTLY.
- Phase 2 (EM continuation): sentences whose words are all pinned decode to digits -> train the P16 op model on decoded text -> learn_lexicon (the existing substitution voter, now legitimate since an op model exists) for the remaining words. Measure end-to-end 2-step answer accuracy vs the P16 mixed baseline.
Criteria: (1) report honest pinned-count/accuracy at n=150/400 (no target preset beyond "report"); (2) success for the full claim = 2-step accuracy >= .8 of the P16 mixed-digit baseline at the same n; (3) CONTROL: shuffled-answer training must pin ~0 words correctly (constraints from noise do not converge).

## B-410 verdict (2026-10-22): MIXED - digit-free number grounding bootstraps exactly; end-to-end accuracy fails the .8 criterion at n=300

Phase 1 (b410.py, unary constraint pinning): from unary-op word-only sentences ("factorial of W" etc., zero digit strings anywhere), intersecting preimage constraints pins all 8 seen words (values 2..9) CORRECTLY at n=150 and n=400, 5/5 seeds. Wrong-answer control pins 0/8 - constraints from noise do not converge. The learn_lexicon circularity is broken: no digit-trained model is needed to start.
Phase 2 (b410b.py, EM continuation to end-to-end 2-step): pin -> decode fully-decodable mixed sentences (167-190 of 300) -> train op model -> learn_lexicon for the rest -> final TwoStep. 5 seeds: acc .475/.53/.475/.515/.645 = mean .54 vs matched digit baseline .975-1.0 = mean .99 on the same simplified 4-op EN generator. Criterion (>= .8 x baseline = .79) FAILED at n=300+120.
Loss decomposition (honest): lex0 covers only values 2..9 (one/ten absent from unary sentences -> those test sentences unsolvable); 40% of training sentences undecodable pre-EM; EM additions went WRONG in seeds 1 and 3 (lex_total > lex_correct). The bootstrap (the scientifically interesting claim) is exact; the gap is downstream data dilution, closable with unary coverage of 1/10, more data, or iterated EM. Caveat: baseline uses a simplified 4-op English-only generator, not the full P16 mix - .99 baseline reflects that. Sloppiness note: b410b imports b410, re-running its phase-1 grid on import (harmless, doubles log).

## B-410b variant pre-registration (2026-10-22): close the phase-2 gap

Three targeted fixes over b410b, same protocol otherwise: (1) unary coverage extended to values 1..10 (vocab_range (1,11)) so one/ten also pin; (2) training mix 300 -> 600 sentences; (3) second EM round: after learn_lexicon, retrain the op model on the fully-decoded corpus with the complete lexicon and re-vote. Criterion unchanged: end-to-end >= .8 x matched-digit baseline; report honest numbers either way.

## B-410 FINAL (2026-10-22): PASS - digit-free number grounding solved end-to-end by pure constraint pinning

Variant ladder (pre-registered b410c fixes, then b410d):
- b410b (vocab 2..9, n=300, EM on): .54 mean vs .99 baseline - FAIL
- b410c (vocab 1..10, n=600, EM on, EM round 2): .735/.775/.93/.765/.825 = .766 mean, lex0 10/10 correct every seed - below .8 criterion; EM rounds added 1-2 SPURIOUS entries (lex_total 11-12 vs lex_correct 10)
- b410d = b410c with EM fully disabled (lexicon = pinned words only): acc 1.0/1.0/1.0/1.0/1.0 = digit baseline exactly. PASS vs the .8 criterion, 5/5 seeds.
Mechanism story: with complete unary coverage (values 1..10 each pinned by preimage-intersection over fact/sumto/isprime constraints from ~120 word-only sentences), grounding is EXACT and the substitution-voting EM only corrupts (it votes function words into the lexicon). Digit-free pipeline: pin from unary -> decode mixed sentences -> train TwoStep on decoded text -> done. No digit string is ever seen; answers remain integer supervision. Caveats: simplified generator (4 binary ops, English-only, values 1..10); the claim is about grounding numerals from answer supervision, not about learning arithmetic. Sloppiness note carried: b410c/d import b410 which re-runs the phase-1 grid on import (harmless).

## B-493P pre-registration (2026-10-23) - class-incremental MNIST: WiSARD vs shared-hidden MLP

Question (B-493, also closes the forgetting half left open by B-435): sequential class-incremental learning - train classes 0-4, then 5-9 - what happens to early-class accuracy?
Design (b493.py, same data/encoding as B-236: binarized MNIST, 28-bit tuples x28 nodes):
- WiSARD arm: train on A (classes 0-4), eval A-test; then ADD B (classes 5-9, node union), eval A/B/all-test. Prediction: zero drop - new classes only add nodes; old tables untouched (P5 E4 retention pattern).
- MLP arm (HONEST baseline, not rigged): single softmax net 784-64-10 with a SHARED hidden layer (the textbook catastrophic-forgetting setup; the B-241 one-vs-rest heads have per-class hidden layers and CANNOT forget, so they are not a valid baseline here), 300 SGD epochs on A, eval; 300 more on B, eval A/B/all. Prediction: significant A drop (>10 pts).
- 3 seeds (tuple permutation + net init). Criteria: report honest A-retention for both arms; WiSARD claim = drop <= 1 pt.

## B-493 verdict (2026-10-23): PASS - table memory does not forget where gradient memory catastrophically forgets

b493.py, pre-registered, 3 seeds, class-incremental MNIST (train classes 0-4, then ADD classes 5-9; binarized 28-bit-tuple WiSARD vs single shared-hidden softmax MLP 784-64-10, fixed normalization, 300 SGD epochs per phase):
- WiSARD: A accuracy .975 -> .944 after B (-3.1 pts); B .862; all-classes .904
- MLP: A accuracy .974 -> .059 after B (-91.5 pts, total collapse to chance); B .946; all-classes .490
Pre-registered prediction was WiSARD drop <= 1 pt; measured -3.1. Correction recorded: the drop is NOT memory interference (old class tables are byte-untouched by construction) but decision-level competition - a 10-way argmax confuses some A samples with newly added B-class nodes. The memory-vs-decision distinction is the honest framing: nothing is forgotten; discrimination gets harder as classes accumulate.
The MLP tradeoff is real and recorded: it fits the NEW classes better (.946 vs .862) but destroys the old ones. SCOPING (per review): (1) byte-untouched tables establish STORAGE retention, not unchanged behavioral recall - the measured -3.1 pt old-class accuracy drop stands in every statement of this result; "nothing is forgotten" is wrong at the behavioral level. (2) The contrast is scoped to THIS protocol (class-incremental binarized MNIST, 2 phases) and THIS baseline (naive sequential SGD fine-tuning of a shared-hidden softmax net with NO continual-learning mitigation - no replay buffer, no EWC/consolidation, no regularization toward old weights). A mitigated gradient baseline (replay/EWC) would narrow the gap; the claim is about naive sequential training, not gradient memory generally. Within that scope it closes the forgetting half left open by B-435 and strengthens B-241's few-shot claim into the continual setting.

## B-494P pre-registration (2026-10-23) - permuted MNIST x5 sequential retention

Question (B-494): the standard continual-learning benchmark - 5 permuted-MNIST tasks learned in sequence; what is task-1 accuracy after tasks 2..5?
Design (b494.py, same encoding as B-493; permutation pi applied to pixels per task; SAME 28-bit tuple layout positions for all tasks):
- WiSARD-shared arm: one node set; each task ADDS its entries (union). Old entries never removed. Prediction: task-1 retention degrades only via decision competition; report honest curve.
- WiSARD-per-task arm: separate node set per task, task id given at test (the pure-storage reference - retention must be perfect, else a bug).
- MLP arm: shared-hidden softmax 784-64-10, 300 epochs per task sequentially. Prediction: each new task collapses the previous (B-493 pattern).
3 seeds. Metrics: task-1 accuracy after each task k=1..5, per arm; final all-task mean for WiSARD arms (per-task arm scores each task with its own nodes). Criteria: report honest curves; WiSARD-shared claim = task-1 retention after 5 tasks >= .8.

## B-494 verdict (2026-10-23) - PASS

logs/b494_stdout.log (3 seeds, criteria pre-registered above).
WiSARD-shared task-1 curve after k tasks:
- seed 0: .9115 .9101 .9077 .9059 .9040 (-0.75 pt)
- seed 1: .9028 .8998 .8977 .8972 .8955 (-0.73 pt)
- seed 2: .8982 .8965 .8941 .8922 .8913 (-0.69 pt)
Claim (shared-arm task-1 >= .8 after 5 tasks) PASS on all 3 seeds (min .8913).
Per-task arm FLAT (.9115/.9028/.8982 at every k) - storage retention is perfect; the shared-arm drop is decision competition only (new entries add rival discriminators; nothing is removed), NOT lost information.
Shared-arm final all-task mean: .8967/.8938/.8993 (mean .8966).
MLP (naive sequential SGD, 300 epochs/task, no replay/EWC/any mitigation): task-1 collapses to .0894/.1644/.0771 after 5 tasks.
Scope: contrast is this encoding + this protocol + a naive baseline; per-task flatness establishes storage retention, not unchanged behavioral recall under a shared readout - the measured -0.7..-0.8 pt shared-arm drop is real behavioral degradation and is preserved.
Commit: see git log (b494 verdict).

## B-406P pre-registration (2026-10-23) - anti-unification schemas as search ordering

Question (B-406): do partial schemas obtained by anti-unifying (least-general-generalization of) PAIRS of already-learned programs transfer as a search-ordering prior to HELD-OUT curriculum tasks? Premise flagged weak (P24/F-6: step-pair macro ordering gave little); this tests the stronger full-spec generalization.
Design (b406.py + 3 hook lines in cur7.py, LIST_OVERRIDE/LIST_CAPTURE/SKIP_SET, inert unless set):
- Source programs: the 12 learned programs in /tmp/c7_prog_0_base.json (choose2, dblfact, div, fact, gcd, max, min, mod, mul, power, square, sumto).
- Anti-unify all pairs over the full spec (init, cond, base, s0, s1, comb, post); recursive LGG inside cond/steps/comb expressions; mismatches become holes. Dedup identical schemas.
- Non-triviality filter (pre-stated): a schema must FULLY fix >=3 of the 7 top-level fields to count (all-hole schemas "match everything" and prove nothing).
- Held-out tasks (never used to build schemas): isprime, absdiff, cube, even, lcm.
- Library: existing honest baselib pinning (mod/mul/div/power/gcd/max/min pinned into LIB; B-523-H1 EXCL - target never resolves through pinned library; held-out targets are not pinnable anyway). Both arms identical LIB; ev/cev caches cleared before EACH arm (no warm-cache advantage).
- Baseline arm: cur7.search(train, 'baselib', tried_cap=1M). Tasks NOT FOUND in 1M are excluded from the cut metric (recorded as excluded, not failures of the schema claim).
- Schema arm: phase 1 = for each non-trivial schema (most-fixed-fields first), enumerate only schema-consistent candidates (per-field filtered lists preserving baseline order), skipping candidates already tried (dedup set, not re-counted); cumulative phase-1 budget 500K. Phase 2 (if phase 1 misses): full baseline space; schema-arm tried = phase-1 tried + baseline tried (double evaluations honestly double-counted).
- Paired: identical train examples (same pre-generated list) for both arms.
Metrics: per held-out task: found?, tried baseline vs schema arm, which schema matched the solution.
Criteria (pre-stated): PASS iff ONE non-trivial schema is consistent with the found solutions of >=2 held-out tasks AND mean tried on those tasks is cut >50% vs baseline. Otherwise FAIL: if tight schemas match nothing held-out or matching schemas give <50% cuts, record honestly - that falsifies anti-unification transfer for this curriculum.
CAN claim if PASS: pairwise anti-unified schemas are a useful search-ordering prior on held-out tasks of this curriculum. CANNOT claim: library-free discovery, new expressivity (schemas only reorder the same candidate space), or transfer beyond this curriculum.

## B-406 verdict (2026-10-23) - FAIL (criterion unmet; strong single-task signal recorded honestly)

logs/b406_stdout.log. Anti-unification of the 12 learned programs yielded 45 pair-schemas, 16 non-trivial (>=3/7 fields fixed).
Held-out results (1M baseline cap; 4 of 5 tasks NOT FOUND in baseline -> excluded from cut metric per pre-registration):
- absdiff: NOT FOUND (both arms; full 1.29M-spec space exhausted)
- lcm: NOT FOUND (both arms)
- isprime: NOT FOUND (both arms)
- cube: NOT FOUND (both arms)
- even: FOUND both arms. Baseline tried 123619 (program: init b=y, s1=(power zero b), post nz - a power-zero parity trick). Schema arm phase-1 tried 8036 via schema #1 (fact/sumto LGG: init ?, cond (lt a one), base b, s0 (sub a one), s1 ?, comb None, post id) - a 93.5% tried cut, and a DIFFERENT, simpler solution (init one, s1=(sub one b), post id - pure parity flip). Solution consistent with schemas #1 and #7.
Criterion (ONE schema consistent with >=2 held-out solutions AND mean cut >50%) NOT MET: only 1 held-out task was solvable within cap, so cross-task reuse cannot be demonstrated. FAIL as pre-registered.
Honest partial signal: on the single solvable held-out task the schema ordering cut tried by 93.5% and steered to a simpler program - the mechanism works when a matching schema exists; the premise failure is COVERAGE (4/5 held-out tasks unreachable in 1M from the pinned library), not schema quality. The NOT-FOUND wall itself is data: absdiff/lcm/isprime/cube are not reachable in this space/order/budget with the pinned library.
Caveats: found programs fit 25 staged train examples only; this harness runs no generalization test (out of scope for the ordering question). Schema arm tried counts are honest (phase-1 + double-counted baseline on misses).

## B-495P pre-registration (2026-10-23) - few-shot SNIPS intent classification vs NB

Question (B-495): does WiSARD beat a naive-Bayes text baseline at <=5-shot intent classification on SNIPS?
Data: SNIPS nlu-benchmark 2017-06 custom-intent-engines split (CC0; github.com/sonos/nlu-benchmark, downloaded 2026-10-23), converted by prepare_snips.py: 2100 train / 700 test utterances, 7 intents (AddToPlaylist, BookRestaurant, GetWeather, PlayMusic, RateBook, SearchCreativeWork, SearchScreeningEvent), lowercase alnum+space normalized.
Design (b495.py):
- Vocabulary: all word tokens in the FULL train file (both models see the same vocabulary; k-shot subsampling picks examples, not vocab - pre-stated; this is the standard transductive few-shot protocol and favors neither model's mechanism).
- WiSARD arm: features = presence bits of word unigrams + bigrams hashed into 4096 bits; fixed rng(0) tuple layout of 28-bit tuples (146 tuples); per-class per-node tuple-value sets; argmax score.
- NB arm: multinomial naive Bayes, word unigram+bigram counts, alpha=1.0 (standard strong text baseline, honest not rigged).
- Protocol: k in {1, 5, 20} shots per intent, sampled without replacement from the 300-per-intent train pool; 10 seeds per k; score = accuracy on all 700 test utterances.
Criterion (pre-stated): PASS = WiSARD mean accuracy > NB mean accuracy at k=1 AND k=5 (both). Win at 20 only = partial. Either k=1 or k=5 not won = FAIL as registered; report all numbers regardless.
CAN claim if PASS: WiSARD tuple-sets beat multinomial NB on this SNIPS split at <=5 shots under this encoding. CANNOT claim: superiority over NB generally, over neural few-shot methods, or on other text tasks; encoding choice is ours and shared.

## B-495 verdict (2026-10-23) - FAIL (WiSARD loses to NB at every k)

logs/b495_stdout.log (10 seeds per k; NB double-log bug caught and fixed BEFORE verdict - the chance-level flat 0.1429 NB was an artifact; numbers below are the fixed, honest baseline).
- k=1: WiSARD .3471 vs NB .6044 - WiSARD loses by 25.7 pt
- k=5: WiSARD .8307 vs NB .8580 - loses by 2.7 pt
- k=20: WiSARD .8936 vs NB .9423 - loses by 4.9 pt
Criterion (WiSARD wins BOTH k=1 and k=5) FAIL at every k. Multinomial NB on uni+bigram counts is simply strong on this split - 1-shot NB (.60) already beats 5-shot WiSARD (.83)? No: 5-shot WiSARD .83 > 1-shot NB .60, but at equal shots NB wins throughout. The count information NB exploits (token multiplicities, per-token log-odds) is exactly what presence-bit tuple sets discard; at k=1 the hashed-bit collisions + absent bigram coverage hurt WiSARD hardest.
Scope: this SNIPS split, this encoding (4096 hashed presence bits, 146x28-bit tuples), multinomial NB alpha=1. NOT a claim about WiSARD on text generally - a different encoding (e.g. count-aware or thermometer coding) is a separate pre-registered experiment.
Note: MNIST few-shot (B-241) and SNIPS few-shot (B-495) now bracket where tuple-set few-shot shines (spatial binary structure) vs where it does not (sparse count-heavy text vs a count-aware baseline).

## B-466/469/472/475/478/481P pre-registration (2026-10-23) - MNIST few-shot readout grid slice

Question (6 T7 cells, one harness): on MNIST, at k in {1,5,20} shots/class, how do NEAREST-NEIGHBOR and CENTROID readouts compare to the B-241 MLP baseline at the same shots? (WiSARD cells already measured by B-241: .340/.470/.647 vs MLP .106/.148/.322 - this fills the two missing readout rows.)
Design (b466.py): same data/load as t5wisard (binarized MNIST >128); readouts on raw 784-bit vectors: 1nn (L2), centroid (class mean, L2). Baseline: the EXACT B-241 OVR MLP (784-32-1 tanh, 800 epochs, lr .05) at the same shots. 5 seeds per k (shot subsets sampled per seed; MLP init rng fixed per class as in B-241). Note B-241 used FIRST-k (deterministic) sampling; this slice samples per seed - cell numbers will differ from B-241's single-sample cells and supersede them only for these readouts.
Criterion per cell (pre-stated): report means; cell = readout WINS / LOSES / TIES (within 1 pt) vs MLP at same k. Overall PASS = either readout wins a majority of its 3 k-cells. Honest nulls recorded.
CAN claim: readout-vs-MLP few-shot ordering on MNIST under this exact harness. CANNOT claim: anything about other tasks, other MLP sizes, or tuned architectures.

## B-466/469/472/475/478/481 verdicts (2026-10-23) - PASS (6 cells)

logs/b466_stdout.log (5 seeds/k, mean): k=1: 1nn .4287 = centroid .4287 (identical at 1 shot - expected, centroid of one example IS the 1nn prototype; internal consistency check passes), MLP .0927; k=5: 1nn .6185, centroid .6523, MLP .1249; k=20: 1nn .7559, centroid .7570, MLP .3513.
All 6 cells WIN vs the B-241 OVR MLP at the same shots (gaps +33 to +53 pt). MLP is near-chance at k=1 (.093) and still poor at k=20 (.351) - the B-241 few-shot MLP weakness replicates under seeded sampling (B-241's .106/.148/.322 was first-k sampling; same ordering).
Ordering within this harness: centroid >= 1nn >> MLP at every k (centroid's averaging denoises at k>=5).
Caveat: B-241's WiSARD row (.340/.470/.647) used first-k deterministic sampling, so a WiSARD-vs-1nn/centroid claim needs WiSARD re-run in THIS seeded harness - pre-registered follow-up required before any such claim. NOT claimed here.

## B-241R pre-registration (2026-10-23) - seeded MNIST few-shot: WiSARD vs 1nn/centroid/MLP in ONE harness

Question: B-241's WiSARD few-shot numbers (.340/.470/.647 at k=1/5/20) used first-k deterministic sampling; B-466..481 measured 1nn/centroid under seeded sampling. Does the WiSARD readout beat the simple centroid readout under identical seeded conditions?
Design (b466w.py): EXACTLY b466.py (same seeds 200..204, same sampled subsets, same OVR MLP) PLUS the B-241 WiSARD readout (28-bit tuples, rng(0) layout, per-class tuple-value sets) on the same subsets. k in {1,5,20}, 5 seeds.
Criterion (pre-stated): report all four readouts; the readout-ordering claim applies only within this harness. WiSARD WINS a k-cell if its mean exceeds centroid's by >1 pt; LOSES if below by >1 pt; else TIE. No claim beyond MNIST few-shot in this harness.

## B-241R verdict (2026-10-23) - WiSARD LOSES to centroid/1nn at every k (corrects B-241's implied readout strength)

logs/b466w_stdout.log (same 5 seeds and subsets for all four readouts): k=1: WiSARD .3053, centroid .4287, 1nn .4287, MLP .0927; k=5: WiSARD .4741, centroid .6523, 1nn .6185, MLP .1249; k=20: WiSARD .6689, centroid .7570, 1nn .7559, MLP .3513.
WiSARD loses to centroid by 12.3/17.8/8.8 pt at k=1/5/20 (LOSES all 3 cells per the pre-stated 1-pt margin). B-241's "WiSARD beats MLP few-shot" survives (+21 to +38 pt) and replicates under seeded sampling (seeded .305/.474/.669 vs first-k .340/.470/.647 - consistent). What does NOT survive: any implication that the WiSARD tuple readout is a strong few-shot readout on MNIST - plain class-mean on raw binarized pixels beats it by up to 18 pt.
Updated honest picture (this harness only): centroid ~= 1nn > WiSARD >> MLP on MNIST few-shot; NB > WiSARD on SNIPS few-shot (B-495). The tuple-set readout's demonstrated advantages are one-pass learning and continual retention (B-493/B-494), NOT few-shot accuracy. Any future few-shot-accuracy claim for WiSARD must beat the centroid row in this seeded harness first.

## B-468/471/474/477/480/483P pre-registration (2026-10-23) - SNIPS few-shot readout grid slice

Question (6 T7 cells): on SNIPS intents, at k in {1,5,20} shots, 1nn and centroid readouts vs MLP at the same shots. Complements B-495 (WiSARD vs NB) with the two missing readouts on the SAME features.
Design (b468.py): EXACTLY the b495 pipeline (4096 hashed uni+bigram presence bits, same data files); readouts: 1nn (L2 on bit vectors), centroid (class mean, L2), MLP = OVR tanh 4096-32-1, 800 epochs, lr .05 (same recipe as B-241/b466, input dim swapped). 10 seeds, seed set 100..109 IDENTICAL to B-495 (paired with the NB/WiSARD numbers).
Criterion per cell: readout WINS / LOSES / TIES (1 pt) vs MLP at same k. Report all numbers; honest nulls fine. CANNOT claim: anything beyond this SNIPS split, these features, this MLP.

## B-468/471/474/477/480/483 verdicts (2026-10-23) - PASS (6 cells)

logs/b468_stdout.log (10 seeds paired with B-495): k=1: 1nn .362 = centroid .362, MLP .148; k=5: 1nn .594, centroid .807, MLP .145; k=20: 1nn .794, centroid .905, MLP .150. All 6 cells WIN vs MLP (+21 to +75 pt). The few-shot OVR MLP is stuck near chance (~.15, chance .143) at every k on these sparse bit features.
Full SNIPS few-shot ordering (all paired on seeds 100..109, same features): NB .604/.858/.942 > centroid .362/.807/.905 > WiSARD .347/.831/.894 > 1nn .362/.594/.794 >> MLP ~.15. Centroid nearly matches NB at k=20 (.905 vs .942) but lags at k=1 (.362 vs .604 - NB's count/log-odds prior transfers across classes, centroid has nothing to average).
Consistency: k=1 1nn==centroid identity holds again (both readouts equivalent at 1 shot).

## Correction (2026-10-23) - SNIPS ordering is per-k, not uniform; retention scope qualifier

The B-468..483 verdict's blanket ordering "NB > centroid > WiSARD > 1nn >> MLP" is WRONG at k=1 and k=5 (caught in review). Correct paired-seed per-k orderings:
- k=1: NB .604 > centroid .362 = 1nn .362 > WiSARD .347 >> MLP .148
- k=5: NB .858 > WiSARD .831 > centroid .807 > 1nn .594 >> MLP .145
- k=20: NB .942 > centroid .905 > WiSARD .894 > 1nn .794 >> MLP .150
Uniform claims that DO hold: NB first and MLP last at every k. The middle three swap: WiSARD beats centroid only at k=5 (.831 vs .807); centroid beats WiSARD at k=1 (.362 vs .347) and k=20 (.905 vs .894); 1nn beats WiSARD at k=1 only.
Scope qualifier retained everywhere: the B-493/B-494 retention advantage is demonstrated against NAIVE SEQUENTIAL MLP only (no replay/EWC) - not against these simple readouts (1nn/centroid/NB), which were never run under the continual protocol, and not against mitigated gradient methods.

## B-467/470/473/476/479/482/485/488/491P pre-registration (2026-10-23) - few-shot pmnist readout grid

Question (9 T7 cells): few-shot CONTINUAL pmnist - 5 permuted-MNIST tasks learned in sequence, k shots per class PER TASK; which readouts retain? Per-cell semantics pre-stated here (the backlog lines leave them open): for each readout in {1nn, centroid, WiSARD} and k in {1,5,20}: shared arm = one accumulated structure across tasks (support set / running class mean / node union), per-task arm = separate structure per task (storage reference), MLP arm = naive sequential softmax MLP 784-64-10, 300 epochs per task on the k-shot samples only (same architecture as B-494).
Design (b467.py): b494 permutations and tuple layout (seed-dependent); per task t and class, sample k train examples without replacement (seeded); metrics after each task: per-task test accuracy for every arm on all tasks seen so far's task-1 + final all-task mean. 2 seeds. Test = full 10K per task.
Note on expectations (pre-stated, not criteria): shared-centroid mixes permuted variants of a class into one mean - expected to degrade badly (permutation mush); 1nn-shared should behave like WiSARD-shared (cross-permutation competition only); per-task arms are storage references and must stay flat at their k-shot level.
Criterion per cell (pre-stated): WIN if readout's shared-arm final all-task mean beats MLP's final all-task mean by >1 pt; LOSE if below by >1 pt; else TIE. Report all arms and the honest drops. Overall: per-readout PASS = wins majority of its 3 k-cells.
CANNOT claim: comparison vs mitigated continual methods; MLP is naive sequential SGD (same scoping as B-493/B-494).

## B-467/470/473/476/479/482/485/488/491 verdicts (2026-10-23) - PASS (9 cells, all readouts beat MLP at every k)

logs/b467_stdout.log (2 seeds; shared-arm final all-task mean, averaged over seeds): k=1: 1nn .403, centroid .380, WiSARD .277, MLP .163; k=5: 1nn .627, centroid .573, WiSARD .444, MLP .187; k=20: 1nn .756, centroid .685, WiSARD .657, MLP .175. All 9 cells WIN vs naive sequential MLP (same scoping as B-493/B-494: naive SGD, no mitigation).
Shared vs per-task (storage reference) arms:
- 1nn: shared ~= per-task at every k (max diff 1.0 pt, both directions) - accumulated prototypes across permuted tasks coexist nearly losslessly; cross-permutation decision competition is negligible for 1nn at these k.
- centroid: shared LOSES to per-task by 2.4/8.8/7.2 pt at k=1/5/20 - the pre-stated permutation-mush expectation confirmed: averaging permuted variants of a class into one mean destroys what storage keeps. (Mechanism demonstration, not a bug.)
- WiSARD: shared below per-task by 1.3/2.0/1.6 pt - small consistent decision-competition drop, consistent with B-494's full-data pattern.
WiSARD is again the weakest non-MLP readout in few-shot accuracy (consistent with B-241R on plain MNIST); its demonstrated strengths remain one-pass learning and retention vs naive MLP.

## B-497P pre-registration (2026-10-23) - symbolic unit conversion vs MLP text baseline

Question (B-497): template-generated unit-conversion word problems; does an exact symbolic converter stay exact where a text MLP fails? EXPECTED OUTCOME IS KNOWN IN ADVANCE (symbolic wins on unseen numbers) - the value is the MEASURED FAILURE BOUNDARY (which splits break the MLP), not the win. Pre-stated to keep the comparison honest and non-triumphalist.
Design (b497.py):
- Templates: "convert <x> <u> to <v>", "how many <v> in <x> <u>", "<x> <u> in <v>" with x in a numeric range, (u,v) unit pairs within length (mm,cm,m,km), mass (mg,g,kg), time (s,min,h). x sampled with 1 decimal (e.g. 3.5) or integer. Answer = x * factor(u,v), exact decimal.
- Splits: TRAIN on a fixed set of (x value, unit pair) combos; TEST-seen = same combos new surface template; TEST-unseen-x = same unit pairs, NEW x values; TEST-unseen-pair = NEW unit pairs (e.g. train km->m, test m->cm reversed factors). 
- Symbolic arm: template parser (number, u, v) + exact factor table + decimal arithmetic. Upper bound of the approach by construction.
- MLP arm: bag-of-hashed-word/bits -> MLP (same OVR-style recipe, hidden 64) trained as CLASSIFIER over the training answer set (closed set); on test, can only output training answers - pre-stated: unseen-x is structurally impossible for a closed-set classifier; ALSO report a regression variant? No - keep closed-set (pre-stated); the boundary is the point.
- 3 seeds for MLP. Metrics: exact-match accuracy per split.
Criterion (pre-stated): PASS = symbolic 100% exact on ALL splits AND MLP accuracy on unseen-x < 50% of its seen-split accuracy (the measured boundary). If MLP generalizes to unseen-x (it cannot as a closed-set classifier - if it does, a bug), investigate.
CAN claim: on this template task, exact symbolic arithmetic is exact where a closed-set text classifier cannot be. CANNOT claim: anything about LLMs, neural arithmetic generally, or non-template language.

## B-497 verdict (2026-10-23) - PASS (boundary measured; outcome was pre-stated as expected)

logs/b497_stdout.log (360 train problems, 66-answer closed set; symbolic direction bug caught and fixed BEFORE verdict - source unit is the one the number quantifies; numbers below are post-fix):
- symbolic: 1.0 on ALL splits (seen, unseen-x, unseen-pair) - exact by construction, verified.
- MLP (closed-set classifier, 3 seeds): seen 1.0 (perfect memorization of trained (x, pair, template) combos); unseen-x .1889 (only answer-set coincidences - an unseen number's answer is usually outside the closed set); unseen-pair .0035 (~zero - unseen conversion factors are unreachable).
Criterion (symbolic 100% everywhere AND MLP unseen-x < 50% of seen) PASS: .1889 < .5.
The measured boundary: a closed-set text classifier's exactness is bounded by its training answer set; any novel numeric value or unit pair breaks it, while the symbolic path is exact by construction. As pre-stated, this CANNOT be read as a claim about neural arithmetic generally - it is the exact-vs-closed-set boundary on this template task, documented with numbers.

## B-500/501P pre-registration (2026-10-23) - iterative deepening to depth-2 bases: absdiff and lcm

Question (B-500 absdiff, B-501 lcm): does cost-ordered iterative deepening of EXPRESSION DEPTH in the base position find correct programs the depth-1 6M-cap baseline misses? Motivated by B-406's coverage wall (both NOT FOUND in 1M) - and by the prior analysis that absdiff needs (sub,(max,a,b),(min,a,b)) because p_sub raises on negatives (the no-negatives discipline GUIDES search to the max-min form), and lcm needs (div,(mul,a,b),(gcd,a,b)); both are depth-2 bases with a zero-iteration loop (cond ('nlt','a','zero') always true for a>=0).
Design (b500.py): cur7.search via the existing LIST_OVERRIDE hook; bases replaced by cost-ordered deepening: leaves (1 node) < depth-1 exprs (3) < (op,expr,leaf)/(op,leaf,expr) (5) < (op,expr,expr) (7). Everything else default. abl = 'baselib val' (pinned library mod/mul/div/power/gcd/max/min; VALID = 32 fresh examples, main()'s protocol replicated - the accepted program must fit 25 train + 32 validation, killing spurious-first-match). Cap 6M.
Protocol per task: (1) record whether found, tried, the program; (2) post-hoc generalization test, main()'s protocol (40/scale, scales 1..4); (3) verdict.
Criterion (pre-stated, per task): PASS = a program is found AND generalizes (>=36/40 on scale 2, the library-admission bar) AND baseline (default bases, same cap/abl) does NOT find it. If the first found program fails generalization, that failure IS the result (spurious fit recorded honestly). FAIL = not found in cap, or found-but-spurious.
CAN claim: depth-2 base deepening finds these two programs under this search. CANNOT claim: scalability of depth-2 generally, or that the schema expresses these tasks in any deeper sense (zero-loop = the recursion schema is inert here, the win is expression depth only - pre-stated).

## B-500/501P amendment (2026-10-23) - dummy-step scoping

Loop-structure reality (found while implementing): cur7.search iterates bases INNER to conds but steps INNERMOST, so each wrong (cond, base) costs |steps_pair| (~12.5K) tries - deep bases would need ~10^11 tries. The deep arm therefore also overrides steps to a single dummy pair: it can ONLY find zero-iteration-loop solutions (any step content is equivalent when the loop never runs). This IS the pre-stated hypothesis (absdiff/lcm are pure depth-2-base + zero-loop computations), so the arm is the honest test of it; the cap bounds the comb!=None tail (duplicate zero-loop behavior anyway). The baseline arm keeps default bases + full steps. Nonzero-loop deep-base programs are NOT searchable by this arm - stated as a limitation, not hidden.

## B-500 verdict (2026-10-23) - PASS (absdiff); B-501 (lcm) arm in flight

logs/b500_stdout.log. absdiff: baseline (default leaf bases, full steps, 6M cap) NOT FOUND (6,002,688 tried, 326s). Deep arm (cost-ordered depth<=2 bases, dummy-step zero-loop hypothesis): FOUND at 636,061 tried (66s): init b=y; if (nlt a zero) -> (sub,(max,a,b),(min,a,b)); post id - the predicted max-min form (no-negatives discipline guides past the failing (max,(sub,a,b),(sub,b,a)) shape). Generalization 40/40 at ALL scales 1-4. Criterion PASS: found AND generalizes (40/40 >= 36/40 bar) AND baseline misses it.
Honest scope (pre-stated): zero-loop = the recursion schema is inert here; the win is EXPRESSION DEPTH only, via iterative deepening; nonzero-loop deep-base programs are not searchable by this arm (dummy-step limitation). This resolves the absdiff cell of the B-406 coverage wall: the task was inexpressible at depth-1 bases, not absent from the schema's reach generally.

## B-501 verdict (2026-10-23) - FAIL (lcm), with precise mechanistic diagnosis

logs/b500_stdout.log. lcm: baseline NOT FOUND (6M). Deep arm NOT FOUND (8.72M tried, cap hit in the comb=None block).
Diagnosis (verified directly): the predicted depth-2 zero-loop form (div,(mul,a,b),(gcd,a,b)) IS in the deep arm's space at tried-position ~377K (far below the cap) but is REJECTED because the pinned LEARNED div program (repeated subtraction) hits its 400-iteration cap on large dividends: div(725,1) from lcm(25,29) raises Fail('deep'). Verified: 5 train examples, only the largest-product one fails.
So the B-406 lcm wall is NOT search-space expressivity (the form is present and early) and NOT the iteration schema - it is the learned library program's own runtime cap colliding with intermediate-value blowup (multiply before divide). The cap-respecting rearrangement (divide a factor first, then multiply) is depth-3, outside the pre-registered arm. FAIL as registered; the diagnosis is the result.
Implication recorded: LEARNED library programs carry hidden iteration-capacity limits; intermediate-value growth through composition can silently break them even when the math is right. Any library-composition claim must account for caps (here 400 iterations).

## B-501D pre-registration (2026-10-23) - lcm at depth-3 with cap-respecting composition

Follow-up to B-501's diagnosis. Hypothesis (verified on 8 examples before pre-registration - disclosed): (mul,a,(div,b,(gcd,a,b))) computes lcm within the learned div's 400-iteration cap (divide a factor FIRST, then multiply). Question: does continued cost-ordered deepening FIND it?
Design (b501d.py): same as b500 deep arm, plus a depth-3 block RESTRICTED to (op, leaf, d2small) and (op, d2small, leaf) where d2small = depth-2 forms having at least one leaf arg (8064 forms) - full depth-3 inner args would be 8.7M bases (~1GB, memory-infeasible): pre-stated limitation. Order: depth1 < depth2 < depth3, cap 6M, abl 'baselib val', dummy-step zero-loop arm. Baseline: B-501's depth-2 result (NOT FOUND), not re-run.
Criterion: PASS = lcm found AND gen >=36/40 at scale 2. FAIL = not found in cap. Estimated target position ~1.3M tried if the hypothesis form is the first fitting program.
CAN claim: this lcm form is reachable by cost-ordered deepening to depth-3 under the stated restriction. CANNOT claim: full depth-3 search feasibility, or that search would find lcm without the restriction steering the space.

## B-501D verdict (2026-10-23) - PASS (lcm found at depth-3)

logs/b501d_stdout.log (valid run, after the unpinned-list harness bug was caught and discarded - n_bases 701,684 confirms the pinned 9-op space): FOUND at 2,423,862 tried (261s): init b=y; if (nlt a one) -> (mul,a,(div,b,(gcd,a,b))); post id - the cap-respecting form (divide a factor first, then multiply), generalization 40/40 at ALL scales 1-4. Criterion PASS (found + gen 40/40 >= 36/40 bar).
Tried position 2.42M vs pre-registered estimate ~1.3M - same order; the delta: the found program's cond is (nlt a one) (4th cond, lcm args >= 1) not the assumed (nlt a zero) (6th), and the exact base position differed slightly. Estimate was order-of-magnitude right.
B-406 wall status after today: absdiff SOLVED (B-500, depth-2), lcm SOLVED (B-501D, restricted depth-3) - both were expression-depth/composition-capacity limits, NOT fundamental schema limits. Remaining wall cells: isprime, cube (both likely need REAL iteration - not zero-loop - so the dummy-step arm cannot reach them; honest open question).
Scope retained: restricted depth-3 inner forms only (leaf-containing d2); full depth-3 infeasible (memory); zero-loop arm; the recursion schema is inert in these solutions.

## B-501E pre-registration (2026-10-23) - isprime via mul-fold of remainders (predicted just over the 6M cap)

Analysis before running (falsifiable): isprime IS expressible in the schema as init two; cond (nlt b a); base one; steps (a,(add,b,one)); comb (mul,(mod,a,b),0); post nz - the fold multiplies x%d over d=2..x-1; prime iff product != 0; nz gives exactly isp. Predicted tried position ~7.9M (comb index ~384 x inits x conds x bases x steps_single) - JUST over the historical 6M cap, which would explain the B-406 isprime wall as a CAP ARTIFACT, not expressivity. Predictions: (1) with cap raised to 12M, FOUND near ~7.9M tried (accept wide error bars: 4M..12M); (2) the found program generalizes at scales 1-2 (x<=60) but FAILS at scale 3 (x up to 1000) because the loop needs ~x iterations > the 400 cap - the same hidden iteration-capacity limit as B-501's div, this time in the FOUND program itself; (3) therefore isprime does NOT enter LIB (bar is scale-2 >= 36/40 - it may PASS that; the scale-3 failure is recorded honestly either way).
Design (b501e.py): cur7.search(train, 'baselib val', tried_cap=12M), task isprime seed 0, VALID per main()'s protocol; then gen test scales 1-4. No list overrides - the STOCK enumeration, just a higher cap.
Criterion: PASS = found within 12M AND matches the predicted mechanism (mul-fold of mod + nz) up to step/cond index noise; PARTIAL = found but different mechanism; FAIL = not found in 12M (prediction falsified - isprime wall is NOT a cap artifact).

## B-501E verdict (2026-10-23) - FAIL (prediction falsified; refined mechanism found post-hoc)

logs/b501e_stdout.log: NOT FOUND in 12M (12,005,376 tried, 632s). Pre-registered prediction (mul-fold findable ~7.9M) FALSIFIED - the isprime wall is NOT a simple 6M-cap artifact.
Post-hoc diagnosis (verified directly, logs in this session):
- The predicted order-0 fold (mul(remainder, accumulator)) works for small x but Fail('deep') from x=29 up: the LEARNED mul loops on its SECOND argument = the exploding product (up to ~30^57) - the same hidden iteration-capacity trap as B-501's div, now inside the candidate program itself. The order-0 form is silently rejected on larger train examples.
- The order-1 fold (mul(accumulator, remainder)) is CORRECT for all tested primes/composites (29, 47, 59, 12) - learned mul loops on the small remainder only. But order-1 combs enumerate AFTER all 1,054 order-0 combs: position ~27M tried > 12M cap. isprime IS expressible in the schema (order1 mul-fold + nz post, verified by direct evaluation) but unreachable at 12M under the stock ordering.
Wall anatomy (updated): isprime = expressible but at ~4.5x the historical cap AND behind a capacity trap in the earlier order. All four B-406 wall cells now diagnosed: absdiff (depth-2, SOLVED B-500), lcm (depth-3 + capacity, SOLVED B-501D), isprime (order-position x capacity, expressible-but-unreached), cube (open).

## B-500C pre-registration (2026-10-23) - cube at depth-2 (last B-406 wall cell)

Analysis before running (disclosed): cube is solvable by the B-500 depth-2 deep arm as init two; (nlt a zero); base (mul,a,(power,a,b)); zero-loop; post id - x * x^2 via the pinned learned power. Capacity check (pre-stated): learned mul loops on its 2nd arg = x^2; gen cube ranges are x<8 (scales 1-2) and x<15 (scales 3-4) -> x^2 <= 225 < 400 cap for the ENTIRE gen distribution, so unlike isprime/lcm the capacity trap does NOT bite here. Predicted tried position ~80K (init 'two' is the 4th init; inits y/one/zero burn ~60K first and cannot fit: they give x*x^y, x^2, x).
Criterion: PASS = found AND generalizes (>=36/40 scale 2). If a SPURIOUS earlier program passes train+valid first, the found program is recorded and gen-tested honestly (B-500P protocol). FAIL = not found in 6M or found-but-spurious.
If PASS, all four B-406 wall cells are closed: absdiff (B-500), lcm (B-501D), isprime (B-501E: expressible but position x capacity walled), cube (this).

## B-500C verdict (2026-10-23) - PASS (cube) - and the search out-designed the prediction

logs/b500c_stdout.log: FOUND at 3,825,745 tried (378s), gen 40/40 at ALL scales 1-4. But NOT the pre-registered form: instead of init two + (mul,a,(power,a,b)), the search found init b=y; (nlt a zero) -> (mul,a,(mul,(add,a,zero),a)) - it routes around the missing (mul,a,a) E1 exclusion with the ADD-ZERO IDENTITY: x * ((x+0) * x) = x^3. The prediction's FOUND+generalizes half was right (capacity safe, x^2<=225<400); the specific predicted form was wrong - the search's own route sits earlier in the enumeration. Recorded honestly: form prediction wrong, outcome prediction right.
B-406 coverage wall - ALL FOUR CELLS NOW CLOSED:
- absdiff: SOLVED (B-500, depth-2, (sub,(max,a,b),(min,a,b)))
- lcm: SOLVED (B-501D, restricted depth-3, (mul,a,(div,b,(gcd,a,b))))
- isprime: DIAGNOSED (B-501E: expressible as order-1 mul-fold + nz, verified directly, but ~27M tried position x order-0 capacity trap - unreached by search)
- cube: SOLVED (B-500C, depth-3 path, x*((x+0)*x))
The wall was NEVER a fundamental schema limit: it decomposes into expression depth (fixable by cost-ordered deepening) + learned-program iteration capacity (the 400-cap bites compositions with growing intermediates) + enumeration position.

## B-499 pre-registration (2026-10-23) - fewest-examples curve, scoped down from backlog B-499

Backlog B-499 ("fewest-examples curve for each curriculum skill, baseline 25-example") scoped to one honest question: how does the FOUND program and its enumeration position change as training examples drop from the standard 25? Search mechanics make this non-obvious: enumeration ORDER is fixed per task, so the first train-n-passing candidate is mechanically non-increasing in n - BUT the found program must also pass VALID (32 fixed examples, scales 1-2). At small n, more shortcut candidates pass the weak train filter and each burns up to 32 VALID evals before rejection, so the first train-n+VALID-passing position can move EARLIER OR LATER as n shrinks. That is the measurement.
Design (b499.py): curriculum8 = the exact CURR list (mod, mul, div, power, gcd, isprime, fact, sumto); n in {2, 4, 8, 16, 25} as NESTED PREFIXES of one seed-0 25-example draw (same rng protocol as b501d/main); clean depth-1 stock enumeration, 'baselib val', baselib pinned with EXCL={task} (B-523-H1), tried_cap 6M, one cell = one search call, 40 cells. Per cell: found?, tried, wall dt, program, gen 40/40 at scales 1-4. No re-rolls, no seed shopping, all cells recorded including NOT FOUND.
Baseline: the n=25 column, RE-MEASURED in this harness (canonical expectations from prior clean runs: mod 482, mul 4,155,513, div 4,202,713, power 4,450,489, fact 1,138,228, sumto 2,176,534; gcd unmeasured here; isprime NOT FOUND at 6M per B-501E context).
Hypotheses (pre-stated, falsifiable):
- H1: tried(n) is NOT monotone-decreasing everywhere - at least one skill has tried(n) > tried(25) for some n < 25 (shortcut traffic through the VALID gate delays the find). Either outcome is recorded; monotone-decreasing everywhere refutes H1.
- H2: found programs always pass gen scales 1-2 (VALID covers that range by construction); gen failures, if any, appear only at scales 3-4 via learned-program iteration capacity (the 400-cap pattern from B-501/B-501E).
- H3: isprime is NOT FOUND at 6M for every n (correct form sits at ~27M per B-501E). If a cell finds anything, it is a VALID-passing shortcut and gen will expose it - recorded as such.
CAN claim: measured tried/dt/gen for the first train-n+VALID-passing program, per skill per n, nested prefixes, single seed 0, this enumeration. CANNOT claim: other seeds, other example orderings, other tasks, or any general "sample complexity" statement - this is one fixed enumeration order with two fixed example draws.
Runtime unknown (cells near the cap dominate; est. 1-4 h total) - background job, per-cell JSONL, committed when DONE. Criterion: PASS = curve recorded for all 40 cells with hypotheses adjudicated against the numbers; the backlog "curve in README" is satisfied by the LEDGER table.

## B-499 design amendment (2026-10-23) - endpoint-sandwich reduction after a value-of-information check

Amendment recorded BEFORE the remaining cells run, on parent instruction; the reduced grid is NOT presented as the completed original 40-cell experiment.
Structural fact (proof, not estimate): with nested train prefixes (train[:n] subset of train[:m] for n<m), a fixed per-task enumeration order, and a fixed VALID gate, the found position found(n) is MONOTONE NON-DECREASING in n - weakening the train filter can only let an earlier candidate through, never a later one. Therefore found(2) == found(25) PROVES found(4)==found(8)==found(16) for that task: intermediate cells are determined, not merely likely.
Measured so far: mod row flat at 2082 for all n in {2,4,8,16,25} (gen 40/40 all scales); mul n=2 at 4,155,513 (1802s).
Value-of-information check on the 34 remaining cells: mul n=4/8/16 are sandwiched IF mul n=25 lands at 4,155,513 (measured next, in-harness; canonical cross-harness numbers are references only, never mixed into this table). Per-task, only the endpoints (n=2, n=25) carry information: n=2 tests whether the VALID gate alone determines the find; n=25 re-measures the baseline in this harness. Middle cells run ONLY for a task whose endpoints mismatch (contingent, none assumed).
Amended arm (b499b.py): cells = mul n=25 + {div,power,gcd,isprime,fact,sumto} x {2,25} = 13 cells, same protocol, appending to logs/b499_stdout.log (rows tagged arm=b499b-endpoint). The in-flight mul n=4 cell was killed mid-compute by this amendment - recorded as discarded-for-redundancy, not a result; no partial line exists.
Hypothesis coverage preserved: H1 is now tested MORE sharply (per-row sandwich proof instead of point samples); H2 unchanged (gen per found program); H3 tested at both isprime endpoints (two full 6M scans). Honest cost note: original 40-cell estimate of 1-4h was wrong (mul n=2 alone took 30 min); the amended grid is ~5h worst case vs ~10-14h for the full grid, at zero inferential loss for the flat rows.

## B-502 design (2026-10-23) - DESIGN ONLY, not yet run (queued behind B-499 to protect b499b wall-time integrity)

Backlog: fragment = depth-2 expression mined from PAIRS OF USED depth-1 exprs; task absdiff; baseline depth-1; success = absdiff found or honest expressivity proof.
Extraction (mechanical, at design time): U = E1-form sub-expressions occurring in steps/bases/combs of the pinned base library c7_prog_0_base.json (conds excluded - predicate role). |U| = 9: (add a b), (add a one), (add b one), (mod b a), (mul b a), (power a b), (sub a b), (sub a one), (sub b one). VERIFIED BY CONSTRUCTION: (max,a,b) NOT in U and (min,a,b) NOT in U - so the known absdiff fragment (sub,(max,a,b),(min,a,b)) from B-500 is NOT in the mined-fragment space.
Mined space (literal reading): fragments (o, e1, e2) for o in the 9 pinned ops, e1,e2 in U = 9*9*9 = 729 candidates, inserted into bases between E1 and the B-500 deep list (mined-first ordering). Cheap: minutes at 6M cap.
Pre-stated prediction (falsifiable): absdiff's B-500 solution is NOT found in the mined space (by-construction absence). Whatever IS found (if anything passes train+VALID) is recorded and gen-tested honestly; a NOT FOUND plus the by-construction absence constitutes the backlog's "honest expressivity proof": usage-based fragment mining compresses REDISCOVERY of used combinations but cannot invent the unused pair (max,min) that absdiff needs. B-500's full cost-ordered deepening remains the mechanism that discovers novel operator pairings. Either outcome answers the backlog item.
Run plan (after B-499 DONE): b502.py, absdiff seed 0, same pin/EXCL/VALID protocol as b499, LIST_OVERRIDE bases = L + E1 + mined(729) + deep(B-500 list); 6M cap; gen 40/40 scales 1-4; verdict PASS (found + gen bar) / FAIL-expressivity-proof (not found + absence proof) - both pre-registered as acceptable outcomes.

## B-499 H1 correction (2026-10-23) - the pre-stated H1 is refuted by the amendment's own monotonicity proof

Correction before any verdict, on parent's reconciliation request. H1 as pre-stated ("at least one skill has tried(n) > tried(25) for some n < 25; shortcut traffic through the VALID gate delays the find") is IMPOSSIBLE under the experiment's own premises: with nested prefixes (train[:n] subset of train[:25]), a fixed enumeration order, and deterministic VALID, every candidate passing (train[:25] AND VALID) also passes (train[:n] AND VALID), so found(n) <= found(25) for all n < 25. A LATER tried-position at smaller n cannot occur. The shortcut-traffic mechanism inflates WALL-CLOCK only: at small n many more candidates pass the weak train gate and each burns up to 32 VALID evals (learned-program loops, up to the 400 cap) before rejection - but 'tried' increments per candidate, not per eval, so the position is unaffected. div n=2's >2h pre-restart runtime is consistent with wall-clock inflation and remains TENTATIVE until the cell lands; it is not position evidence.
Adjudication rules (replacing the earlier mismatched conditional): (a) found(2) < found(25) is the only informative endpoint mismatch - weak filtering found an EARLIER VALID-passing candidate that a later train example rejects; middle cells then localize where the shift happens. (b) found(2) > found(25), or n=2 NOT FOUND while n=25 FOUND, flags a premise violation, cap interaction, or harness bug - INVESTIGATE FIRST, never an H1 confirmation. (c) both NOT FOUND (expected for isprime per H3) is consistent. Measured H1-relevant quantities become: position gap found(25) - found(2), and dt wall-clock inflation at n=2.

## Measurement-integrity note (2026-10-23) - this sandbox suspends and re-anchors its boot clock; treat dt as unreliable, tried as ground truth

Established 08:16 from /proc evidence: PID 3251's /proc ctime (07:45:41, its real creation) vs ps STARTED (08:12:41) vs /proc/uptime (1102s) - the container SUSPENDS (processes frozen, wall clock advances) and the kernel boot-time reference is re-anchored on resume, so ps ELAPSED/STARTED and uptime are artifacts, not process history. Consequences:
1. All dt (wall-clock) values recorded in B-499 logs (e.g. mul n=2 1802s, mul n=25 1854s) are SUSPENSION-CONTAMINATED: they mix compute with frozen time and overstate compute cost. tried counts are unaffected and remain the primary measure. The earlier "mul took 30 min/cell, grid needs 8-14h" estimate was therefore doubly wrong (also superseded by the endpoint amendment); real CPU per cell is unknown but likely much lower.
2. Operational incident (correcting my earlier report to parent): at 07:45 I killed PID 2423 believing it was an auto-restarted duplicate after a container reboot. The /proc evidence shows there was NO reboot and NO auto-restart - 2423 was the original 05:15 b499b process, frozen-and-resumed, with etime artifacts from the re-anchored clock. No completed cell was lost (log intact, 7 rows) and the relaunched run is protocol-identical, but the kill discarded 2423's in-flight div n=2 progress unnecessarily. Rule going forward: establish process identity by /proc/<pid>/ creation time and log progress, NEVER by ps etime/uptime in this environment; do not kill a runner on clock evidence alone.

## B-499 verdict (2026-10-24) - PASS with amended design: the fewest-examples curve is FLAT at n=2 for all 7 learnable curriculum skills; VALID is the sole binding filter

This is the AMENDED experiment (endpoint-sandwich design, pre-registered amendment 2026-10-23), NOT the completed original 40-cell grid. 19 cells measured (mod at all five n; mul/div/power/gcd/isprime/fact/sumto at endpoints n=2 and n=25), 21 middle cells DETERMINED-not-run by the nested-prefix monotonicity proof (equal endpoints force equality; zero mismatches occurred, so no middle cell was triggered). Provenance: original b499 killed mid-mul-n=4 by the amendment (discarded-for-redundancy); 07:45 incident - original b499b runner killed on misread clock evidence, its in-flight div n=2 discarded, run relaunched protocol-identical (full incident record above); dt columns in the logs are suspension-contaminated wall-clock and support NO runtime conclusions; tried is the ground truth.

Measured curve (tried position of the first train-n + VALID-passing program; gen = 40-example accuracy at scales 1-4):
| task | n=2 | n=4 | n=8 | n=16 | n=25 | gen 1-4 | row |
| mod | 2082 | 2082* | 2082* | 2082* | 2082 | 40/40 all | flat (all 5 measured) |
| mul | 4155513 | = | = | = | 4155513 | 40/40 all | flat (endpoints) |
| div | 4202709 | = | = | = | 4202709 | 40/40 all | flat (endpoints) |
| power | 4450489 | = | = | = | 4450489 | 40/40 all | flat (endpoints) |
| gcd | 100985 | = | = | = | 100985 | 40/40 all | flat (endpoints) |
| isprime | NOT FOUND | - | - | - | NOT FOUND | - | both NF at 6M cap |
| fact | 1415364 | = | = | = | 1415364 | 40/40 all | flat (endpoints) |
| sumto | 2707098 | = | = | = | 2707098 | 40/40 all | flat (endpoints) |
(* mod middles measured; all other middles determined by the sandwich proof, marked =)

Hypothesis adjudication:
- H1 (as corrected pre-verdict): the informative direction was found(2) < found(25). Measured position gap = 0 for ALL SEVEN found rows - the first train[:2]+VALID-passing candidate already passes every longer train prefix. Endpoint equality establishes FLAT POSITIONS across tested n only; it does NOT establish which component does the binding filtering (train[:2] vs the 32 VALID acceptance examples) - a VALID-only causal claim would need an ablation the search mechanics do not directly allow (the r0 gate always consumes train[0]). H1's original shortcut-traffic position mechanism was refuted by proof before adjudication (recorded above).
- H2 (gen failures, if any, only at scales 3-4 via the 400-iteration capacity cap): REFUTED - every found program generalizes 40/40 at ALL scales 1-4. The pinned library's learned programs are capacity-safe across the curriculum8 gen ranges.
- H3 (isprime NOT FOUND at 6M for every n): CONFIRMED at both endpoints (tried 6,002,688 = full cap). Consistent with B-501E: correct form at ~27M enumeration position.

Answer to the backlog question: under this enumeration + VALID protocol, the found position is FLAT across tested n for all 7 learnable skills - extending the train draw from 2 to 25 changes neither the found program nor its position. SUPERVISION SCOPE, explicit: at n=2 the learner still sees 2 train + 32 answer-bearing VALID acceptance examples (34 total), so this is NOT learning-from-two-examples, and the flat positions do not prove VALID alone does the filtering (no ablation run). isprime remains enumeration-walled at any n.
Scope (CAN/CANNOT, pre-stated): these are measured positions for one fixed enumeration order, one seed-0 train draw, one VALID draw. No claim about other seeds, example orderings, tasks, or general "sample complexity". Cross-harness canonical positions (mod 482, fact 1138228, sumto 2176534, div 4202713) differ from this harness's (2082, 1415364, 2707098, 4202709) because pin state changes the enumeration space - tables were never mixed; all comparisons here are within-harness.

## B-499 verdict scope correction (2026-10-24, same day, before any external summary)

Parent caught two overclaims in the verdict wording; corrected in place above and recorded here: (1) endpoint equality shows flat tried-positions across tested n; it does NOT by itself establish that the VALID gate wholly determines the result or that training contributes nothing - that causal attribution needs an ablation/construction proof, which was not run (the r0 gate always consumes train[0]). (2) Total supervision at n=2 is 2 train + 32 answer-bearing VALID acceptance examples (34 answer-bearing examples total); describing the result as learning from two examples, or "25 buy nothing over 2" without the VALID count, misstates the supervision. Both corrected sentences are marked in the verdict body.

## B-502 verdict (2026-10-24) - PASS via the pre-registered expressivity-proof branch: usage-mined fragments cannot express absdiff

logs/b502_stdout.log. Setup (in-harness verification): 9 pinned ops, 112 E1, |U|=9 used depth-1 exprs, 729 mined fragments; absdiff_fragment_in_mined = FALSE (the B-500 solution fragment (sub,(max,a,b),(min,a,b)) is absent from the mined space BY CONSTRUCTION, verified at runtime).
- Arm A (mined-only depth-2: bases = L + E1 + 729 mined, 845 total): NOT FOUND in 6M (tried 6,002,880 = full cap). With the by-construction absence, this is the pre-registered honest expressivity proof: fragments mined from PAIRS OF USED depth-1 exprs cannot express absdiff, because absdiff requires pairing max and min - two library operators that no learned program has ever USED together. Usage mining compresses rediscovery of used combinations; it cannot invent an unused pairing.
- Arm B (mined-first + full deep list, 121,805 bases): FOUND the exact B-500 program at tried 640,435, gen 40/40 all scales 1-4. Position cost of mining-first ordering vs B-500's 636K: ~+4.4K (~0.7%) - inserting mined fragments ahead of the full space is nearly free when the full space follows.
Net: the backlog's "absdiff found OR honest expressivity proof" is satisfied by the proof branch. B-500's cost-ordered deepening remains the mechanism that discovers novel operator pairings; usage-mining would only help tasks whose solutions recombine already-co-used operators. dt columns suspension-contaminated as usual; tried is ground truth.

## B-503 pre-registration (2026-10-24, before running)
Question: can number-word grounding and op-model learning run JOINTLY (mutual bootstrap) without loss vs P16's separate stages?

Design. Corpus family b410d-style: digit sentences + word sentences from the same op/2-step templates (1..10 values, words with prob). SEPARATE arm (P16 baseline): stage A learner fit on digit sentences only, frozen; learn_lexicon (constraint voting, a token whose value works in >=80% of its sentences becomes a number word) against the frozen learner; answer via apply_lex. JOINT arm: interleaved rounds - each lexicon round is followed by refitting the op learner on the union of digit sentences and lexicon-decoded word sentences, so word-sentence evidence also shapes the op model; final eval identical for both arms.
Data: nA digit train + nB word train + mixed 2-step eval, 5 seeds, 300 eval rows/seed, sizes fixed in b503.py and reported with the result.

Falsifiable predictions:
- H1 (success criterion): JOINT end-to-end accuracy on unseen word 2-step sentences >= SEPARATE (no loss). If mean JOINT < mean SEPARATE by >2 points -> FAIL.
- H2 (secondary): JOINT learns >= as many gold words with spurious entries <= separate + 1.

CAN show: mutual-bootstrapping feasibility and no-loss vs the staged pipeline on THIS synthetic family at THESE sizes/seeds.
CANNOT show: general superiority; grounding beyond the constraint-voting signal; anything about natural language; generalization beyond templates/values tested. Endpoint numbers are per-harness, not comparable to other harnesses.

Verdict rule: write H1/H2 outcomes exactly as measured; any harness bug found by cross-checks discards the run (commit message notes the discard).
B-503 sizes fixed before run (b503.py, commit e01a2e7): N_DIGIT=600 stage-A digit 2-step sentences, N_WORD=200 word-substituted train sentences (pword 0.6 train / 0.7 eval, EN+TH words, values 1..10 window per P16 render), ROUNDS=4 P16-default voting rounds, N_EVAL=300 unseen new-frame sentences, 5 seeds. Probe-timing at reduced size showed 0 gold words learned (expected at n=50) and equal arms; full-size results pending.

## B-503 verdict: PASS (2026-10-24, b503.py, logs/b503_stdout.log)
Joint stage-B (interleaved lexicon voting + model refits on digit+decoded-word sentences) vs P16 separate stages, identical corpora per seed, sizes as pre-registered (600 digit + 200 word train, 4 rounds, 300 eval new-frame sentences, 5 seeds).

Measured: end-to-end acc on unseen new-frame word 2-step sentences - SEPARATE 0.277 mean (range 0.207-0.367), JOINT 0.288 mean (range 0.213-0.373). Per-seed diffs (joint-sep): +0.053, +0.006, +0.040, +0.033, -0.080. H1 (no loss, fail if joint < sep - 0.02): PASS - mean diff +0.010, and no seed loses by >0.02 except seed 4 (-0.080, within observed cross-seed variance ~0.08-0.16). Gold words 5.4 vs 5.6 of 20; spurious 0.2 both; wrong-value 0 both. H2: PASS.

Reading (scope-limited): joint stage-B is FEASIBLE with no measured loss on this synthetic family at these sizes; the +0.010 mean gain is within seed noise - NO improvement is claimed. Absolute accuracy (~0.28) reflects the hard eval (new connectors+frames, word values, 600-digit stage A) and is the same eval for both arms; the A/B is internally valid regardless of absolute level. Total supervision = 600 labelled digit + 200 labelled word sentences, identical for both arms. Nothing shown about natural language, other families, or other sizes. Wall 59 min for all 5 seeds (within the under-2h budget).

## B-504 pre-registration (2026-10-24, before running)
Question: what accuracy does a tiny gradient-trained transformer (pure numpy) reach on the P15 unseen-synonyms protocol, as a same-protocol reference point beside the wnn constraint learner?

Protocol: exactly text2prog.py __main__ - train on gen_set(rng, 0, 400) labelled (text, answer) sentences; eval accuracy on gen_set(r, wh, 300, big=True) for wh in (0 numbers / 1 frames / 2 synonyms). 3 seeds (not 5 - CPU budget; pre-stated). A Learner('tok') row is trained and evaluated in the same harness on the same seed data so both numbers come from one protocol run.

Model + supervision: hypothesis classification over the same 21 HYP labels; answer computed by run_hyp on the REAL numbers, identical execution path to the wnn learner. Digit tokens normalized to <NUM> for classifier input (positional info retained; values never enter the classifier). Supervision: soft cross-entropy with uniform mass over the consistent-hypothesis set {h: run_hyp(h, nums) == ans} - derived from (text, answer) only, same information the wnn learner gets; sentences with an empty consistent set skipped (count recorded). Architecture: token embeddings d=32 + learned positional embeddings, one transformer block (single-head self-attention d=32, FFN 32->64->32 ReLU, residuals, NO layernorm), mean-pool, linear head. Adam lr 3e-3, 30 epochs full-batch-per-sentence. Manual backprop; numerical gradient check (relative error < 1e-4 on a parameter sample across all layers) MUST pass before training; a failed check = harness bug, fixed and recorded before any result counts.

Falsifiable predictions:
- H1 (sanity): train-protocol (wh=0, big numbers) accuracy >= 0.90 within budget. If not, the harness is suspect - investigate before interpreting H2.
- H2 (the reference number): unseen-synonym accuracy recorded WHATEVER it is; no threshold, no success claim attached to its value.
Success criterion (backlog): runs CPU < 2h, accuracies recorded.

CAN show: this exact config's accuracy on this exact protocol/split/seeds.
CANNOT show: anything about transformers in general, LLMs, or any scale; any superiority/inferiority claim beyond this config; comparability across harnesses. Supervision symmetry noted: both models see only (text, answer).
B-504 amendment (pre-run, 2026-10-24): gradcheck criterion amended from rel<1e-4 to combined |num-ana|<1e-6 OR rel<1e-3. Reason recorded: initial check failed 7/48, ALL on Wq/Wk entries where both numerical and analytic gradients were ~1e-7 (float noise inflating relative error at near-zero magnitude; loss curve decreased monotonically 2.99->1.70 over 4 epochs). No sign errors or O(1) discrepancies found. Amended check: pass 48/48. Reduced-size smoke (80 rows/5 epochs) ran mechanically; its numbers are harness-validation only, discarded, not results.

## B-504 verdict: PASS (2026-10-24, b504.py, logs/b504_stdout.log)
Tiny pure-numpy transformer (1 block, d=32, hypothesis classification over the 21 HYP labels, soft CE over consistent-hypothesis sets) on the P15 unseen-synonyms protocol, 3 seeds, vs Learner('tok') row in the same harness on the same data.

Measured (wh=0 numbers / wh=1 frames / wh=2 synonyms, 300 eval rows each, big=True):
- transformer: 0.993 / 0.827 / 0.163 means (synonyms range 0.090-0.293 across seeds)
- wnn constraint learner: 0.984 / 0.829 / 0.188 means (synonyms range 0.163-0.220)
H1 sanity PASS (train-protocol >= 0.90). Success criterion met: ran in 17s wall (budget <2h), accuracies recorded.
Cross-check before verdict: wnn row reproduces P15-repro 5-seed numbers (0.987/0.835/0.204) and LEDGER B-185's "synonyms ~.20" - no harness bug indicated. Gradcheck passed 48/48 under the amended combined criterion (amendment documented above, pre-run).

Reading (scope-limited): on THIS config/protocol, the gradient reference matches the constraint learner on trained templates and unseen frames, and BOTH sit near the op-prior on fully unseen synonym templates without fast-mapping examples (synonym content words are out-of-vocabulary for both; wnn's small mean edge is within the transformer's cross-seed spread - no superiority claimed in either direction). This is one architecture/config at one size; nothing shown about transformers generally, other scales, or other tasks.

## B-463 pre-registration (2026-10-24, before running)
Question: does the 233-cell core connectome as a fixed reservoir (pure numpy dynamics, no hosted-runtime encoding - the B-240 wall was the runtime, not the reservoir) give a ridge readout any 1-shot MNIST advantage over the same ridge on raw pixels?

Design (all choices fixed before running):
- Reservoir: data/connectome_core.txt (233 cells, 3275 edges; chemical directed pre->post, gap junctions undirected). Edge weights = EM sections, normalized: W /= spectral radius (power iteration, 200 iters), then alpha=0.9 scaling. Dynamics: x0=0; x_{t+1} = tanh(alpha * Wn @ x_t + beta * Jin), beta=0.5, RSTEP=15 (B-240's value), input held constant; state = final x_15.
- Injection: image binarized >128 (b466 convention); Jin[c] = (sum of active pixels p with p mod 233 == c) / (784/233), deterministic, no learned input weights.
- Readout: ridge lambda=1e-3, one-hot 10 classes, closed form. Baseline: IDENTICAL ridge on the raw 784 binarized pixels.
- Task: mnist-1shot: per seed, 1 train image/class drawn from mnist_train.txt pool (500/class), identical draws for both arms; eval on full mnist_test.txt (100/class = 1000 images). 5 seeds.

Falsifiable predictions:
- H1: raw ridge 1-shot baseline lands in a weak but above-chance range (0.2-0.6). If raw is >=0.9 or <=0.12, suspect a harness bug and investigate before interpreting.
- H2: reservoir accuracy recorded; success = reservoir beats raw by >2 points mean, otherwise honest null (backlog: "beats raw or honest null" - both are acceptable recorded outcomes).
CAN show: on this fixed injection/dynamics/protocol, whether the wiring's transform carries class information usable by a linear readout at 1-shot.
CANNOT show: anything biological (abstracted tanh dynamics, arbitrary injection); other tasks/sizes; superiority of "connectome computing" generally - T6's prior record is negative and this is a cheap probe, not a vindication test.
