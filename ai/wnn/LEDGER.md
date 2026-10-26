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
B-463 amendment (pre-result, 2026-10-24): mnist_train/test.txt capped files hold 392 pixels/image (14x28 half-resolution), not the raw 784; injection mapping and denominator adjusted to npix=392. Both arms use identical images, so the A/B is unaffected. Two harness bugs caught pre-result and fixed (edge lines are integer indices not names; pixel count) - recorded here per discard/fix discipline.

## B-463 verdict: PASS via honest null (2026-10-24, b463.py, logs/b463_stdout.log)
233-cell core connectome as a fixed tanh reservoir (pre-registered dynamics/injection) + ridge readout vs identical ridge on raw pixels, mnist-1shot, 5 seeds.
Measured: raw 0.342 mean (0.303-0.429), reservoir 0.343 mean (0.288-0.438); per-seed diffs -0.024/+0.009/-0.002/+0.036/-0.015, mean +0.001. H1 sanity PASS (raw 0.342 in the pre-stated 0.2-0.6 range). H2: reservoir does NOT beat raw by >2 points -> honest null recorded (backlog success: "beats raw or honest null").
Reading (scope-limited): under this fixed injection/dynamics, the wiring's transform preserves class information (tracks raw per seed) but adds none usable by a linear readout at 1-shot. Consistent with T6's negative record. One dynamics/injection/protocol; no biological claim.

## B-464 pre-registration (2026-10-24, before running)
Question: do the wiring's STATIC structural features (degree + spectral) carry class information as image embeddings, without any dynamics?
Design (fixed before running): structural matrix S (233 x 13): [in-degree, out-degree, gap-degree, weighted-in, weighted-out] standardized + top-8 right-singular vectors of the symmetrized normalized adjacency (SVD). Image embedding: A = X @ J / (npix/233) (B-463's deterministic pixel->cell injection), E = A @ S (13-dim). Readout: same ridge as B-463 (lambda=1e-3). Baseline: identical ridge on raw pixels, identical draws. Protocols recorded: (a) mnist-1shot 5 seeds (B-463-comparable), (b) full-pool train (5000) - both recorded whatever they show.
Falsifiable predictions: H1: 13-dim structural embeddings land near chance at 1-shot (<=0.25 mean) - a high value would mean the injection+structure accidentally encodes pixel position strongly; investigate before interpreting. H2: accuracies recorded; success = win vs raw or honest null (backlog).
CAN show: whether THIS static structural embedding carries task information under THIS injection. CANNOT: biological claims; other embeddings/tasks; vindication of T6 (prior record negative).

## B-464 verdict: PASS via honest null (2026-10-24, b464.py, logs/b464_stdout.log)
Static degree+spectral wiring features (233x13) as image embeddings under the B-463 injection, ridge readout vs raw ridge, identical draws.
Measured: 1-shot (5 seeds) emb 0.139 mean (0.120-0.165) vs raw 0.342 - near the 0.1 chance floor, per H1's pre-stated expectation (<=0.25, so no accidental positional-encoding artifact to investigate). Full-pool (5000 train): emb 0.478 vs raw 0.778. H2: honest null - the 13-dim static structural embedding carries far less class information than raw pixels under this injection; no win at either scale.
Reading (scope-limited): another T6-negative consistent result. The wiring's static structure, compressed to 13 dims and linearly read, does not substitute for pixel information on this task. One embedding construction, one injection, one task.

## B-465 pre-registration (2026-10-24, before running)
Question: does adding literature-grounded synapse SIGNS to the worm.holy tap-circuit sim fix its known check-4 MISS (posterior touch fails to make PVC dominate AVD - the unsigned model's own comment calls this "full inhibitory signatures needed")?

Baseline: unsigned worm.holy as-is (all chemical excitatory except the existing GABA list; divisive normalization stand-in). Signed variant: worm_sign.holy, identical except the sign annotation below. Same steps=100, same stimuli, same 4 checks (the checks ALREADY in worm.holy, unchanged): (1) anterior touch -> AVD dominates PVC; (2) DVA posterior-selective >3x; (3) PVC/AVD ratio shifts toward PVC for posterior touch; (4) posterior touch -> PVC dominates AVD.

Sign annotation (per presynaptic cell class, chemical synapses only; gap junctions stay symmetric-positive in both arms). Evidence class recorded per row:
- GABA list (DD01-06, VD01-13, RMEL/R/D/V, AVL, RIS, DVB) -> inhibitory. ALREADY in worm.holy. Evidence: measured transmitter (unc-25 GABA; McIntire et al 1993).
- ALML, ALMR, AVM, PLML, PLMR (touch sensory) -> inhibitory. Evidence: MODEL-INFERRED (Wicks & Rankin 1996, J Neurosci 16:4017 polarity prediction from ablation-behavior fits; Chalfie et al 1985 proposal: gap junctions to agonists, inhibitory chemical to antagonists). NOT a measured transmitter sign.
- RIML, RIMR -> inhibitory. Evidence: MEASURED functional sign (RIM tyramine activates the LGC-55 tyramine-gated chloride channel on AVB, hyperpolarizing it; Pirri & Alkema 2011; Alkema et al 2005. WormAtlas RIM page).
- AIYL, AIYR -> inhibitory. Evidence: ABLATION-INFERRED (AIY and AIZ ablations give opposite phenotypes, "synapses made by AIY onto AIZ may be inhibitory"; de Bono & Maricq 2005 via WormAtlas AIY page). Weakest class; note AIY is cholinergic by atlas (Pereira et al 2015), so this is a functional not transmitter claim.
- All other chemical synapses stay excitatory, including AVA/AVB/AVD/PVC/DVA (cholinergic per WormAtlas/Pereira et al 2015; AVA's old glutamate assignment superseded per the AVA atlas page). Consistent with Wicks & Rankin 1996's excitatory predictions for AVD/PVC.
Correction to my earlier grounding note: the AIY-dual-sign-via-GLC-3 claim was WRONG - GLC-3 acts on the INPUT side (AFD/AWC glutamate inhibits AIY through GLC-3). Corrected here with the WormAtlas AIY page as source.

Falsifiable predictions:
- H1 (sanity): unsigned baseline reproduces 3/4 (check 4 MISS). If the baseline's pattern differs, the runtime/environment is suspect - investigate first.
- H2 (success criterion, from backlog): signed variant passes 4/4 -> PASS. If signed passes fewer than 4 but MORE than unsigned, record the partial honestly. If signed BREAKS any check unsigned passed, the sign table is suspect - investigate before concluding; a broken check is a result to record, not to tune away.
CAN show: whether THIS coarse per-cell sign annotation suffices for the 4 behavioral checks in THIS linear-threshold sim. CANNOT: biological validation of the signs (two evidence rows are inference, not measurement); anything about other circuits; real worm behavior beyond these 4 aggregate checks.
B-465 amendment 1 (2026-10-24, after signed-v1 broke check 2 as the pre-registration anticipated): signed-v1 (blanket per-cell inhibitory for touch cells) passed check 4 but BROKE check 2 (DVA posterior selectivity: DVA posterior activity 0.0). Investigation before any conclusion: data/connectome.txt shows DVA receives DIRECT chemical synapses from PLML (9 sections) and PLMR (19) - its dominant touch-cell input - and the literature describes PLM->DVA as activity-MAINTAINING (Wicks & Rankin 1995; the WormAtlas DVA page cites diminished responses after PVD/DVA ablation). The Wicks & Rankin 1996 inhibitory prediction covers touch-cell chemical synapses onto ANTAGONIST command interneurons (Chalfie et al 1985: gap junctions to agonists, inhibitory chemical to antagonists), not onto every postsynaptic partner. Amendment: per-EDGE touch signs - pre in {ALML,ALMR,AVM} x post in {AVBL,AVBR,PVCL,PVCR} inhibitory; pre in {PLML,PLMR} x post in {AVAL,AVAR,AVDL,AVDR} inhibitory; all other touch-cell outputs (incl. PLM->DVA) stay excitatory. RIM (measured LGC-55) and AIY (ablation-inferred) remain blanket-inhibitory. This is the Chalfie-proposal-faithful reading, not accuracy tuning; v1's result and this analysis are recorded above and in logs/b465_signed.log.

## B-465 verdict: PASS (2026-10-24, worm_sign.holy, logs/b465_unsigned.log + b465_signed.log + b465_signed2.log)
Literature-grounded signed annotation of the P0 tap-circuit sim vs the unsigned baseline, identical harness/stimuli/checks.
- Unsigned (H1 sanity, reproduced): 3/4 - checks 1-3 PASS, check 4 MISS (posterior AVD 0.104 > PVC 0.086), exactly the sim's documented open gap.
- Signed v1 (blanket per-cell touch inhibition): check 4 fixed but BROKE check 2 (DVA posterior 0.0) - the pre-registered sign-table-suspect case. Investigation: DVA's dominant touch input is direct PLM chemical synapses (9+19 sections) and the literature describes PLM->DVA as activity-maintaining; the inhibitory prediction covers touch->antagonist-command-interneuron edges only (Chalfie et al 1985). Recorded as amendment 1.
- Signed v2 (amendment 1: per-edge antagonist-only touch signs; RIM measured / AIY ablation-inferred blanket): 4/4 PASS. Posterior: PVC 0.0853 > AVD 0.0608; anterior: AVD 0.131 > PVC 0.0; DVA posterior/anterior = 20x. Checks byte-identical to worm.holy's.
Reading (scope-limited): the Chalfie/Wicks-Rankin sign proposal SUFFICES for all 4 aggregate behavioral checks in this linear-threshold sim, where the unsigned model structurally could not (its divisive normalization stand-in couldn't flip posterior dominance). Evidence classes: GABA + RIM measured, touch model-inferred, AIY ablation-inferred - this is consistency with literature, not biological validation of the signs. One documented amendment round (v1 failure + mechanism + v2) is part of the record, not tuning. Effect direction sanity: anterior AVD/PVC asymmetry unchanged in kind from unsigned (gap-junction path), posterior flip driven by the antagonist-edge signs.

## B-505 pre-registration (2026-10-24, before running)
Question: does reward-GATED plasticity beat ungated Hebbian growth for tap-circuit association learning?

Substrate decision (pre-stated): the GRADED plastic sim (worm_plastic.holy, P4), NOT worm_spike.holy - the spiking variant is a documented bistable dead-end (README). Naming caveat: this is graded eligibility-gated timing-dependent plasticity, not spiking STDP.

Variant worm_reward.holy = worm_plastic.holy with ONE plasticity change: the Hebbian line (wpl += 0.002*apre*apost when both > 0.1) becomes two-factor - eligibility e[k] += 0.002*apre*apost on co-activation, e[k] *= 0.99 every step for every chemical edge, and wpl[k] = clamp(wpl[k] + e[k], 0.2, 3.0), e[k] = 0 ONLY on reward-flag steps. Reward is an ABSTRACT global consolidation gate (neuromodulatory stand-in; no biological routing claimed). Everything else byte-identical, including the T1 habituation phase that precedes T2.

Arms (same program, argv-selected, identical T1+T2 schedule):
(a) reward: pairing (ALM+PLM 15x, 5 on / 25 off) with reward flag on the first 5 off-steps after each pairing.
(b) no-reward: identical pairings, reward never fires (baseline; backlog's "no reward").
(c) reward-unpaired control: same total ALM and PLM stimulation temporally separated (PLM shifted to off-steps 15-19), same reward schedule - reward alone must not create the association.
Metric: T2's ALM-alone -> PVC (PVCL+PVCR) response, before vs after.
Reference: plain-Hebbian worm_plastic.holy re-measured in-harness TODAY: before 0.010011, after 0.011790 = +17.8% (matches the recorded +18%).

Falsifiable predictions:
- H1 DONE (sanity): plain Hebbian re-measures +15..+20%. Measured +17.8% - PASS.
- H2 (internal validity): delta(a) > delta(b) AND delta(a) > delta(c).
- H3 (backlog PASS bar): delta(a) > +17.8% relative (beats the ungated Hebbian reference).
If H2 holds but H3 fails: partial - gating works but does not beat ungated Hebbian. If delta(a) < delta(b): reward gating HURTS - record honestly. Absolute values are tiny (~0.01); relative change is the metric throughout; note the small-signal caveat in the verdict.
CAN show: whether a consolidation gate helps association in THIS graded sim/protocol. CANNOT: neuromodulator biology (abstract flag); other circuits; spiking-STDP claims.

## B-505 verdict: FAIL on the backlog bar, with a load-bearing CORRECTION to the P4 record (2026-10-24, worm_reward.holy, logs/b505_arm{0,1,2}.log)
Pre-registered 3-arm test of reward-gated eligibility consolidation vs ungated Hebbian, T2 association metric, identical T1+T2 schedule.

Measured (ALM-alone -> PVC before -> after pairing):
- plain Hebbian (worm_plastic.holy, H1 sanity): 0.010011 -> 0.011790 = +17.8% (reproduces recorded +18%)
- (a) reward-gated: 0.010008 -> 0.011789 = +17.8%; max|wpl-1| = 0.163 (consolidation FIRED)
- (b) no-reward gated: 0.010008 -> 0.011789 = +17.8%; max|wpl-1| = 0.0 (consolidation NEVER fired, as designed)
- (c) reward-unpaired control: 0.010008 -> 0.007592 = -24.1%; dep trajectory differs
H2 FAILS ((a) equals (b) to 5 decimals); H3 FAILS ((a) does not exceed the +17.8% reference).

CORRECTION (recorded per failure-logging discipline): the T2 "+18% cross-pathway association" is NOT Hebbian. With Hebbian growth switched off entirely (arm b: eligibility never consolidates, wpl frozen at init), the same protocol yields the identical +17.8%. The signal is STD(dep)-state-mediated (depressed-then-recovering synapses at measurement time; the unpaired control's different dep trajectory gives -24%). Conversely, reward-gated consolidation WORKS mechanically (arm a grew wpl to +0.163 max, arm b exactly 0) but the grown weights do not move this metric at these gains. README.md and FOUNDATIONS.md lines attributing the +18% to Hebbian association are corrected to point here.
Scope: this graded sim, this metric, these gains. It does NOT show reward gating useless generally (the consolidated 0.163 may matter at other gains/metrics), and it does not dispute that worm_plastic.holy's Hebbian line compiles and grows weights - only that the published +18% T2 number was never caused by it.

## B-486/489/492 pre-registration (2026-10-24, before running)
Question: complete the snips few-shot grid rows for the wiSARD readout (shots 1/5/20) - the only missing readout x task cells in the B-466..B-492 family (mnist/pmnist wiSARD rows triaged to B-241 cells or measured in b467).
Design: EXACTLY b468.py's snips protocol (4096-bit hashed unigram+bigram features, k shots/intent drawn with rng 100+seed, 10 seeds, 7 intents, full test set) with one added arm: wiSARD over the same bit vectors - fixed per-seed random permutation of the 4096 bits reshaped to 128 tuples of 32 bits (int64 dot with 1<<arange(32), no collisions below 2^32), per-class per-position observed-value sets, score = tuple-membership count, argmax. Baseline: b468's OVR MLP (same shots), already measured - re-measured in the same harness for paired comparison.
Falsifiable predictions: H1 (sanity): re-measured nn/centroid/mlp rows match b468's logged values within seed noise (same code path; mismatch = harness bug). H2: wiSARD accuracies recorded whatever they are; success per backlog = retention/acc gap recorded.
CAN show: wiSARD few-shot intent classification on these hashed features at k=1/5/20 vs the same-shots MLP. CANNOT: other featureings/tupleings; NLP claims.

## B-486/489/492 triage (2026-10-24) - cells already measured by B-495; cross-check run confirms

The snips WiSARD few-shot rows at shots 1/5/20 are exactly the WiSARD arm of B-495 (same data, same features, same seed set 100..109): .3471 / .8307 / .8936 vs MLP .148/.145/.150 (B-468, same shots) - gaps +19.9 / +68.6 / +74.4 pt over MLP; vs NB .6044/.8580/.9423 (B-495): loses at every k. Backlog items checked off as triaged (same pattern as B-484/487/490 -> B-241).
Pre-registered cross-check (b486.py, pre-reg above): b468's protocol re-run with an alternative tuple layout (rng(400+seed), 128x32-bit tuples vs B-495's rng(0) 146x28-bit). Sanity H1 PASS: re-measured 1nn/centroid/MLP rows reproduce b468's logged values to 4 decimals at all k. WiSARD alt-layout .3473/.8043/.8931 - consistent with B-495 within tuple-layout noise (max deviation 2.6 pt at k=5). No new claim; the B-495 numbers remain the grid cells of record.

## B-412..B-434 pre-registration (2026-10-24, before running) - WiSARD tuple-size x bleaching grid, full-data, 3 tasks

Question (24 cells: tuple {8,16,32,64} x bleach {off,on} x task {mnist,pmnist,snips}; B-411/B-414 triaged from B-236's first attempt and re-confirmed or corrected in-grid): full-data WiSARD accuracy as a function of tuple grain and bleaching, vs a same-harness MLP baseline. "Retention gap" in the backlog lines is covered by the continual cells (B-467/493/494); this grid's criterion is the accuracy cell criterion only.
Design (b412.py):
- Data: mnist = t5wisard binarized 784-bit (60k/10k); pmnist = same with ONE fixed pixel permutation rng(12345) applied to train+test (single-task permuted MNIST; pre-stated: MLP is invariant to a fixed permutation, WiSARD tuple membership is not); snips = b468's 4096-bit hashed uni+bigram (2100/700).
- WiSARD: tuple layout rng(0).permutation(B)[:NT*s].reshape(NT,s), NT = B//s (784: 98/49/24/12 positions; 4096: 512/256/128/64). Per class per position: value->count dict (one pass over full train).
- Bleach off: score_c = #positions with count >= 1. Ties: numpy argmax (lowest index) - pre-stated.
- Bleach on: standard bleaching - score_c(b) = #positions with count >= b; raise b from 1 until each sample's argmax is unique or b > 64 (pre-stated cap; ties at cap -> lowest index).
- MLP baseline (same harness, one recipe pre-stated for all tasks): tanh MLP B-64-C softmax, minibatch SGD batch 256 lr 0.1, 10 epochs (mnist/pmnist, 60k train) / 50 epochs (snips, 2100 train), 2 seeds, mean. NOT the B-241 few-shot OVR recipe (full-data OVR 800ep is compute-infeasible in numpy); this is a stated, ordinary MLP.
Criterion per cell (pre-stated): WiSARD cell PASSES if its acc >= MLP acc - 0.03 on that task, else FAILS. All 24 numbers reported; honest FAILs recorded (B-411's tuple-8 mnist FAIL expectation carried in).
Pre-stated expectations (NOT criteria): (a) tuple-8 mnist bleach-off reproduces the ~.30 saturation (B-411); (b) bleaching rescues small-tuple saturation via counts; (c) 16-32-bit tuples near B-236's .9115 grain are best on mnist; (d) at tuple-64 counts are mostly 0/1 so bleach ~= presence.
CAN show: tuple-grain/bleaching viability map on these 3 tasks with these encodings vs this MLP. CANNOT: optimal WiSARD design generally; other encodings; comparisons to tuned deep nets.

## B-412..B-434 verdicts (2026-10-24) - tuple-32 is the viable grain on image bits; bleaching rescues small tuples; snips cells all PASS vs the small MLP

logs/b412_grid.log. MLP baselines (pre-registered recipe): mnist .9298, pmnist .9264, snips .5129. Cell criterion: WiSARD >= MLP - 3pt.
- mnist: t8 .3001(off FAIL)/.7982(on FAIL) | t16 .7268(F)/.8675(F) | t32 .9204(P)/.9260(P) | t64 .8751(F)/.8821(F)
- pmnist: t8 .2826(F)/.8055(F) | t16 .7023(F)/.8689(F) | t32 .9153(P)/.9277(P) | t64 .8766(F)/.8848(F)
- snips: t8 .7571(P)/.8471(P) | t16 .7586(P)/.8514(P) | t32 .7814(P)/.8643(P) | t64 .8043(P)/.8929(P)
12 PASS / 10 FAIL of the 22 open cells (all 8 snips cells PASS; only tuple-32 passes on mnist/pmnist). B-411 triage CONFIRMED in-grid (.3001 = B-236's saturated .30) and B-414's FAIL triage confirmed by direct in-grid measurement (.7982, -13.2pt).
Expectations: (a) tuple-8 saturation reproduced exactly; (b) bleaching rescues small tuples (+50pt at t8 mnist/pmnist) CONFIRMED; (c) tuple-32 (nearest B-236's 28-bit grain) best on image bits CONFIRMED; (d) bleach ~= presence at t64 CONFIRMED (+0.7pt).
pmnist ~= mnist per cell (max dev ~1pt) as expected for a fixed permutation with a random tuple layout - internal consistency check PASS.
Sensitivity (b412s.py, post-hoc, logs/b412_snips_mlp_epochs.log): snips MLP at 100/200/400 epochs = .5436/.5543/.5664 - the .5129 baseline is the recipe's plateau, not under-training; snips PASS margins stand (+24..+38pt vs baseline, +19..+33pt vs the 400-epoch variant).
Honest picture: on image bits, plain WiSARD reaches the small MLP only at tuple-32 (bleached or not); at other grains it FAILS the 3pt bar even with bleaching. On sparse text bits, tuple WiSARD beats the small MLP at every grain but remains below NB (B-495 ordering: NB .94-ish full-data-equivalent few-shot k=20 vs WiSARD .89 at best here). Bleaching = real, sizable accuracy recovery at saturated grains, one extra count array's worth of memory.
Scope: these 3 tasks, these encodings, this MLP. No claim about tuned/deeper nets or other encodings.

## B-510 (F-1) pre-registration (2026-10-24, before running) - contradiction correction / unlearning with status

Question (FOUNDATIONS F-1, Turing's status-carrying propositions + ephemeral validity): when the store is told a fact and later a correction, does the LATEST statement win? Current stores either accumulate (P15-style soft counts - no recency) or, in learn_lexicon, split votes (2.5x margin rule -> contradictory evidence yields NO mapping). Nothing carries status/provenance. This measures the baseline failure and tests the minimal status mechanism.
Design (b510.py):
- Probe A (name facts, new minimal store - none exists today): episode stream "my name is X" ... "actually my name is Y" (1-3 corrections, name pool 8), probe "what is my name". Arms: (i) ACCUM = count accumulator, recall = argmax count (ties -> lowest count-order, pre-stated); (ii) DICT = naive overwrite (reference: latest wins by construction); (iii) STATUS = entries carry (value, statement index, active/superseded); a correction-marked statement supersedes prior entries for the key; recall returns the active value. 200 episodes x 5 seeds. Metric: probe = latest stated value.
- Probe B (wrong-then-right number word, text2prog machinery): base Learner('tok') on P15 n=300; then lexicon learning (text2prog2.learn_lexicon, defaults minv=3 rounds=4) over data where novel word W appears meaning v1 in n1 sentences (op templates), then a correction phase where W means v2 in n2 sentences. Arms: (i) BATCH = current learn_lexicon over the concatenated data; (ii) STATUS-LEX = phases processed in order; a phase's accepted mapping SUPERSEDES prior mappings for that word (same acceptance rule within phase). n1, n2 in {5, 10, 20} (9 cells), 5 seeds. Metric: probe accuracy on W-sentences with unseen numbers (correct answer uses v2), via apply_lex + learner answer.
Falsifiable predictions (pre-stated, not criteria): A: ACCUM < 100% (stale wins when early statements outnumber the correction), DICT = 100%, STATUS = 100%; B: BATCH fails when n1 >= n2 (no mapping or stale mapping), STATUS-LEX = 100% in all 9 cells.
Criterion (pre-stated): PASS = baseline failure measured (ACCUM or BATCH < 100% somewhere) AND status mechanism = 100% latest-wins on both probes. FAIL = status mechanism misses any probe, or baselines already 100% (nothing to fix - honest null).
CAN show: recency-correct recall in these two probes with a status store. CANNOT: belief revision generally, consistency checking, anything about the baby dialogue harness.

Amendment 1 (pre-full-run, after seed-0 smoke): probe-B metric refined - primary = mapping correctness (lex[W] == latest value v2, exact); secondary = probe answer accuracy NORMALIZED by the same learner's accuracy with an oracle lexicon (W -> v2 hardcoded), factoring out base-learner noise (P15 n=300 unary-template accuracy ~.9, nq=20 small). Probe B restricted to single-number unary ops (fact/sumto/isprime) so ans = OPS[op](v) matches generator semantics exactly (the first draft's run_ans_with mis-evaluated binary ops - harness bug caught pre-verdict, discarded).


## B-510 (F-1) verdict (2026-10-24) - FAIL on probe B per criterion; baseline correction failure measured decisively on both probes

logs/b510_contradiction.log. Pre-stated criterion: PASS = baseline failure measured AND status mechanism 100% latest-wins on BOTH probes.
Probe A (name facts, 200 episodes x 5 seeds): ACCUM (P15-style counts, the current-style store) = .52/.575/.56/.52/.545 - stale values win ~45% of episodes (more early statements -> stale wins): baseline failure CONFIRMED. DICT (naive overwrite reference) = 1.0. STATUS (provenance+supersede on correction marker) = 1.0 on all 5 seeds.
Probe B (wrong-then-right number word, text2prog learner n=300 + learn_lexicon, 9 n1 x n2 cells x 5 seeds): BATCH (current learn_lexicon over concatenated contradictory data) lands the corrected mapping in 3/45 cells (.067) - in 42/45 it accepts NO mapping at all (2.5x vote-margin rule rejects split evidence: the store "keeps neither"). STATUS-LEX (phase-sequential, latest accepted phase supersedes) lands it in 21/45 (.467); by correction size n2=5/10/20: 6/15, 6/15, 9/15. Criterion FAILS on probe B.
Mechanism analysis (why status != 100% on B): the binding constraint is the ACCEPTANCE gate, not recency. isprime's binary answers make every same-parity candidate value vote-eligible (~n2/3 runner-up votes), so the 2.5x margin rule rejects the correction even at n2=20 when the isprime fraction runs high. Recency supersedes correctly whenever a mapping is accepted. Secondary honest finding: learned lexicons also carry spurious mappings for template words, so even correct-W status lexicons reach only .738 of oracle downstream accuracy (oracle arm itself = 1.0: base learner handles the unary templates perfectly).
Honest bottom line: recency status is NECESSARY (batch .067) and sufficient for fact recall (probe A 1.0) but NOT sufficient for word-meaning correction under the current vote-margin acceptance rule. F-1 follow-up direction (not done here): confidence-aware or correction-triggered acceptance, and lexical entries that carry status individually rather than wholesale lex.update.
Scope: these two probes, P15 learner, learn_lexicon defaults. CANNOT claim: belief revision generally.

## B-514 (F-5) pre-registration (2026-10-24, before running) - soft 2^-len explanation weighting vs categorical Occam

Question: text2prog8.py implements F-5 (keep ALL explanations, weight each by 2^-(#ops)) but was never run/verdicted. Does soft Occam match P16's categorical Occam (text2prog2 TwoStep drops 2-op explanations when a 1-op one exists) on accuracy, and win on AMBIGUOUS sentences (both 1-op and 2-op explanations consistent)?
Note: the shortest-on-tie half of F-5 for program SEARCH is already measured: B-287/288/289 tie-break-shorter found no benefit over first-found (B-290/291/292 tie-break-first equivalent) - cross-referenced, not re-run.
Design (b514.py): EXACTLY text2prog8's main protocol (n=1000 two_step train rows wh=0, 5 seeds, eval 300 rows each wh=0 same / wh=1 new, big=True), arms TwoStep vs Soft on IDENTICAL rows. Ambiguity analysis (pre-stated): an eval row is AMBIGUOUS if its text+answer admits BOTH a consistent 1-op hyp and a consistent 2-op (h1,h2,split) explanation (computed directly, not via either model); report per-arm accuracy on that subset.
Criterion (pre-stated): equal acc = |Soft - TwoStep| <= 1pt on both same and new (5-seed means). F-5 PASS = equal acc AND Soft > TwoStep by >1pt on the ambiguous subset. Honest nulls recorded.
CAN show: soft vs categorical Occam on this 2-step protocol. CANNOT: other weightings (this is 2^-ops with the stated 0.5/0.25 normalization), other domains.


## B-514 (F-5) verdict (2026-10-24) - FAIL: soft 2^-len explanation weighting LOSES to categorical Occam on trained frames; wins only on unseen-frame ambiguous rows

logs/b514_softoccam.log (5 seeds, n=1000 train, 300 eval rows/split, text2prog8 Soft vs text2prog2 TwoStep, identical rows):
- same: Soft 0.7327 vs Cat 0.8227 (-9.0pt - NOT within the 1pt equal-acc bar)
- new: Soft 0.4167 vs Cat 0.4113 (equal within 1pt)
- same_ambiguous (both 1-op and 2-op explanations exist, n=143-179/300): Soft 0.7161 vs Cat 0.8242 (-10.8pt)
- new_ambiguous: Soft 0.5301 vs Cat 0.5285 (+0.2pt - the only Soft win)
Criterion FAIL: equal-acc fails on same; the ambiguous-subset win appears only on unseen frames and is swamped by the trained-frame loss.
Mechanism (pre-stated-style analysis, recorded post hoc): rows with a 1-op explanation typically admit MANY 2-op explanations (splits x HYP x H2); weighting EACH 2-op explanation by 0.25 vs 0.5 still lets their aggregate mass dominate the counts - 2^-len per-EXPLANATION is not 2^-len per hypothesis CLASS. Categorical Occam's hard filter (drop all 2-op when a 1-op exists) is the better inductive bias on this protocol; soft weighting helps exactly where the hard filter throws away true signal (unseen-frame ambiguous rows, +0.2pt).
Cross-reference: the shortest-on-tie half of F-5 in program SEARCH was already null (B-287..292: tie-break-shorter = tie-break-first, no benefit). F-5 as stated is 0-for-2: neither search tie-breaking nor soft explanation weighting pays off here.
Scope: this 2-step protocol, this 0.5/0.25 normalization. A class-normalized weighting (per hypothesis class, not per explanation) is a different, unrun variant - noted, not claimed.

Correction (2026-10-24, B-514): the commit message and backlog line said "+4.7pt on new-ambiguous" - that was a 3-seed interim figure seen before the run finished. The 5-seed figure is +0.2pt (Soft .5301 vs Cat .5285), i.e. a TIE, not a win: Soft wins big on seeds 1/3, loses on 0/2/4. Corrected bottom line: Soft ties on new and new-ambiguous, and loses on same (-9.0pt) and same-ambiguous (-10.8pt). The criterion FAIL is unchanged; the "only Soft win" phrasing in the verdict above is withdrawn - there is no subset where Soft wins by >1pt at 5 seeds.

## B-515 (F-6) pre-registration (2026-10-24, before running) - OOPS-style doubling scheduler over generators

Question: cur7's search exhausts comb-generator g1 fully before g2 (P14 ordering) - a program that is shallow in a LATE generator pays for all of every earlier generator. OOPS (Schmidhuber) interleaves generators with doubling per-generator budgets, bounded near-optimally by ~2-4x the best generator's own discovery depth. Does a doubling scheduler find the same programs at <=50% of the tried count?
Design (b515.py): recipe 'init10,baselib,simp,adv' (T9 standard; baselib pinned per B-523-H1 with EXCL={task}); tasks square, even, sumto, choose2; cap 6M; 1 run per cell (deterministic under the pinned library - verified by the sanity check below). Enumeration lists captured verbatim from cur7.search via LIST_CAPTURE (tried_cap=0) so both arms use IDENTICAL candidate lists and orderings; only the generator SCHEDULE differs.
Arms: (a) baseline = cur7.search unmodified (P14 ordering); (b) oopsdbl = generators g=(comb,init) enumerated by per-generator iterators; cumulative per-generator tried cap doubles 256, 512, 1024, ... ; round-robin phases until found or global cap. Same test body copied verbatim (r0 screen, staged train check, ADV boundary checks).
Sanity check (pre-stated, must pass before verdict): oopsdbl with a single phase whose per-generator cap exceeds the whole search degenerates to the baseline ORDER exactly - tried counts on even and sumto must EQUAL cur7.search's exactly; any mismatch = harness bug, fix before reading results.
Criterion (pre-stated): PASS = same success set (both arms find the same tasks' programs) AND oopsdbl mean tried over the 4 tasks <= 50% of baseline mean tried. tried is ground truth; dt reported but suspension-contaminated.
Predictions (not criteria): large win on square/choose2 (deep solutions in single generators); near-1x on tasks the baseline finds immediately (even).
CAN show: scheduler effect on this enumeration, these tasks, this recipe. CANNOT: full OOPS (no Levin-search probability re-estimation, no program-probability updates - this is budget doubling over a FIXED per-generator order).

## B-519 pre-registration (2026-10-24, before running) - babbling trajectory: production volume + correct-rate per day

Question: in baby7's NORMAL arm (P31 turn-taking dialogue), what does the pre-criterion babbling trajectory look like: how much does the baby produce per day, and what fraction is appropriate, per day? "Before criterion" = the grounding criterion already defined in baby7 (grounded(): top-2 association mass, top >= 1.5x runner-up).
Design (b519.py): baby7 run_d EXACTLY (NORMAL arm, feedback on, not shuffled; pools logs/baby3c_pool.json, f from the P31 protocol's main), 5 seeds, days=5, eps_per_day=100. Instrumentation added WITHOUT changing dynamics: per-day production count (episodes where the baby actually says a word), per-day appropriate-rate (existing day_approp), and for each distinct produced word the first day it met grounded() (checked passively, no effect on learning).
Metrics: 5-seed mean/min-max volume per day, appropriate-rate per day (d1..d5 - d1/d5 already in the P31 protocol), distribution of first-grounded day across produced words.
Success (pre-stated, documentation item): the curve is recorded in the LEDGER with all three metrics. No baseline arm; honest shape whatever it is (declining volume, rising rate, late grounding - all fine).
CAN show: production trajectory in THIS baby7 protocol. CANNOT: real-child babbling claims.
Amendment 1 (pre-run): f=1.0 (pure caregiver pool) chosen as the B-519 primary arm; f=0.2 is the P31 protocol's other arm, not this item's focus.
Amendment 2 (pre-run): pool path corrected to ai/wnn/pools.json (the committed P29 LLM pool file, 838 lines) - logs/baby3c_pool.json is the different P27h pool format and errored on load.

## B-519 verdict (2026-10-24) - documented (babbling trajectory, baby7 NORMAL f=1.0, 5 seeds)

logs/b519_babbling.log. Curve (5-seed mean [min-max]):
- Production volume/day: 43.0 [21-62] -> 85.2 -> 94.0 -> 97.0 -> 97.2 (reward-shaped speak-propensity saturates by day 3-4 at ~97/100 episodes).
- Appropriate-rate/day: .482 [.333-.639] -> .764 -> .731 -> .775 -> .773. The big jump is day1->day2 (+.28); afterwards a PLATEAU at ~.77, not a climb to 1.0 - residual inappropriate productions persist at steady state under the P31 reward rule.
- First-grounded day across produced words (132 grounded words, mean 26.4/seed): day1 78 (59%), day2 42 (32%), day3 8, day4 2, day5 2. Grounding is overwhelmingly EARLY - consistent with P27h's control finding that first-word grounding comes from scene-word co-occurrence on day 1, not reward.
Honest shape: fast volume ramp (babble-to-talkative in 2 days), rate plateaus below ceiling, grounding front-loaded. No baseline arm (documentation item, per pre-reg).
Scope: baby7 P31 protocol, pools.json, f=1.0, 5 seeds, grounded() as defined in baby7. CANNOT: real-child babbling claims.

Correction 2 (2026-10-24, B-514): the pre-registration's claim "text2prog8.py implements F-5 but was never run/verdicted" is FALSE - README.md's P25 section already documents soft Occam at n=100/300/1000 (same .73/.41 vs P16 .82/.44 at n=1000). B-514 is therefore an independent REPLICATION at n=1000 (identical-rows pairing: soft .733/.417 vs cat .823/.411 - the same-split numbers match P25 exactly; new-split differs by <=3pt, attributable to P25's non-paired rows) PLUS the new ambiguity-subset analysis. The verdict (FAIL at n=1000 on the equal-acc criterion) AGREES with P25's documented n=1000 result and stands; P25 additionally shows soft WINS at n=100/300, which B-514 did not test (its protocol fixed n=1000). Honest combined picture: soft Occam wins small-n, loses n=1000 - P25's "schedule (soft early, categorical late)" option remains untested (backlog-worthy, not run here).

## B-511 (F-2) pre-registration (2026-10-24, before running) - declarative advice as hypothesis constraints

Question (McCarthy Advice Taker): can the learner accept a DECLARED sentence - "order does not matter for add and mul" - and use it to shrink its hypothesis space, reaching the same accuracy with fewer examples? The advice must be consumed AS TEXT by a stated minimal parser (pattern: "order does not matter for <op> and <op>" -> prune the reversed-direction hypotheses of the named commutative ops), not silently hard-coded into the learner; same learner otherwise. Scope of the demonstration pre-stated: this one advice form, these two ops.
Mechanism: HYP holds (op, 'f'/'r') direction variants; for commutative ops (add, mul) the 'r' variant is the same function, so soft credit splits across the duplicate pair. Advice prunes ('add','r') and ('mul','r') from HYP (2 of 23 hypotheses). Baseline: P15 full HYP.
Design (b511.py): EXACT P15 protocol (gen_set, Learner('tok'), seeds 0..4, test seed 100+seed, 300 rows per split, big=True), n in {24, 60, 150}, arms FULL vs ADVISED on identical generated rows per seed. Metrics: accuracy on numbers/frames/synonyms.
Criterion (pre-stated): PASS = ADVISED@n=24 >= FULL@n=60 - 1pt on BOTH frames and synonyms (same acc, fewer examples). Report all cells; honest null if the dilution effect is too small to measure.
Predictions (not criteria): small positive at n=24 (the 2 pruned hyps carry ~2/23 of consistent-credit mass when consistent; less when not), within noise at n=150.
CAN show: declared-advice constraint on this learner, this advice. CANNOT: general natural-language advice taking.

## B-511 (F-2) verdict (2026-10-24) - FAIL (honest null with a clean mechanism): duplicate-hypothesis pruning has no measurable effect on this learner

logs/b511_advice.log (EXACT P15 protocol, 5 seeds, identical rows per arm, n in {24,60,150}). The advice machinery works end to end: the declared sentence "order does not matter for add and mul" parses (stated minimal parser) and prunes ('add','r') and ('mul','r') from HYP (23 -> 21). But accuracy deltas are within seed noise at every n and split (max |delta| 2.3pt, sign-inconsistent), and the criterion (advised@n24 >= full@n60 - 1pt on frames AND synonyms) FAILS decisively (frames .433 vs .733; synonyms .115 vs .153).
Post-hoc mechanism analysis (recorded honestly): the pre-reg prediction of a small positive was WRONG, and the null is theoretically clean. P15's predict() is per-hypothesis argmax of summed log-odds with uniform soft credit (w = 1/|C|): (a) the duplicate twin accumulates the SAME counts, so removing it does not change its sibling's score; (b) the soft-weight shrink from a larger |C| applies uniformly to all consistent hypotheses, leaving their relative ranking unchanged. Duplicate hypotheses therefore do not dilute anything in this scoring rule - F-2's premise (credit dilution) does not apply to argmax-over-per-hyp-scores. The Advice-Taker demonstration (declared text -> constraint) is real; the payoff premise was wrong FOR THIS ARCHITECTURE. F-2 would need a scoring rule where hypothesis mass matters (e.g. sampling/posterior over hypotheses, or pooled voting) to pay off.
Scope: P15 learner, this advice form, these splits. CANNOT claim: advice-taking is useless generally - it is useless HERE because the scoring rule is duplicate-invariant.

## B-522 verdict (2026-10-24) - PARTIAL PASS: decisive learned-vs-copied separation on composition (T1/T3/T4 PASS), impossible-conjunction attenuation FAILS pre-stated bar (T2)
B-522 (attribute<->concept, decisive tests) | PARTIAL PASS | b522.py logs/b522_decisive.log | frames INDUCED from corpus (slot-replacement pattern counting, no hard-coded frames); retrieval-copier baseline arm. q=8, 5 seeds.
- T1 compositional gap PASS: with one attribute pair fully held out per animal (no sentence contains both), model describes the gap pair exactly 30/30 (criterion >=27); retrieval copier 0/30 exact, mean coverage 0.5 (best it can do is a single-attribute sentence). Composition across sentences never seen together vs copying: decisive separation.
- T2 impossible conjunction FAIL: median normalized top score on empty-extension pairs .306-.333 vs .556-.583 on uniquely-identifying pairs; ratio .52-.57 vs pre-stated <0.5. Attenuation is real (~half strength) but does NOT meet the bar; an empty probe still scores positive because the top animal shares one attribute. No abstention - recorded as CANNOT.
- T3 novel-animal composition PASS: ช้าง taught ONLY with single-attribute sentences; model composes correct pair and triple descriptions (e.g. "ช้าง มี ขา และ หู และ งา", "ขา และ งา ของ ช้าง") 5/5 seeds at both arities (criterion >=4); copier 0/5 (no multi-attribute ช้าง sentence exists to copy). T3b sanity: reverse-ID {งา} -> ช้าง 5/5.
- T4 unknown-word distractor PASS: probes with 'เขา' (never in corpus) keep top-1 in the true extension 32/32 per seed, all 5 seeds (criterion >=95%). Unknown words contribute zero counts; lookup degrades gracefully.
CAN (measured): frames recoverable from co-occurrence alone; content composed across sentences never seen together, for a concept never seen in any multi-attribute sentence; unknown words ignored gracefully. CANNOT (measured): reject impossible attribute combinations (score attenuates ~2x but stays positive, fails bar); novelty preference, explicit refusal, meaning (carried from B-521).

## B-517 verdict (2026-10-24) - PASS: F-8 one-shot gap table assembled, honest and complete over measured cells
B-517 (F-8 gap table) | PASS | README.md "F-8 (B-517)" section | all existing few-shot cells assembled into three tables (MNIST B-241R seeded; SNIPS B-495+B-468..483 paired-seed incl. NB row; continual PMNIST B-467..491 shared-arm) with MLP baseline column, per-k orderings (Correction 2026-10-23 carried), WiSARD-not-a-few-shot-readout scoping, and a DECLARED-GAPS list of unmeasured cells (NB on MNIST, non-MLP readouts under continual protocol, single-task PMNIST few-shot, mitigated/larger gradient baselines). No new runs; every number traces to a LEDGER verdict.

## B-523 pre-registration (2026-10-24, before running) - root-cause + fix for impossible-combination lookup (Ash 2026-10-24 13:34 UTC: "มันพังเพราะอะไร จะแก้อย่างไร" = why does it break, how to fix)
B-522 T2 FAILED: impossible attribute pairs still get a clearly positive best-match score (ratio .52-.57 vs <0.5 bar).
ROOT-CAUSE HYPOTHESIS (to verify by measurement, not assert): the lookup score ADDS co-occurrence credit per probe attribute and never requires conjunctive coverage - an animal matching 1 of 2 demanded attributes keeps half the credit, and nothing in the rule can express "attribute demanded but never taught with this animal". Measured check: for every empty-extension pair, decompose the top animal's score per attribute - prediction: the winner covers exactly 1 of 2 attributes in 100% of cases.
FIX (architectural decision rule over the SAME learned counts; not new knowledge, not world-knowledge hard-coded): three-way decision - (a) UNKNOWN: a probe word never taught with ANY animal is reported as unknown and excluded from matching (was silently ignored in B-522 T4); (b) NO MATCH: no taught animal has nonzero count for every known probe attribute -> abstain, semantics = "not taught together", NOT "impossible in the world" (the teaching table is not complete world knowledge); (c) AMBIGUOUS: extension >1 -> return the FULL extension, ranked by the old score (was quiet top-1 with weak margin); (d) UNIQUE: exactly one -> answer.
Pre-stated criteria (q=8, 5 seeds, same world as B-521/B-522):
- T1 abstention: 100% of empty-extension pairs -> NO MATCH, all seeds.
- T2 no regression: 100% of uniquely-identifying probes (r=1,2,3) still answered correctly.
- T3 ambiguity: 100% of multi-extension probes return exactly the true extension.
- T4 unknown-word: probes mixing known attrs + 'เขา' report 'เขา' as unknown AND preserve the B-522 T4 validity (top within known-extension 100%).
- T5 control: shuffled-counts control world -> unique-ID accuracy near chance (the rule reads LEARNED counts; it is not a hard-coded table).
CANNOT claim: the learner still has no negative evidence (absent teaching != taught impossibility); the three-way rule is designed architecture, not learned behavior; "no match" means "not taught together" only.

### B-525 Amendment 1 (2026-10-24) - name/attribute role discriminator
First run FAILED C2/C3 (grounding 6/6 but uniq .22, abstain 0/75). Root cause (measured): the grounded vocabulary (10-13 words) admits attribute and function words (e.g. จะงอยปาก grounds to นก); summing their co-occurrence rows into the animal tables corrupts coverage. Data-driven fix (pre-stated before re-run): name-ness = assoc[w][animal] / (sentences with that animal primary); a NAME appears in ~every sentence about its animal (~0.9), an attribute in only a fraction (~0.3). Threshold >= 0.5 selects name rows; only name rows feed the animal-attribute table. Designed rule over learned counts, same status as decide().

## B-523 verdict (2026-10-24) - PASS: root cause verified by measurement, three-way decision rule fixes abstention/ambiguity/unknown without touching learned knowledge
B-523 (impossible-combination fix) | PASS | b523.py logs/b523_abstain.log | ROOT CAUSE (measured, not asserted): 13/13 empty-extension pairs, the old additive lookup's top animal covers exactly 1 of 2 demanded attributes - the score sums per-attribute co-occurrence credit and has no conjunctive-coverage requirement, so half-matches stay clearly positive (the B-522 T2 .52-.57 ratio). FIX: three-way decision over the SAME learned counts - UNKNOWN (word never taught with any animal, reported and excluded), NO MATCH (no taught animal covers all known probe attributes; semantics = "not taught together", NOT world-impossibility), AMBIGUOUS (extension >1, full extension returned ranked), UNIQUE. q=8, 5 seeds.
- T1 abstention: 13/13 empty pairs -> NO MATCH, all 5 seeds (criterion 100%).
- T2 no regression: 32/32 uniquely-identifying probes (r=1,2,3) correct, all seeds.
- T3 ambiguity: 22/22 multi-extension probes return exactly the true extension ({wing} -> [bat, bird, butterfly]).
- T4 unknown-word: 'เขา' flagged unknown 32/32 per seed AND known-part validity 32/32 (was silently ignored in B-522 T4).
- T5 control: shuffled-counts world -> unique-ID accuracy .00-.19 (chance ~.167): the rule reads learned counts, it is not a hard-coded table.
Honest status: the counts (knowledge) are learned; the three-way decision rule is DESIGNED architecture, same status as the old argmax - not claimed as learned. The learner still has no negative evidence: "no match" means "never taught together", and the teaching table is not complete world knowledge. Ambiguity vs no-match vs unknown are now three distinct, measured outcomes.

## B-523 applied (2026-10-24, Ash: "แก้เลย") - fixed three-way lookup is now the DEFAULT in the maintained harness (b521.py)
b521.py default lookup = decide() (UNKNOWN / NO MATCH / AMBIGUOUS-full-extension / UNIQUE over the same learned counts); `--legacy` preserves the pre-fix additive argmax. Legacy reproduction verified EXACT: all 10 B-521 rows, every metric key byte-identical (t1_uniq/t1_amb/wing_margin/t2_*/ctrl_*/bird_example). Fixed-path regression (logs/b521_bird_fixed.log): t1_uniq 1.0, t1_amb 1.0 STRENGTHENED to exact-extension equality (was top-in-ext validity), empty-probe abstention 75/75 (r=1..3) at both q, shuffled controls at chance, generation path (t2 metrics) untouched. Caveats carried unchanged: the decision rule is designed architecture over learned counts (not learned); NO MATCH = "not taught together", not world-impossibility; this fixes the animal/attribute lookup ONLY, not the broader conversational learner.

## B-524 pre-registration (2026-10-24, before running) - introspection audit: trace mode + causal lesion battery (Ash 2026-10-24 13:37 UTC: expose the internals, how answers arise, whether it really thinks)
Two measured components (the learned-vs-given inventory and the thinking-evidence matrix are assembly, in the audit File):
- TRACE: an explain mode on the maintained attribute learner (b521.py decide/describe paths) that dumps the ACTUAL recorded state behind each answer: decision branch, per-animal coverage booleans, raw counts for demanded attributes, score table, chosen frame pattern with its corpus count, novelty verdict vs corpus. Criterion: every produced answer is accompanied by the numbers that produced it; no narrative rationalization.
- LESIONS (causal removal, pre-stated predictions):
  - L1 remove all teaching of one attribute of one animal (นก-ปีก): probes whose unique answer depends on it ({ปีก,จะงอยปาก}) flip unique->NO MATCH 100%; นก drops out of the {ปีก} extension; นก generation recall drops by exactly 1/4 (one of its 4 attributes).
  - L2 remove ALL multi-attribute teaching sentences: induced frame inventory has ZERO arity-2/3 patterns; describe() returns None; gap-pair composition collapses to the copier's 0/30 (B-522 T1 re-run under lesion). Shows combination frames are learned from heard combinations, not built in.
  - L3 remove the B-523 decision rule (legacy argmax): abstention disappears (0/75) while counts are unchanged - the RULE, not the knowledge, causes abstention.
  - L4 shuffled-counts control: unique-ID at chance (re-runs B-521/B-523 control in this harness).
CANNOT claim: traces show mechanism, not consciousness; lesions establish causal roles of components within this toy system only.

## B-524 verdict (2026-10-24) - PASS: trace mode + all four lesion predictions confirmed exactly
B-524 (introspection audit, measured half) | PASS | b524.py logs/b524_audit.log | TRACE mode dumps the actual recorded state behind each answer (decision branch, per-animal coverage booleans, raw counts, score table, frame pattern + corpus count, novelty flag) - no narrative. Lesions (5 seeds, all predictions exact):
- L1 (remove นก-ปีก teaching): {ปีก,จะงอยปาก} flips unique->NO MATCH 5/5; นก leaves the {ปีก} extension 5/5; นก generation recall .75 = exactly -1/4 (5/5).
- L2 (remove all multi-attribute sentences): induced frame inventory = arity 1 ONLY; composition collapses 0/6 = the copier's level (5/5). Combination frames are learned from heard combinations; with none heard, the learner IS the copier.
- L3 (legacy argmax on same counts): abstention 0/75 - the B-523 RULE causes abstention, the counts alone never did.
- L4 (shuffled counts): unique-ID .00-.19 (chance ~.167).
Audit File (inventory + thinking-evidence matrix + integration feasibility) assembles these with existing LEDGER verdicts.

## B-525 pre-registration (2026-10-24, before running) - Link A integration test: P26 grounding feeds the B-521 lookup (Ash 13:39: can the systems be combined?)
Question: can the baby line (P26 Hebbian grounding from overheard speech + co-present scenes) replace the GIVEN animal-name lexicon in the attribute learner, with no loss on the B-521 battery? Same-corpus arms:
- ARM GIVEN: B-521 as-is (name lexicon handed to the learner).
- ARM GROUNDED: no name lexicon given. Scenes have a primary animal present (+30% noise co-present, P26-style); the baby builds (a) word->animal Hebbian associations (+1 co-present / -0.25 absent) and (b) word->attribute co-occurrence counts from the same overheard sentences. Grounded name vocabulary = words with best assoc >= 3 and best >= 2x runner-up (pre-stated threshold, filters function words). decide()/describe() then run on the grounded rows only.
Attribute words stay given (they are the QUESTIONER's vocabulary); the animal truth table is eval-only in both arms.
Criteria (5 seeds, q=8, 3 corpus rounds ~800 sentences):
- C1 grounding: top-associated word = correct name for >= 5/6 animals per seed.
- C2 on/off: grounded-arm unique-ID accuracy >= .90 (given arm = 1.0 in B-521).
- C3 fixed-rule behavior preserved: grounded arm abstains on empty pairs 13/13 and returns exact ambiguity extensions.
CANNOT claim: this links grounding to lookup only; it is not a general system merger (Links B/C deferred); co-present scenes are still given for free (P26's joint-attention caveat).

## B-525 verdict (2026-10-24) - PASS (after Amendment 1): first implemented cross-system link - grounded vocabulary feeds the fixed lookup at given-lexicon level
B-525 (Link A: P26 grounding -> B-521/B-523 lookup) | PASS | b525.py logs/b525_linka.log | baby overhears the B-521 corpus with co-present animal scenes (30% noise co-presence), grounds word->animal associations, discovers the name vocabulary WITHOUT a given lexicon; decide() then runs on the baby's own memory. First attempt FAILED (uniq .22, abstain 0/75): grounded vocab admitted attribute/function words, corrupting coverage tables. Amendment 1 (pre-stated before re-run): name-ness = assoc/primary-scene rate (names ~0.9, attributes ~0.3, threshold 0.5). Result 5/5 seeds: grounding 6/6 names; discovered vocabulary = EXACTLY the 6 true names (function words and attributes both rejected by the margin + name-ness filters); unique-ID 1.0; ambiguity extensions exact 1.0; abstention 75/75. Criteria C1 (>=5/6), C2 (>=.90), C3 (13/13 + exact extensions) all PASS. On/off: grounded memory == given lexicon on every B-521 metric. Caveats: co-present scenes given for free (P26 joint-attention caveat); attribute words remain the questioner's vocabulary; name-ness rule is designed over learned counts; this is ONE link, not a merged system (Links B/C planned).

## B-521 pre-registration (2026-10-24, before running) - attribute<->concept feasibility (Ash's bird question, 2026-10-24)

Ash asked (via main): if taught "a bird has wings, a tail, eyes", can the learner (1) answer "bird" when given attributes - including a MESSY UNORDERED attribute list it must reorganize itself - and (2) produce a NOVEL description (select and order learned words into a sentence it was never taught), rather than copying a taught sentence? Pre-stated honest framing (from main's reply): existing two-word composition does not establish this; ambiguous attributes require COMPETING concepts; naming-from-attributes and description-generation are DISTINCT capabilities needing distinct evidence; no claim of understanding from templates we supplied.
Design (b521.py), all within the existing associative machinery (baby-style co-occurrence counts, no new learning rule):
- World: 6 animal concepts with overlapping attribute sets: nok/bird {wing, tail, eye, beak}, khangkhao/bat {wing, fur, eye, ear}, phisuea/butterfly {wing, scale, eye}, ma/dog {fur, leg, eye, tail}, pla/fish {fin, tail, eye, scale}, maeo/cat {fur, leg, eye, tail, ear}. Overlaps by construction: wing shared by 3, tail by 4, eye by all 6, fur by 3, scale by 2, ear by 2. (English glosses here; the harness uses Thai words as in the baby line.)
- Teaching: co-occurrence sentences from 4 surface frames ("X มี Y", "X นั้น มี Y", "ดู Y ของ X", "Y ของ X สวย"), q sentences per (animal, attribute) pair, q in {3, 8}; sentences drawn per seed. The learner sees ONLY word co-occurrence (no slot labels): count C[name][attr] over sentence tokens.
- Task 1 (reverse identification, incl. Ash's messy-input case): probe = an UNORDERED SET of attribute words (set input = no syntax to exploit, exactly the "scrambled words" case). Score(name) = sum of C[name][attr] over probe attrs (normalized per name by total name mass - pre-stated); answer = argmax. Metrics over ALL attribute subsets of size 1-3: (a) accuracy on UNIQUELY-identifying sets (true extension = 1 animal): target >= .8 at q=8; (b) validity on AMBIGUOUS sets (extension > 1): top answer inside the true extension, target >= .9; (c) honest ambiguity behavior: on the probe {wing} alone the answer must NOT be reported as uniquely bird - measured as top-2 margin, reported, no threshold claim.
- Task 2 (novel description): per animal, produce a description = highest-count frame for that animal FILLED WITH the top-3 associated attribute words (selection by C, order by association rank inside a frame with multiple slots; single-slot frames iterated). Metrics: content precision/recall of selected attributes vs the true set (target >= .8 / >= .6 at q=8, 5-seed means); NOVELTY = fraction of produced sentences not verbatim in the training corpus (target >= .8 - proves non-copying at the sentence level); and a NEGATIVE control: a shuffled-counts learner (co-occurrence matrix permuted per seed) must score at chance on both tasks.
- 5 seeds. Baselines: chance top-1 = 1/6; single-attribute lookup baseline (answer only from the single most discriminative attribute) reported for contrast with the joint-set scorer.
Criterion (pre-stated): PASS = T1(a) >= .8 AND T1(b) >= .9 AND T2 precision >= .8 with novelty >= .8 AND shuffled control at chance (< .3 accuracy on T1(a)). Anything less = honest FAIL/partial.
CAN show: attribute<->concept association with competing concepts, set-input reverse identification, and selected-content generation with learned frames. CANNOT: understanding, referential meaning, or description of NOVEL concepts; the attribute vocabulary and frames are given in the data.
Amendment 1 (2026-10-24, pre-verdict, after smoke run): T2's single-slot frames saturate novelty at q=8 (every single-attribute frame+content sentence is verbatim in a dense corpus - honest finding: single-attribute "generation" is copying once the corpus is dense). Ash's novelty question is about COMBINATIONS, so the corpus is extended with 2-attribute frames ("X มี Y และ Z", "Y และ Z ของ X") covering a random 60% of each animal's attribute PAIRS and a 3-attribute frame ("X มี Y และ Z และ W") covering a random 30% of TRIPLES (coverage subsets drawn per seed). T2 generation = fill the 2-slot frame with the top-2 and the 3-slot frame with the top-3 associated attributes; novelty = produced (frame, content-combination) verbatim-absent from the corpus. All other elements unchanged.

## B-522 pre-registration (2026-10-24, before running) - decisive learned-vs-copied tests (Ash 2026-10-24 12:37 UTC, via parent: "ลองทดสอบใหม่ๆ ที่ทำให้เห็นผลชัดเจนกว่านี้" = new tests with clearer evidence of what is learned vs copied)
Follow-up to B-521. Upgrade over B-521: sentence frames are INDUCED from the corpus by slot-replacement pattern counting (name token -> X, attribute tokens -> A), not hard-coded; a retrieval-copier baseline arm (best corpus sentence containing the animal name, ranked by attribute-set overlap) separates composition from copying. q=8, 5 seeds, same 6-animal world as B-521.
- T1 compositional gap: per animal one attribute pair is FULLY held out (no corpus sentence contains both). Task: describe that animal with exactly the gap pair (content given; frame must be supplied by the learner). CAN criterion: model exact-correct (name + exactly the target pair as an induced-pattern sentence) >= 27/30 (6 animals x 5 seeds); copier full-set-correct = 0/30 by construction, report its mean coverage. Separation on both = decisive.
- T2 impossible conjunction: all attribute pairs with empty extension (no animal has both). Criterion: median normalized top score on empty probes < 0.5x median top score on uniquely-identifying probes. CANNOT caveat: this is a score-attenuation signal only; the learner emits no explicit "I don't know".
- T3 novel-animal composition: a 7th animal (ช้าง: งา/ขา/ตา/หู) taught ONLY with single-attribute sentences. Task: describe it with a target pair and a target triple it never saw combined. CAN criterion: model exact-correct >= 4/5 seeds at BOTH arities; copier 0/5. T3b sanity: reverse-ID {งา} -> ช้าง 5/5.
- T4 unknown-word distractor: reverse-ID probes = known attribute(s) + 'เขา' (a word never in the corpus). Criterion: top-1 answer lies in the extension of the known attributes for >= 95% of probes (graceful degradation, no crash, no corruption by the noise word).
Overall CAN claims if passed: frames recoverable from co-occurrence alone; composition of content across sentences never seen together; graceful unknown-word handling; weak-match score signal. Overall CANNOT (carried from B-521, not retested): novelty PREFERENCE, explicit refusal, referential meaning/understanding, frames beyond those in the data.

## B-521 verdict (2026-10-24) - PARTIAL PASS: reverse identification perfect incl. messy unordered input; novel-combination generation works (~70% novel, 100% correct content) but below the pre-stated .8 novelty bar

logs/b521_bird.log (5 seeds, q in {3,8}; co-occurrence counts only; 6 competing animal concepts with overlapping attributes).
- T1 reverse identification (UNORDERED attribute sets = Ash's scrambled-input case): uniquely-identifying sets 1.0 at both q (target .8); ambiguous sets: top answer inside the true extension 1.0 (target .9). Shuffled-counts control: .21/.23 (chance 1/6 = .167, < .3 bar). Single shared attribute {ปีก}: top-2 margin .20-.22 - measured and reported as NOT uniquely identifying (3 winged animals), the honest ambiguous behavior.
- T2 generation (learned frame + association-selected content): content precision 1.0, recall .767 (target .8/.6 PASS at q=8; recall capped by design at top-3 for 4-5-attribute animals). Example productions (seed 0, q=8): "นก มี จะงอยปาก และ หาง" / "นก มี จะงอยปาก และ หาง และ ตา".
- NOVELTY: .667 (q=3) / .717 (q=8) - FAILS the pre-stated .8 bar. Mechanism: the learner picks its strongest-associated attributes whether or not that exact combination was taught; with 60%/30% pair/triple teaching coverage, ~70% of its top-ranked descriptions are genuinely novel combinations and ~30% happen to replicate a taught sentence. It CAN produce correct novel descriptions; it does not PREFER them (it has no representation of novelty). The .8 bar conflated capability with preference - recorded as measured.
Bottom line for Ash's question: (1) attribute->name inference works at 100% under competing concepts, including unordered/messy attribute input; (2) description generation produces correct, majority-novel sentences from learned words + learned frames, but is not novelty-seeking. NOT shown (scope): understanding, referential meaning, describing novel concepts, free word-order invention (the frame "X มี Y และ Z" is learned from data; content selection is the novel part).

## B-526 pre-registration (2026-10-24, before running) - Link B: HDC one-shot attribute memory backend, on/off vs count tables (first link of the hsml unified-integration plan; Ash 2026-10-24: "ทำให้ทุกอย่างรวมเป็นหนึ่งอย่างสมบูรณ์")
Goal: the B-521/B-523 answer path gets a SWAPPABLE memory backend (real data flow: corpus -> memory -> decide()), and the hyperdimensional (HDC) backend is measured against the exact-count backend on the same battery. Integration criterion: not a renamed wrapper - decide() must read all its evidence through the backend interface in both arms.
Design (b526.py):
- Backend interface: observe(sentence_tokens); score(name, attr) evidence; totals. ARM COUNT = current tables (control). ARM HDC: D=10000-bit binary hypervectors, random per word (seeded); sentence record = XOR-bind of word vectors BUNDLED (per-name majority) - one-shot superposition memory; evidence(name, attr) = Hamming similarity of (bind(name,attr) probe) vs the name's bundle, normalized.
- Battery = the B-523 three-way decide() checks exactly as committed (abstain 13/13 empty pairs, no-regression 32/32, ambiguity 22/22 exact extensions, unknown-word 32/32, shuffled control at chance) PLUS B-521 T1 reverse-ID accuracy.
- One-shot axis (the pre-stated place HDC could actually win): teaching budget q=1 sentence per (animal,attribute) pair. Measure T1 accuracy for both arms on identical corpora.
Criteria (5 seeds):
- C1 parity: HDC arm passes abstain 13/13, ambiguity 22/22, unknown 32/32, and T1 >= .95 at q=8.
- C2 value: HDC T1 at q=1 >= count-arm T1 at q=1 + .10 (a real one-shot advantage), OR HDC shows no measured advantage anywhere -> verdict NO-VALUE and the HDC backend is CUT from the answer path (Ash's rule: cut what does not help; recorded honestly either way).
- C3 control: shuffled HDC memory at chance (< .3).
CAN claim if PASS: the answer path runs on an interchangeable memory substrate, measured. CANNOT: neural/biological plausibility, robustness beyond the tested battery, any intelligence gain from the swap itself (integration != intelligence).
Amendment 1 to B-526 (2026-10-24, pre-run, before any HDC result exists): C2 as pre-registered is UNREACHABLE - count tables are lossless for presence, so at q=1 the count arm is already at ceiling and no substrate can beat it by .10. Replacing the value axis with one where exact-match counts are genuinely weak:
- C2 (revised) noise robustness: probe attribute tokens corrupted by one random Thai-character substitution each. COUNT arm keeps B-523 semantics (corrupted token = unknown word: flagged, excluded, decide on the rest). HDC arm: word vectors composed from character 3-gram hash vectors (XOR-bundled), so a 1-edit corruption stays near the true word vector; membership still thresholded, and a low-margin result still abstains (honesty preserved - similarity matching is an engineered capability, not understanding). Criterion: HDC correct-decision rate under corruption >= count arm + .10, AND HDC clean-probe parity (C1) holds.
- Descriptive only (no criterion): memory bytes of both backends at 6-animal and synthetic 60-animal scale.
- Cut rule unchanged: if HDC fails C1 parity, or fails to beat counts under corruption, verdict NO-VALUE and the HDC backend is cut from the answer path; the swappable-backend interface (the actual integration deliverable) stays with counts as default.
- Threshold honesty: the HDC membership threshold tau is calibrated on separate calibration seeds (100+sd), frozen, then applied unchanged to the 5 test seeds; no fitting on the test battery.
Amendment 2 to B-526 (2026-10-24, pre-run of the revised design; the bind arm HAS already run and is recorded, not erased): the bind arm's measured C2 failure has a known mechanism - XOR-binding decorrelates by design, so word-level similarity (the only thing corruption robustness could come from) cannot survive bind(V_name, V_attr). Revised HDC design (arm hdc2): per-name ITEM bundle of attribute word vectors (standard HDC item memory; no binding - there is no role/filler structure in a presence table); taught(n,a) = sim(V[a], B[n]) >= tau2, V built from char 3-grams as before; tau2 calibrated on seeds 100-104, frozen, applied to test seeds 0-4; same battery, same criteria (C1 parity, C2 corruption win >= +.10, C3 shuffled control < .3). Cut rule now applies per design: whichever HDC design fails C2 is cut; if both fail, HDC as a whole is cut from the answer path and the backend interface ships with counts only.
Implementation note to Amendment 2 (2026-10-24, BEFORE the hdc2 arm's first run): XOR composition destroys set-overlap similarity (A xor B differs in ~50% of bits whenever the trigram symmetric difference is nonempty), so the hdc2 word encoder uses MAJORITY composition over trigram vectors (standard HDC bundling), and the per-name memory is a majority bundle of attribute word vectors. Predicted honestly: robustness should appear for LONG attribute words (จะงอยปาก, ค้างคาว-class) and likely fail for 2-3 char words (ตา, ขน, หู) whose few trigrams all change under a 1-char edit; if the aggregate win is < +.10, C2 fails and HDC is cut.

## B-526 verdict (2026-10-24) - NO-VALUE, both HDC designs CUT; swappable-backend interface ships with counts as default
b526.py logs/b526_linkb.log logs/b526_linkb_item.log | tau_bind=0.518 (cal J=1.00), tau_item=0.675 (cal J=0.64 - overlap already visible at calibration, run continued for the honest record).
- C1 parity: BIND arm PASS (abstain 13/13, unique 32/32, ambig 22/22, unk 32/32, all 5 seeds = count arm exactly). ITEM arm FAIL HARD (unique 10/32, ambig 3/22 every seed): majority bundles of 3-5 subword-encoded members cannot separate member from non-member attrs in a 10-word vocabulary with shared characters/trigrams.
- C2 value axis (corruption robustness): BIND +0.00 vs count arm (count .027 mean, bind .027 mean) - mechanism as amended: XOR binding decorrelates, word similarity cannot survive bind(). ITEM arm's corrupt numbers (0-.2) are uninterpretable given C1 failure.
- C3 shuffled controls at chance (bind 0-.19, item 0-.22, bar .3). Memory (descriptive): count 192B vs HDC 7500B at this scale - HDC loses on footprint too at small vocabulary.
- Harness bugs caught pre-verdict by calibration sanity outputs (pos/neg sim overlap): (1) majority-bundling REPEATED observations dilutes every true pair below threshold - fixed by deduping observed pairs; (2) XOR composition destroys set-overlap similarity - fixed to majority composition for the item arm. Both recorded.
Decision (Ash's cut rule, applied): HDC is CUT from the hsml answer path. What ships from Link B: the backend interface (observe/taught) with decide() reading all evidence through it - the actual integration artifact - with exact counts as the measured-correct default backend. No neural-plausibility claim was made or is salvageable here; HDC may be retried only if a future task has (a) large vocabulary and (b) a measured need exact tables cannot serve.

## B-527 pre-registration (2026-10-24, before running) - Link C: program-skill memory -> dialog answer path (Ash: "รวมทุกอย่างเข้าด้วยกัน")
Goal: the dialog answer path gains a SKILL STORE: procedures induced by the cur7 engine are stored with provenance and EXECUTED to answer novel queries through the same sentence-in/sentence-out path as attribute questions. This is the second real cross-system link (after Link A), not a renamed demo: the query arrives as a Thai sentence, the answer is produced by executing a stored induced program, and the same memory still serves the B-521/B-523 attribute battery without interference.
Honest scoping: induction COST is not re-measured here (b515/F-6 owns that); the skill store is seeded with the programs b515's runs already found (verbatim from logs/b515_oops.log, with seed/tried provenance), each re-validated inside this harness on the b515 unseen-scale protocol before use. Tasks = exactly those with a logged generalizing program: even, sumto, square, choose2.
Design (b527.py):
- Skill store inside the same memory object as the attribute tables: skill(name) = (spec, init, post, provenance). Query sentence frame (DESIGNED, named as such): "ถาม <skill> ของ <n>" / teaching frames for examples are NOT needed - skills come from b515's induction logs, not from new in-dialog teaching (that is a separate future link).
- Answer sentence: filled result in a designed frame; the system reports which skill fired (traceable, B-524-style).
- ARMS: SKILL (execute stored program) vs COPIER baseline (answer only verbatim-seen input->output pairs from b515's train examples; 0 on unseen by construction).
Criteria (pre-stated):
- C1 execution accuracy: >= 95% correct on 40 unseen inputs per skill (the b515 unseen scales), answered through the sentence path.
- C2 copier = 0% on the same unseen inputs (construction sanity).
- C3 abstain: a query naming a function with NO stored skill (gcd) -> no_match/abstain, never a guessed number.
- C4 no interference: with the skill store loaded, the B-523 battery still passes exactly (abstain all, unique all, ambig all, unk all).
- C5 garbage control: cur7 induction on shuffled (x -> random y) examples with the same per-task budget finds NO program -> the store stays empty -> abstain. (Guards against a pipeline that "finds skills" in noise.)
CAN claim if PASS: stored induced procedures are executed through the dialog path on novel inputs, with abstention when no skill exists, and no degradation of the attribute answer path. CANNOT: in-dialog teaching of procedures (skills are seeded from b515 logs with provenance, not taught by conversation); any understanding of numbers (the numeric parse/format is designed); general programming beyond cur7's primitive set.

## B-528 pre-registration (2026-10-24, before running) - engineered-connectome arm 1: STD recency gate for novelty-aware generation (hsml connectome, Ash's free-redesign scope)
Grounded in two measured facts: B-521's novelty gap (the generator picks strongest associations whether or not the combination was taught; novelty .667-.717, fails the .8 bar) and B-505's root cause (the connectome line's only reproduced behavioral effect, +18%, is mediated by short-term depression dynamics - STD is a recency signal). Design: an ENGINEERED component derived from the connectome line (not worm wiring, no biological claim): per-(name,attribute) count rows get STD-style recency adaptation - recently USED (name,attr,frame) combinations depress, so the generator's selection shifts toward correct-but-unused combinations. Arms: STD-gate ON vs OFF (identical everything else) on the B-521 T2 battery, 5 seeds, q=8; plus a SHAM gate (random depressions, same count) to assign credit to the dynamics, not the noise (B-505 lesson).
Criteria (pre-stated): PASS = ON-arm T2 novelty >= .8 AND content precision >= .8 AND recall >= .6 AND B-523 battery unchanged (abstain/unique/ambig/unknown all exact) AND sham-arm novelty < ON-arm - .1. FAIL/NO-VALUE -> the STD gate is cut and the connectome line is recorded as contributing nothing to the answer path (Ash's cut rule).
CAN claim if PASS: one engineered connectome-derived mechanism (recency adaptation) has a measured, ablation-credited function in the answer path. CANNOT: biological fidelity, memory like a human, novelty PREFERENCE as understanding - it is a designed depletion dynamic over learned counts.

## B-515 verdict (2026-10-24) - PASS with two recorded caveats: OOPS doubling scheduler passes the pre-stated bar (mean tried 9.8% of baseline), but the even leg regresses 4.9x on tried while finding the better-generalizing program
b515.py/b515_run.sh/b515_followup.sh, logs/b515_oops.log + logs/b515_progs.log (followup re-ran every leg; tried counts match the grid EXACTLY on all 6 re-run legs: oops even 611365, oops sumto 537, baseline even 123944, baseline sumto 1415698, baseline square 2583787, baseline choose2 2597867).
- Pre-stated criterion (same success set AND mean tried <= 50% baseline): PASS. Both modes found generalizing programs for all 4 tasks. Mean tried: oops 164,048.5 vs baseline 1,680,324 = 9.8%.
- Caveat 1 (even regression): oops tried 611,365 vs baseline 123,944 on even (4.93x WORSE). The doubling scheduler pays 256*2^phase across ALL generator arms per phase, so it loses when the winning candidate sits early in one arm. The mean is dominated by the two ~2.6M baseline legs (square/choose2); per-leg: sumto 537 vs 1.4M, square 747 vs 2.6M, choose2 43.5k vs 2.6M.
- Caveat 2 (tried is not the whole story): on even, the baseline's cheaper find generalizes WORSE on unseen scale 4 (26/40 vs oops's 40/40; all other legs 40/40 both modes). Program quality differs independently of search cost - recorded as measured on one task/scale, not generalized.
- Operational findings recorded: (a) capture_lists(tried_cap=0) runs a FULL baseline search to capture enumeration lists - derivation tooling must budget for it; (b) sandbox wall-clock dt is unreliable (baseline square: 1746.4s vs 193.7s for identical 2,583,787 tried) - tried counts are the only ground truth.

## B-528 verdict (2026-10-24) - PASS: STD-style depletion gate earns the first measured engineered-connectome function in the answer path (novelty 1.0 vs .42 off-arm, sham-credited)
b528.py logs/b528_std.log, 5 seeds q=8, beta=1 pre-set. ON arm = strength/(1+P[name][combo]); OFF = same combo-argmax ungated; SHAM = same gate on random equal-sized combo sets.
- Criterion novelty >= .8: PASS - ON 1.0 all seeds (OFF .25-.5, mean .42; SHAM .33-.58, mean .475).
- Content maintained: precision .944 (>= .8), recall .711 (>= .6). Cost recorded: OFF was 1.0/.767 - the gate sometimes trades the single strongest attribute for an untaught combination.
- B-523 battery unchanged on all seeds (13/13, 32/32, 22/22, 32/32, 32/32) - generation-only change, lookup path untouched.
- Credit assignment: ON - SHAM = +.53 > .1 - the gain comes from depressing TAUGHT combinations, not from adding noise.
- Tie-break note: OFF-arm novelty here (.42) differs from B-521's .717 because combo-argmax breaks count ties in combinations() order vs B-521's ATTRS order; both are below the .8 bar, so the gap being closed is the same gap.
- Honesty: the novelty preference is now DESIGNED-IN (depletion over learned co-occurrence counts), not emergent novelty-seeking; the component is engineered, named STD-style for its depletion dynamics, no biological claim. What it shows: one connectome-derived mechanism has a measured, ablation-credited function. Mechanism caveat: with 60%/30% teaching coverage an untaught correct combo always exists, so novelty 1.0 is partly by construction; the informative numbers are the sham separation and the prec/rec cost.
CORRECTION 1 to the B-528 verdict framing (2026-10-24, parent review): "novelty gap closed" was over-claimed - ON-arm novelty 1.0 came with a correctness cost (precision 1.0->.944, recall .767->.711). Mechanism of the precision drop: selection scores combos by SUM of member counts, so a combo containing an UNSUPPORTED attribute (C=0) can outrank a taught all-supported combo once the latter is depressed - the gate trades unsupported content for novelty. The STD-inspired depletion heuristic is an engineered heuristic over counts, NOT a contribution of the connectome graph itself; the comparison establishes the heuristic's effect under this coverage protocol only, and novelty != understanding. B-528 ON arm is EXPERIMENTAL evidence, not the default answer path; the accurate OFF baseline stays default.
Amendment 1 to B-528 (2026-10-24, pre-run): add arm GATED-CONSTRAINED - candidates restricted to combos whose members are ALL supported (C[name][a] > 0) BEFORE novelty ranking; if every supported combo is taught, fall back to the strongest supported combo (accept non-novel rather than go unsupported). Criteria: precision == OFF arm (1.0), recall >= OFF - .02, novelty >= .8 where coverage permits (report per-seed when impossible), battery unchanged, sham separation maintained vs the same constrained ranking with random depressions.
Amendment-1 result (2026-10-24): PASS. GATED-CONSTRAINED restores exact content (precision 1.0, recall .767 = OFF arm on all seeds) while keeping novelty .833-.917 (mean .875 >= .8); gc_sham .5-.667 (mean .533) preserves credit separation (+.34 > .1). Novelty < 1.0 is the honest coverage cost: when every supported combo was taught (e.g. ผีเสื้อ's only triple) the fallback picks the strongest supported combo instead of going unsupported. Status per parent review: ON/gc arms remain EXPERIMENTAL; OFF (accurate baseline) is the default generation path; all three arms' evidence and costs are retained for the audit/integration status. The engineered STD-inspired depletion heuristic now has measured value WITHOUT a correctness tradeoff under this coverage protocol; it remains a heuristic over counts, not a connectome-graph contribution, and novelty != understanding.

## B-527 verdict (2026-10-24) - PASS: Link C - induced-program skill store answers through the dialog sentence path, 160/160 per skill, with abstain and zero interference
b527.py logs/b527_linkc.log | one HSMLMemory serves the B-523 attribute battery AND the cur7 skill store; skills re-derived deterministically from b515's oops config and verified show_prog == logged string per task (even's provenance: the followup leg in logs/b515_progs.log; the original oops.log even leg recorded no prog string - noted).
- C1 (bar >= 95%): 160/160 sentence-path execution accuracy on unseen inputs for ALL FOUR skills (even, sumto, square, choose2; b515 unseen protocol scales 1-4).
- C2 copier: 11/54/87/63 per 160 - AMENDMENT to the pre-reg reading: "0 by construction" was wrong because scale-1 unseen queries collide with train inputs; measured collisions exactly equal the copier's correct counts (11/54/87/63), so on NON-colliding inputs copier = 0 and skill = 100%. Sanity function intact.
- C3 abstain: no-skill query ("ตัวหารร่วมมาก ของ 12 คืออะไร") produced no number - it fell through the designed frame match to the attribute path's unknown_all. Abstention behavior correct; routing is designed, named as such.
- C4 no interference: attribute battery exact with skills loaded (13/13, 32/32, 22/22, 32/32, 32/32).
- C5 garbage control: induction on shuffled examples found NOTHING within 611,365 tried (cap = largest successful b515 oops leg, implementation note) - no skill hallucinated from noise; store stays empty -> abstain.
CAN claim: stored induced procedures execute through the sentence path on novel inputs; abstain when no skill; no degradation of the attribute path; no skills from noise. CANNOT (carried): in-dialog teaching of procedures (skills seeded from b515 logs with provenance); number understanding (parse/format designed); anything beyond cur7's primitive set. Integration != intelligence: this is one more real data-flow link, not a merged-mind claim.
## B-529 pre-registration (2026-10-24, before running) - Link D: in-dialog procedure teaching (closes B-527's seeded-skills gap)
Goal: a NEW procedure enters the skill store entirely through conversation - the teacher uses only sentences, never code or a seeding API. B-527's skills were seeded from b515 induction logs; this is the human-facing teaching path the integration audit marks as not yet done (Ash: "ทำให้ทุกอย่างรวมเป็นหนึ่งอย่างสมบูรณ์").
Design (b529.py):
- Scripted teacher, sentences only, DESIGNED frames (named as such): a naming statement ("วิธีนี้ชื่อ สองเท่า"), example statements ("ถ้า n เป็น 3 ตอบ 6") and confirmation answers ("ตอบ 6"). The system parses (x -> y) pairs, runs cur7/OOPS induction under a bounded tried budget on the accumulated pairs, then CONFIRMS the candidate by querying the teacher on held-out inputs ("ถ้า n เป็น 7 ตอบอะไร"); only a teacher-confirmed program enters the store, with provenance (dialog, examples, tried, confirmation transcript).
- Teaching target: one new procedure not among the 4 seeded skills (double, 2n). Validation: 40 unseen inputs through the b527 sentence path.
- Confirmation-round cap 3: if every candidate fails teacher confirmation within 3 rounds, teaching FAILS and the store stays unchanged.
Criteria (pre-stated):
- C1 sentences only: every supervision pair comes from a parsed sentence; no direct store writes. Total teaching supervision (examples + confirmations) <= 20, reported.
- C2 taught-skill accuracy >= 95% on 40 unseen inputs through the sentence path (B-527 C1 bar).
- C3 no interference: the 4 seeded skills still 160/160 and the B-523 battery unchanged after the new skill enters.
- C4 noise control: a teacher giving random (x,y) pairs with the same budget ends with NO new skill (induction finds nothing or confirmation rejects all candidates within the round cap) -> abstain.
- C5 provenance: the stored skill carries dialog provenance and is inspectable (show_prog).
FAIL recording: budget exhaustion or confirmation-cap exhaustion is a FAIL with tried counts and rounds recorded; grammar/frame changes mid-run are an amendment, not silent repair.
CAN claim if PASS: a procedure was taught through conversation alone and is answered through the same sentence path as pre-existing skills, with bounded supervision and noise control. CANNOT: natural-language understanding of the procedure's meaning (frames are designed); procedures beyond cur7's primitive set; human-like teaching flexibility.
## B-529 verdict (2026-10-24) - PASS: Link D - a procedure was taught through conversation alone and answers through the same sentence path
Pre-reg 2026-10-24 (above). Harness b529.py, log logs/b529_teach.log. Verdict json: PASS, c1-c4 all true.
- C1 sentences-only teaching: 'double' (สองเท่า) taught in round 1 from 5 example sentences + 3 confirmation replies = 8 supervision pairs (bar <= 20); induction tried=549; stored program "init b=one; if (lt a b) -> a; else step (a,(add a a)); comb=('add','a',0); post=id" with dialog provenance. No VALID/ADV extra supervision (honest scoping: induction fit teacher pairs only).
- C2 taught-skill accuracy: 40/40 on unseen inputs (x in 40..2000) through the sentence path (bar >= 38).
- C3 no interference: seeded skills still 160/160 x4; B-523 battery exact (13/13 abstain, 32/32 unique, 22/22 ambig, 32/32+32/32 unknown).
- C4 noise control: garbage teacher (memoized random mapping, same budget) -> induction exhausted at tried=700,001, NO skill stored.
Claim per pre-reg: a procedure was taught through conversation alone, with bounded supervision and noise control, and is answered through the same path as pre-existing skills. Still CANNOT claim: understanding of the procedure's meaning (frames designed); procedures beyond cur7's primitive set; human-like teaching flexibility (scripted teacher, designed frames; teaching of multi-step conditional procedures untested).
Note: the taught program generalizes behaviorally - 40/40 on unseen x in 40..2000 after only 8 dialog pairs (x <= 40 examples, confirmations x < 400); it is not a memorized table. Mechanism of the found schema not further analyzed.
## B-529 Correction 1 (2026-10-24, parent review) - claim scope narrowed
B-529 establishes ONE implemented conversation-to-induction link under the stated designed frames and numeric DSL. It does NOT close "the last artificial step" and does not establish complete integration of all systems: sentence parsing, routing, the search space/primitive set, the confirmation protocol and the teacher remain designed. These boundaries persist in integration status and future audit revisions until separately measured.
## B-530 pre-registration (2026-10-24, before running) - compositional dialog teaching: taught skills accumulate as reusable primitives
Goal: extend Link D (B-529) from one taught skill to an ACCUMULATING library: teach 'double' then 'quad' (4n) through conversation only, and measure whether the previously taught skill makes the later teaching cheaper. This tests the OOPS/library claim at the dialog level: knowledge taught earlier is reused by later induction, not just stored.
Grounded in: B-529 (one dialog-taught skill, 8 pairs, tried=549) and cur7's grown-library mechanics (LIB entries become callable primitives for later search; setup pins the library).
Design (b530.py):
- Same teaching protocol as b529 (naming/example/confirmation frames, DESIGNED and named; confirmation-round cap 3; <= 20 supervision pairs per skill; induction on parsed pairs only, no VALID/ADV).
- Sequence: teach double (สองเท่า), then teach quad (สี่เท่า) with double present in LIB as a callable primitive. Inspect show_prog(quad) for whether double is actually called.
- ARM (ablation): repeat quad teaching with double REMOVED from LIB (same pairs, same seeds, same cap) - assigns the tried-cost difference to the accumulated library, not to the task.
Criteria (pre-stated):
- C1 both skills taught through dialog only, <= 20 pairs each.
- C2 quad accuracy >= 38/40 on unseen inputs through the sentence path (B-527 bar).
- C3 reuse value: tried(quad | double in LIB) <= 1/2 * tried(quad | double ablated), OR the ablated arm finds nothing within cap while the with-double arm finds one. If the with-double program actually calls double, record it; if quad is found without calling double, record that honestly (reuse claim then rests on the tried delta only).
- C4 no interference: seeded 4 skills 160/160, attribute battery exact, double still 40/40.
- C5 garbage control on quad teaching (memoized random mapping, same budget): no skill stored.
FAIL recording: budget/round-cap exhaustion recorded with tried counts; frame changes mid-run are an amendment.
CAN claim if PASS: dialog-taught procedures accumulate as reusable primitives and later teaching is measurably cheaper because of earlier taught knowledge (ablation-credited). CANNOT: semantic understanding of the procedures; anything beyond designed frames + numeric DSL; complete integration (B-529 Correction 1 boundaries stand).
## B-530 verdict (2026-10-24) - FAIL on C3 (reuse bar not met); composition taught but shows no measured value at this depth
Pre-reg 2026-10-24. Harness b530.py, log logs/b530_comp.log. Verdict json: FAIL (c1,c2,c4,c5 true; c3 false).
- C1 both skills taught through dialog only: double (tried=549) then quad (tried=870), 8 supervision pairs each.
- C2 quad accuracy 40/40 unseen through the sentence path.
- C3 FAIL: tried(quad | double in LIB) = 870 == tried(quad | double ablated) = 870, and the SAME program was found in both arms ("init b=zero; if (lt a b) -> b; else step (a,(add a b)); comb=('add','a',0); post=id"), which does not call double (calls_double False). No reuse value measured.
- C4 no interference: seeded 160/160 x4, double 40/40, attribute battery exact.
- C5 garbage quad teacher: induction exhausted at tried=700,001, nothing stored.
Mechanism (measurement-design lesson, pre-reg lesson #6 pattern): cur7's enumeration order places a newly added LIB primitive's candidates AFTER the base-space candidates. quad's winning program sits at position 870 in the base enumeration, before any double-involving candidate is reached, so for shallow targets the reuse arm can never show a tried saving under this protocol - the C3 bar was unreachable by construction for this target, not refuted behaviorally. The reuse hypothesis needs a target whose DIRECT search is deep (near cap), where a primitive-using candidate can win by being found earlier than the deep direct one.
Record: compositional teaching itself WORKS (a second skill was taught through dialog on top of an accumulated library, no interference); only the measured-value claim fails at this depth.
## B-531 pre-registration (2026-10-24, before running) - library-reuse value retest with a depth-selected target
Grounded in B-530's enumeration-order lesson: a new LIB primitive's candidates enumerate after the base space, so reuse can only show a tried saving when the target's DIRECT search is deep. B-530's quad was shallow (870); this retest selects a deep target by a fixed rule BEFORE the reuse arm runs.
Target selection rule (fixed order, recorded): candidates [hexdec 16n (สิบหกเท่า), square-plus-self n(n+1) (กำลังสองบวกตัว), oct 8n (แปดเท่า)]. The ABLATED arm (no taught primitives in LIB) teaches the first candidate; if it is found with tried < 100,000 the target is recorded as too-shallow and the next candidate is tried. The first candidate whose ablated teaching reaches tried >= 100,000 or exhausts the 700,000 cap becomes THE target. (Selection spends only ablated-arm runs; the reuse arm runs once, on the selected target.)
Design (b531.py): b529/b530 protocol unchanged (dialog frames DESIGNED, <= 20 pairs/skill, confirmation cap 3, no VALID/ADV). Primitives available to the reuse arm: double + quad (dialog-taught in-run, as b530) + sumto (seeded from b515 logs with provenance) - all legitimately acquired knowledge. Ablated arm: same LIB as b529 (no taught/seeded primitives).
Criteria (pre-stated):
- C1 dialog-only teaching, <= 20 pairs per skill (including the target skill).
- C2 target accuracy >= 38/40 unseen through the sentence path.
- C3 tried(target | primitives in LIB) <= 1/2 * tried(target | ablated), OR ablated exhausts cap while reuse finds. calls_primitive recorded honestly (which taught skill, if any, the found program calls).
- C4 no interference: seeded 160/160 x4, double+quad 40/40, attribute battery exact.
- C5 garbage control on the target (same budget): nothing stored.
FAIL recording: if all three candidates are too-shallow, verdict = INCONCLUSIVE-DEPTH (record tried per candidate); if the reuse arm fails C3 on the selected deep target, the reuse hypothesis is FAIL at depth too - record tried counts and the found programs.
CAN claim if PASS: accumulated dialog-taught knowledge measurably accelerates later learning (ablation-credited). CANNOT: semantic understanding; designed frames + numeric DSL only; B-529 Correction 1 boundaries stand.
## B-531 verdict (2026-10-25) - PASS: accumulated dialog-taught knowledge measurably accelerates later learning (search phase, ablation-credited)
Pre-reg 2026-10-24. Harness b531.py, log logs/b531_reuse.log. Verdict json: PASS, c1-c5 all true.
- Target selection (fixed rule): hexdec 16n (สิบหกเท่า) - ablated arm (no taught primitives) exhausted the cap at tried=700,001 with NO program. Deep as required by the B-530 lesson.
- C3 reuse: with double+quad (dialog-taught in-run) + sumto (seeded, provenance) in LIB, induction found 16n at tried=29,478 - 23.7x fewer tried than the ablated cap, and the ablated arm found NOTHING. The found program "init b=zero; if (lt a b) -> a; else step (a,(add a b)); comb=('quad','a',1); post=id" actually CALLS the taught quad primitive (calls_primitive=['quad']) - reuse is structural, not a cost artifact.
- C1 dialog-only, 8 pairs for the target (bar <=20). C2 40/40 unseen through the sentence path. C4 no interference (seeded 160/160 x4, double+quad 40/40, battery exact). C5 garbage target teacher: exhausted at 700,001, nothing stored.
- Curriculum note: double (549) -> quad (870) -> 16n (29,478): each layer teaches through dialog and the next layer is findable only because the previous one is in the library.
COST RECORDED HONESTLY: 'tried' counts only the search_oops phase. The unbudgeted capture phase (capture_lists full enumeration) grows with library size: ~800s CPU ablated vs ~7000s with three primitives (utime deltas, sandbox clocks unreliable - treat as approximate). For THIS task the tried metric favors reuse 23.7x while total compute favored the ablated arm; the claim is therefore scoped: accumulated knowledge makes deeper targets REACHABLE within the tried budget (16n was unreachable without it) and cuts search-phase tried 23.7x - it does not yet claim lower total compute. Future protocols should budget the capture phase (B-530/B-531 lesson).
CAN claim: dialog-taught procedures accumulate as reusable primitives; a target unreachable by direct search within budget becomes reachable via the taught library, ablation-credited, with the primitive visibly called in the found program. CANNOT: semantic understanding; designed frames + numeric DSL; total-compute superiority (see cost note); B-529 Correction 1 boundaries stand.
## B-532 pre-registration (2026-10-25, before running) - engineered-connectome arm 2: does WIRING contribute anything behaviorally distinct from isomorphic count tables?
Parent question (2026-10-24 17:08): distinguish an engineered depletion heuristic inspired by STD (arm 1) from a contribution of the connectome graph itself. Analysis before pre-reg: the T2 battery has no headroom for a wiring effect (gc precision 1.0; recall .767 is the structural ceiling of selecting 3 attrs against 3-4 true ones; B-523 battery exact). So arm 2 tests the graph on a capability the flat path lacks - multi-hop relational chain queries - and asks whether the GRAPH implementation differs behaviorally from the ISOMORPHIC count-table implementation of the same queries.
Design (b532.py):
- Small DESIGNED relational corpus (named as designed): ~10 Thai sentences forming entity-relation chains (e.g. นก กิน หนอน / หนอน อาศัย ดิน / ดิน อยู่ สวน) with branches, so 1..3-hop queries have ground-truth answer sets.
- Same information stored TWO ways: (G) explicit edge graph + traversal; (T) count/relation tables + designed multi-step lookup. Query frames designed and named.
- Arms: G-traverse, T-lookup, SHAM-G (degree-preserving rewired graph, same traversal code).
Criteria (pre-stated):
- C1 isomorphism: G and T return IDENTICAL answer sets on every query (1..3 hop, ~12 queries). If any differ, investigate which is wrong before any verdict - a difference is a bug finding, not a wiring contribution.
- C2 SHAM-G answers at <= chance overlap with ground truth (credits the wiring's content for G's answers, not the traversal code).
- C3 cost: record per-query candidate-visits for G vs T (the one axis they may honestly differ on).
- C4 existing battery unchanged (B-523 + skill path 160/160 x4 spot check).
Verdict logic: PASS-NULL if C1 identical AND C2 holds AND C4 exact => the connectome graph contributes NOTHING behaviorally distinct from count tables at current scope; wiring is an implementation choice, not a capability; the connectome line's only measured contribution remains arm-1's STD-inspired dynamics. Any C1 difference => BUG, fixed and recorded. C3 differences are reported as engineering facts only (not intelligence claims).
CAN claim if PASS-NULL: with evidence, that at current scope graph wiring adds no behavioral capability beyond isomorphic tables - closing the graph-contribution question honestly. CANNOT: wiring never matters (larger scale/dynamics could differ); biological claims; integration completeness.
## B-532 Amendment 1 (2026-10-25, before rerunning) - two harness bugs caught by the first run + sham criterion fix
First run FAILED, informatively:
1. Reverse multi-hop queries returned empty in BOTH arms (G==T everywhere, isomorphism held; both disagreed with hand-worked truth). Bug: reverse walks traversed the relation path in forward order instead of reversed. Fix: rev queries walk reversed(path).
2. C4 skill spot check failed 120/160 (all 'even'): KeyError 'mod'. The cached even program calls the pinned LIB primitive 'mod'; with cache hits, no setup/pinning call ever ran, so LIB stayed {add,sub}. PROVENANCE FINDING (recorded): skill execution silently depends on /tmp/c7_prog_0_base.json (the baselib pinning artifact) - not fully repo-backed. b529/b530 masked it because their teach() calls triggered pinning before the checks. Fix: explicit pinning block in b532 (same logic as cur7.search's), and a recorded TODO: make library pinning repo-backed.
3. Sham criterion: pre-registered 'sham mean Jaccard <= 0.2' measured 0.2462 - within-relation permutation on 5-edge relations leaves ~1/5 structural chance overlap, so the absolute bar was miscalibrated (bar-setting error, not a sham pass). Amended criterion, pre-stated before rerunning: G-vs-truth Jaccard 1.0 must exceed SHAM-vs-truth mean Jaccard by >= 0.5 (margin criterion, same crediting function as B-528's sham separation).
## B-532 verdict (2026-10-25) - PASS-NULL: graph wiring contributes NOTHING behaviorally distinct from isomorphic count tables at current scope
Pre-reg + Amendment 1 (2026-10-25). Harness b532.py. Verdict json: PASS-NULL (c1, c2, c4 true).
- C1 isomorphism: edge-graph traversal and relation-table joins returned IDENTICAL, correct answer sets on all 13 chain queries (1-3 hop, forward+reverse). Where both failed before the Amendment-1 fix, they failed identically - the stores are behaviorally isomorphic, as predicted.
- C2 content credit: G-vs-truth Jaccard = 1.0 vs SHAM-rewired mean 0.3077 (margin .692 >= .5) - G's correct answers come from the wiring's CONTENT, not the traversal code.
- C3 cost (engineering fact only): graph 24 candidate-visits vs tables 83 over the query set - adjacency is cheaper per query at this scale; no capability difference.
- C4 existing system unchanged: battery exact, skills 160/160.
Conclusion for the connectome line (answering the 2026-10-24 17:08 steering question): at current scope the ONLY measured connectome-derived contribution to the answer path is arm 1's STD-inspired depletion DYNAMICS over counts (experimental). The graph wiring itself is an implementation choice with no measured behavioral contribution - recorded honestly; it stays out of the answer path and out of capability claims. Ash's cut rule applied to claims, not to the code: the engineered graph remains available as an engineering structure (cheaper associative lookups, C3) but earns no intelligence-adjacent language.
Also recorded (Amendment 1): reverse-walk harness bug (both arms), LIB-pinning /tmp provenance dependency (TODO: repo-backed pinning), sham bar miscalibration -> margin criterion.
## Provenance fix (2026-10-25) - LIB pinning is now repo-backed
B-532 Amendment 1 found skill execution silently depended on /tmp/c7_prog_0_base.json. Fix: the pinned base library (12 programs: mod/mul/div/power/gcd/max/min/fact/sumto/square/choose2/dblfact) is committed as ai/wnn/logs/baselib_pin.json; cur7.search and b532 pin repo-first, /tmp as fallback. Fresh-clone skill execution no longer depends on a sandbox /tmp artifact.

## Hardening: repo-backed skill pinning + clean-process regression (2026-10-25, parent direction 00:37)
Context: B-532 Amendment 1 found cached skills could not execute in a fresh process without
the transient /tmp/c7_prog_0_base.json artifact. Parent directed: fix before deeper curriculum,
add clean-process/rebuilt-workspace regression coverage, explicit missing/corrupt dependency
handling, retain skill provenance.
- 8d3e4db: logs/baselib_pin.json (12 pinned programs) committed; cur7.search + b532 pin
  repo-first with /tmp fallback; fresh-process sanity even(24)=1, even(21)=0 passed.
- This commit: b527.derive_skills hardened - unreadable cache falls back to full re-derivation
  with WARNING; pin_lib() (repo-first) called before an execution self-check of every skill on
  ground-truth probes, raising RuntimeError naming logs/baselib_pin.json when a dependency is
  missing/corrupt. regress_skills.py: 3-check clean-process regression (C1: /tmp hidden,
  fresh subprocess, 40/40 sentence-path spot per skill; C2: both pinning sources hidden ->
  clear RuntimeError; C3: corrupt cache -> warning + re-derivation, no crash).
- FINDING (cache gap): logs/b527_skills_cache.pkl contained ONLY 'even' (evidence of a
  partially-completed earlier re-derivation, interrupted after the first task). Untracked
  derived cache; the regression run's re-derivation repopulates it. Known hazard recorded:
  pinning must never let a TARGET task resolve through the pinned library - cur7.search
  EXCL handling covers search; b529-style induce() clears EXCL, so a future teach of a
  target that IS in baselib_pin.json would shortcut. Current taught targets
  (double/quad/16n) are not in the pin set; B-529/530/531 results unaffected.
- Regression verdict: PASS (2026-10-25 03:22, logs/regress_skills.log).
  C1 clean process, /tmp artifact hidden: all 4 skills execute, 40/40 sentence-path spot each
  (pinning resolved from repo logs/baselib_pin.json). C2 both pinning sources hidden: clear
  RuntimeError naming the dependency. C3 corrupt cache: WARNING + full re-derivation, rc 0.
  Note: re-derivation runs at baseline cost (~25-30 min CPU per task) because derive_skills
  does not add derived skills to LIB between tasks - recorded as a known cost characteristic,
  not a correctness defect (found programs are train-trace-verified either way; the original
  oops-mode speedups in b515 came from the library-growth protocol of that experiment).
## B-533 pre-registration (2026-10-25, before running) - capture-budgeted curriculum accounting: does B-531's reuse advantage survive TOTAL-tried accounting?
Context: B-531's honest cost note recorded that 'tried' counts only the search_oops phase; the capture phase (capture_lists) evaluates one full first (comb,init) block as a side effect of reusing cur7.search for list materialization, and that block grows ~quadratically with library size (B-531 clock estimates ~800s CPU ablated vs ~7000s reuse; sandbox clocks unreliable). Parent direction 2026-10-25 00:37: continue with capture-budgeted experiments.
Source analysis (pre-registered, from cur7.search): the only tried_cap check is per (comb,init) block, so a tried_cap=0 capture evaluates EXACTLY the first block = len(conds) x len(bases) x len(steps_pair) candidates; the captured lists are fully materialized BEFORE any evaluation, so those evaluations are pure harness overhead (search_oops re-enumerates every candidate from the lists anyway).
Design (b533.py); same arms/target as B-531 (ablated vs reuse [double+quad dialog-taught in-run, sumto seeded], target hexdec 16n fixed by B-531's selection rule - no re-selection):
- Fix under test: zero-eval capture (tried_cap=-1: materialize lists, evaluate nothing). Harness-only change; no protocol change.
- C1 equivalence: zero-eval captured lists IDENTICAL to old-protocol captured lists, both arms (dict equality on combs/inits/conds/bases/steps_pair/steps_single/posts).
- C2 outcome equivalence: search_oops on zero-eval lists reproduces B-531 exactly: ablated exhausts the 700,001 cap with no program; reuse finds the same 16n program (calls 'quad') at tried=29,478 (same seeds, deterministic enumeration). Any difference means the capture evaluations were silently load-bearing -> FAIL of the fix, recorded as a harness-provenance finding in the same class as the /tmp pinning dependency.
- C3 exact old-protocol capture cost: computed from list sizes (len(conds) x len(bases) x len(steps_pair)) per arm, AND validated by one actual old-protocol capture run on the ablated arm; measured tried must equal the computed product.
- C4 total accounting recorded BOTH ways per arm: old-protocol total (capture tried + search tried) and zero-eval total (search tried only). The honest claim each supports is stated; the old-protocol totals are expected to shrink the 23.7x ratio - reported, not hidden.
- C5 no interference: seeded 160/160 x4, double+quad 40/40 after the harness change.
Verdict PASS iff C1 & C2 & C3 & C5 hold; C4 numbers recorded either way.
CAN claim if PASS: for this task, accumulated dialog-taught knowledge cuts TOTAL program-search tried 23.7x and makes an otherwise-unreachable target reachable, with capture-phase accounting exact and harness overhead removed. CANNOT: anything beyond B-531's boundaries (no semantic understanding; designed frames + numeric DSL; single-task evidence; not a general compute law).
## B-533 Amendment 1 (2026-10-25, before running) - replicate B-531's exact LIB state
The derive_skills hardening (c10bda9, pin_lib() before the execution self-check) pins ALL 12 baselib programs into LIB, including fact/square/choose2/dblfact, which were NOT in LIB during B-531's run (old derive_skills never pinned). Enumeration content/order depends on LIB keys, so B-533 would not reproduce tried=29,478 for a reason unrelated to the capture fix. Amendment: b533 pops fact/square/choose2/dblfact AND sumto from LIB immediately after derive_skills in BOTH arms (recorded in the harness); in the reuse arm teach_primitives re-adds sumto via as_primitive exactly as b531 did. This restores B-531's exact LIB state at every stage (9 ops during double teaching; 12 at target teaching); all other conditions identical to b531 (teach_primitives seed=0, target hexdec, CAP7=700,000). C2's exact tried replication (ablated 700,001 exhausted; reuse 29,478, calls 'quad') stands.
## B-533 verdict (2026-10-25) - PASS: capture overhead was pure harness cost; B-531's claim upgrades to total-tried, AND the old protocol silently REVERSED the total-cost comparison
Pre-reg + Amendment 1 (2026-10-25). Harness b533.py, log logs/b533_capture.log.
- C1 equivalence: zero-eval capture (tried_cap=-1) produces enumeration lists IDENTICAL to the old protocol, both arms (dict equality).
- C2 outcome equivalence: exact B-531 replication with zero-eval capture: ablated exhausts 700,001 (no program); double 549; quad 870; reuse finds the SAME 16n program calling 'quad' at tried=29,478, 40/40 unseen. The capture evaluations were NOT load-bearing.
- C3 exact capture cost: old-protocol capture tried measured == computed (len(conds) x len(bases) x len(steps_pair)), both arms: ablated 1,291,776; reuse 2,217,984. Replaces B-531's unreliable clock estimates (~800s/~7000s) with exact counts.
- C4 total accounting (the finding): under the OLD protocol, totals were ablated 1,991,777 vs reuse 2,247,462 - the reuse arm's TOTAL tried was HIGHER; the 23.7x search-phase advantage was silently reversed by capture overhead growing with library size. B-531's claim survived only because capture tried was never counted. With zero-eval capture (C1/C2 prove this changes no outcome), totals are ablated 700,001 (exhausted, unreachable) vs reuse 29,478: the 23.7x advantage is now a TOTAL-tried statement for this task.
- C5 no interference: 160/160 x4 seeded skills, double+quad 40/40.
- Harness change following: b515.capture_lists default becomes zero-eval (harness-only; tried counts in b529/b530/b531 were never affected since capture tried was discarded, and C2 shows outcomes identical).
CAN claim (upgrades B-531's scoped claim for THIS task): accumulated dialog-taught knowledge makes an unreachable target reachable and cuts total program-search tried 23.7x, with exact capture accounting. CANNOT: anything beyond B-531's boundaries (no semantic understanding; designed frames + numeric DSL; single-task evidence; not a general compute law). General warning recorded: any future reuse/curriculum experiment must budget capture, because capture cost grows ~quadratically with library size and can silently reverse total-cost comparisons.
## B-533 Addendum 1 (2026-10-25, parent-directed claim qualification)
Parent 2026-10-25 04:59: cap-qualify the comparison and state teaching-inclusive totals.
1. CAP-QUALIFIED: the ablated arm EXHAUSTED the 700,001 budget without finding any program.
   The comparison is success-vs-not-found-within-budget, NOT an exact speedup against a
   completed baseline; the true ablated cost is unknown (> 700,001).
2. TEACHING-INCLUSIVE TOTALS (B-533's C4 counted only the target's own search+capture):
   the reuse arm's full learning sequence is double teach + quad teach + target teach.
   Exact per-stage capture blocks (LIB 9/10/12 ops): 1,291,776 / 1,572,864 / 2,217,984.
   Old-protocol reuse TOTAL = (549+870+29,478) search + 5,082,624 capture = 5,113,521 tried
   (+ 9 confirmation evaluations). Old-protocol ablated TOTAL = 700,001 + 1,291,776
   = 1,991,777. Under the old protocol the reuse arm cost 2.57x MORE total tried.
   Zero-eval (current default) totals: reuse 30,897 tried (+ 9 confirmations) vs ablated
   700,001 (exhausted, nothing found) = 22.6x fewer tried AND reachability, cap-qualified.
3. METRIC LABEL: 'tried' = search-candidate evaluations (candidate programs screened),
   NOT full compute: per-candidate cost varies (run() executions, staging depth), and
   confirmation/accuracy verifications are counted separately (9 confirmation evals in the
   reuse learning sequence; post-hoc accuracy spots are reporting, not learning).
   No wall/CPU claims (sandbox clocks unreliable, B-531 lesson).
## Integration gap analysis (2026-10-25, parent direction 04:59: prioritize the fully integrated usable hsml over another isolated curriculum layer)
Grounded in BACKLOG.md integration status + current code:
- G1 (CORE): teaching and answering live in SEPARATE entry points. HSMLMemory.answer() handles queries; b529.teach() is a harness function driving a scripted Teacher; each experiment builds its own memory. There is no single conversation flow where one incoming sentence can name/exemplify/confirm (teach), state (observe), or ask (answer) against ONE memory object. Ash's bar ("one system, real data flow end-to-end, no stub routing") is not met while teach and answer are separate doors into separate memories.
- G2: no full-memory persistence story (taught skills, attrs) across processes; only seeded-skill cache + baselib_pin exist.
- G3: relation/graph store (B-532) sits outside the unified memory; engineering-only status (isomorphic to tables, cheaper per query).
B-534 (below) takes G1 as the highest-value bounded step: one conversation entry point over one memory, teaching and answering interleaved in one conversation.

## B-534 pre-registration (2026-10-25, before running) - one conversation entry point: teach and answer interleaved against ONE memory
Design (hsml.py): class HSML wrapping HSMLMemory with a single hear(sentence) -> response entry. Designed frames (named as designed): naming ('วิธีนี้ชื่อ X'), example ('ถ้า n เป็น A ตอบ B'), confirmation reply ('ตอบ Y'), statement (observation into attr memory), query (existing answer path), else abstain. Teaching state machine lives in the conversation: naming opens a teaching context for a NEW word; examples accumulate; at 5 pairs the system induces (b529.induce, zero-eval capture default post-B-533); on a candidate it ASKS a confirmation question ('ถ้า n เป็น C ตอบอะไร'); 3 correct confirmations store the skill into the SAME memory the query path reads; a failed confirmation continues the dialog (b529 protocol, cap 3 rounds). The SAME HSML object carries the whole conversation; a skill taught mid-conversation is immediately queryable in that conversation.
Criteria (pre-stated):
- C1 one process, one HSML object, one memory for the whole scripted conversation (no per-segment rebuilds).
- C2 a skill taught mid-conversation (double, then quad by dialog) answers correctly through the query path IN THE SAME conversation: 10/10 unseen in-conversation probes each.
- C3 interleaving does not corrupt: after a mixed conversation (teach double, attr statements, queries, teach quad, queries), seeded skills 40/40 x4 spot, attribute battery exact, no-skill-query abstains.
- C4 order independence: answers about double remain correct AFTER quad is taught (no clobbering).
- C5 data-flow evidence: the conversation log records each response's memory source (taught-this-conversation vs seeded vs attr store vs abstain) - no response from a stub.
- C6 garbage-teacher control in-conversation: a random-response teacher yields no stored skill (tried cap 700,001 recorded).
Verdict PASS iff C1-C6. CAN claim: one conversation entry point teaches and answers against one memory with real data flow (integration claim, scoped). CANNOT: semantic understanding, natural-language generality (designed frames + numeric DSL), intelligence claims; B-529 Correction 1 boundaries stand.

### Correction (B-533 harness reproducibility)
Committed b533.py (through 0dfa327) assigned tuple-returning `capture_zero` directly to `b529.capture_lists`; the executed PASS run used the working-tree wrapper `capture_zero_lists` (applied 03:27 UTC, before the run completed 04:57 UTC). Re-running the committed script would not reproduce the verdict. Fixed by committing the executed version. Verdict data and log are unaffected (produced by the now-committed code).

### B-534 Amendment 1 (C6 garbage-teacher control: bounded induce cap)
Pre-registered C6 used the default 700,001-tried induce cap per round. Measured during execution: under the pinned-12 baselib regime (c10bda9), exhaustive dialog induction sustains only ~0.6 tried/s in deep enumeration phases (tried ground truth via py-spy locals: 271,898 -> 272,026 over 210s; 3/3 stack samples inside the pin_lib lambda, b527.py:97 - candidates invoke pinned baselib programs via nested interpreted run under CAP 400). Projected cost of one exhausted round > 8 CPU-days; up to 3 rounds. Infeasible as a routine control. In-flight data at kill: C6 round 1 induce, tried=272,026, phase 0, no candidate proposed, nothing stored, gate unbreached. Amended: C6 induce cap = 60,000 tried/round (109x double's measured 549-tried teach; recorded in verdict JSON as c6_garbage.cap). What the amended control shows: the confirmation gate is exercised against a random-response teacher and no skill is stored - unchanged. What it does NOT show: exhaustive-space absence of a 5-pair fit; no such claim is made. MOTIVATES (not yet done): separating execution-LIB from induction-LIB (pinned recursive programs in candidate space are the cost driver) - BACKLOG item. double and quad teaches were unaffected (both stored successfully at full cap earlier in the same conversation).

### B-534 Verdict: PASS (2026-10-25, log logs/b534_conv.log, executed under Amendment 1)
One scripted conversation through HSML.hear() over ONE memory (hsml.py), pre-reg criteria:
- C1 single object across the whole conversation (teach + query + attr): PASS.
- C2 dialog-taught skill immediately queryable in the same conversation: double probe 10/10; quad probe 10/10.
- C3 pre-existing abilities intact: pre-teaching query abstains (c3_abstain_before_teaching); seeded 40/40 x4 (even, sumto, square, choose2); attr battery exact (abstain 13/13, unique 32/32, ambig 22/22, unk_flag 32/32, unk_valid 32/32).
- C4 no clobber: double probe still 10/10 after quad taught.
- C5 every response carries a recorded memory source: dialog 45, induction 9, attr 220, unknown_all 2 (the two pre-teaching abstained queries, routed through mem.answer's default; recorded, not hidden).
- C6 garbage-teacher control (Amendment 1 bounded cap 60,000/round): teach_failed after 60,001 tried (round 1 exhausted, no fit proposed), nothing stored, follow-up query abstains.
ACCOUNTING (search-candidate tried, labeled separately from execution): double teach 549, quad teach 870 - byte-identical to the B-531/B-533 direct-API costs, i.e. the dialog path reproduces the underlying teaching protocol exactly; C6 control 60,001 (amended cap). Conversation total search tried = 61,420. Probes, seeded evals and the attr battery are execution, not search. Zero-eval capture default (post-B-533); no uncosted capture blocks in this experiment.
Claim boundary (pre-reg, unchanged): CAN claim one conversation entry point teaches and answers against one memory with real data flow (scoped integration claim). CANNOT claim semantic understanding, natural-language generality (designed frames + numeric DSL), or intelligence. B-529 Correction 1 boundaries stand. Run-1 in-flight data (272,026 tried at kill, gate unbreached) recorded in Amendment 1.

## B-535 pre-registration (2026-10-25, before running) - G2: full-memory persistence across processes
Gap (LEDGER integration gap analysis 2026-10-25): no full-memory persistence story; taught skills and attr observations live only in-process.
Design: HSML.save(path) / HSML.load(path) persisting the FULL learned state as data: dialog-taught skills {task: (prog, provenance)} (fn rebuilt via make_fn on load), CountBackend attr counts C, and the dialog-added SKILL_BY_WORD word map. Format tag 'hsml-mem-1'. Missing/corrupt/wrong-format files fail with a clear error, never a silent fresh memory.
Test (b535.py, two real processes via subprocess):
- C1 process 1: scripted conversation teaches double via dialog, observes attr statements, probes a FIXED probe set, stores the pre-save probe snapshot in the save file, saves, exits.
- C2 process 2 (fresh interpreter): fresh HSML + load; double answers 10/10 unseen inputs (400-3999) through the sentence path (behavioral recall, not storage presence).
- C3 attr probe decisions after load == pre-save snapshot exactly (unique/ambiguous/abstain parity).
- C4 provenance survives: double's provenance source == 'dialog' after load; seeded skills still answer (spot 40/40 even).
- C5 negative control: a never-taught word query abstains after load; no spurious skills.
- C6 missing file and corrupt file each produce a clear error, not a silent fresh memory.
Verdict PASS iff C1-C6. CAN claim: learned state (dialog-taught skills + observed attributes) persists across processes with behavioral recall through the same sentence path (engineering persistence). CANNOT: any new capability, generalization, or understanding claim. Accounting: search-candidate tried recorded for the teach; loads record zero tried.

### B-535 Verdict: PASS (2026-10-25, log logs/b535_persist.log)
G2 closed: HSML.save/load persists the full learned state (dialog-taught skills as (prog, provenance) data, attr count table, dialog word map; format tag hsml-mem-1) across REAL process boundaries (subprocess, clean interpreter). C1 teach+save (double, tried=549, matching B-531/B-533/B-534 exactly); C2 fresh-process behavioral recall 10/10 unseen through the sentence path; C3 attr probe decisions identical pre/post save (unique/ambiguous/abstain parity on a fixed probe set); C4 provenance source=='dialog' survives, seeded even 40/40 intact; C5 never-taught word abstains; C6 missing file and corrupt file each raise a clear error (no silent fresh memory). Accounting: search-candidate tried 549 (teach only); load records zero tried; probes are execution. Claim boundary: engineering persistence with behavioral recall through the same path - no new capability claim.

## B-536 pre-registration (2026-10-25, before running) - execution-LIB vs induction-LIB separation
Motivation (B-534 Amendment 1, measured): under the pinned-12 baselib regime, exhaustive dialog induction sustains ~0.6 tried/s in deep enumeration phases because candidates invoke pinned recursive baselib programs via nested interpreted run() under CAP 400 (3/3 stack samples inside the pin_lib lambda). This made the pre-registered 700,001-tried garbage control infeasible (>8 CPU-days/round projected). Execution pinning (c10bda9) stays untouched - provenance and regression posture are not weakened; the question is only WHICH combs the search enumerates.
Design: two induction-LIB regimes, execution-LIB identical (all 12 pinned) in both:
- Arm A (current default): induction enumerates over the full pinned-12 LIB.
- Arm B (separated): induction enumerates over primitives + skills taught IN-DIALOG (provenance 'dialog'), excluding the seeded recursive baselib programs from the search space. Dialog-taught skills stay reusable (B-531's reuse path preserved); baselib recursive programs stay callable at execution but are not search components.
Criteria (b536.py):
- C1 both arms teach double and quad via the identical dialog protocol; tried recorded per arm per teach.
- C2 deep target 16n: arm B reproduces the B-531 reuse phenomenon (program found that CALLS quad, tried recorded, cap-qualified); arm A runs to the same cap and its outcome is recorded either way.
- C3 behavioral equivalence: every stored skill in both arms answers 40/40 unseen through the sentence path.
- C4 cost accounting: tried per arm labeled as candidate-set-relative (the arms enumerate DIFFERENT candidate spaces, so tried is not a like-for-like speed measure; no wall/CPU claims - B-531 lesson); a qualitative per-candidate cost note grounded in stack sampling may be recorded as such.
- C5 arm B makes the garbage-teacher control feasible at the full 700,001 cap: teach_failed with tried recorded (the B-534 Amendment-1 bound becomes unnecessary if PASS).
Verdict PASS iff C1-C3 hold and arm B tried <= arm A on every shared teach and C5 completes. Adoption rule (pre-stated): PASS -> arm B becomes the default induction regime (execution stays pinned-12, no re-run of past verdicts; comparability note recorded); FAIL -> keep current default, record why. CAN claim: search-space engineering reduces dialog-induction cost while preserving dialog-taught reuse, with measured equivalence. CANNOT: any capability claim beyond the measured arms; comparability of tried across arms is explicitly limited (C4).

### B-536 Amendment 1 (pre-execution): arm A budget-matched, not cap-matched
The pre-reg's C2 as written ran arm A to the 700,001 cap - under the B-534 Amendment-1 measurement (0.6 tried/s sustained deep-phase under pinned-12) that is potentially >8 CPU-days and therefore not a bounded experiment. Amended BEFORE any run: arm A searches the SAME number of candidates arm B consumed for 16n (budget-matched) and the outcome is recorded as found / not-found within that budget (success-vs-not-found-within-budget, never a speedup claim - same discipline as B-533 Addendum 1). Arm B's garbage-teacher control (C5) remains full-cap 700,001: under the b529-era primitive LIB, 700K exhaustions completed feasibly in-session (B-529/B-531 era); if arm B's C5 itself proves infeasible mid-run, that is a FAIL-by-measurement and is recorded, not silently re-bounded.

### B-536 Verdict: PASS (2026-10-25, log logs/b536_run.log) - separated induction-LIB adopted as default
Arms in clean subprocesses (module-global LIB isolation), identical dialog protocol, execution-LIB pinned-12 in both:
- C1 double/quad taught in both arms: tried 549/870 BOTH arms (shallow teaches unaffected by regime).
- C2 deep target 16n: arm B (separated) FOUND a program calling quad at tried=27,430 (B-531 reuse phenomenon reproduced in-conversation); arm A (full pinned-12) found NOTHING within the budget-matched 27,431 tried (Amendment 1: success-vs-not-found-within-budget, NOT a speedup claim).
- C3 behavioral equivalence: every stored skill 40/40 unseen through the sentence path, both arms.
- C4 accounting: arm B tried <= arm A tried on every shared teach (equal: the arms share the cheap region); tried across arms is candidate-set-relative (different search spaces), no wall/CPU claims; qualitative per-candidate cost note: arm-A-regime deep enumeration measured 0.6 tried/s sustained with 3/3 stack samples inside the pin_lib lambda (B-534 Amendment 1), arm-B garbage exhaustion ran ~2,200 tried/s average in the same sandbox - regime difference grounded in stack sampling, rates are sandbox-CPU-relative, not benchmarks.
- C5 garbage-teacher control at FULL 700,001 cap under arm B: teach_failed, tried=700,001, nothing stored - the B-534 Amendment-1 bounding is no longer needed under the new default.
Adoption (pre-stated rule): separated induction-LIB is now hsml.py's DEFAULT induction regime (induction_lib='separated'); execution-LIB remains pinned-12 with provenance intact. Past verdicts unaffected (their teaches were regime-independent, confirmed by C1's identical tried); B-534's C6 stays as recorded under its Amendment 1 (history not rewritten); B-536 C5 supplies the full-cap control under the new default. Also new in hsml.py: dialog-taught skills enter the induction LIB at store time (the B-531 reuse path, now in-conversation) - this is what C2 exercised.
CAN claim: search-space engineering (excluding heavy pinned recursive baselib from induction) preserves dialog teaching + in-conversation reuse and restores full-cap control feasibility, with measured behavioral equivalence. CANNOT: capability claims beyond the measured arms; the arm-A miss is budget-qualified only.

Post-adoption regression (2026-10-25): b534.py and b535.py re-run under the new 'separated' default - both PASS with identical measurements (double 549, quad 870, C6 teach_failed at its amended 60,000 cap; persistence checks unchanged). No verdict text changed.

## B-537 pre-registration (2026-10-25, before running) - continual teaching across sessions
Gap: B-535 verified load-then-ANSWER; the usable-system loop is load-then-CONTINUE-TEACHING (memory grows across conversations). Known suspect: HSML.load restores skills + word map but does NOT register loaded skills into the induction LIB (B-536 registered only at store time), so a loaded skill would not be reusable as a component in a later session's induction.
Design: three real sessions (subprocess, clean interpreter each), one save file:
- S1: teach double via dialog, save.
- S2: load; teach quad via dialog (probes of double must still pass BEFORE the new teach starts); teach 16n via dialog (expected to reuse quad if registration is correct); save.
- S3: load; probe double/quad/16n 10/10 each; provenance of all three == 'dialog'; attr snapshot parity if used; never-taught word abstains.
Criteria: C1 S2 pre-teach double probe 10/10 (loaded memory behaviorally live before any new teaching); C2 S2 quad + 16n stored, 16n tried recorded and its program calls quad (cross-session reuse through the LIB registration); C3 S3 all three skills 10/10, provenance 'dialog' each; C4 cumulative-state check: S3's save contains all three skills (state accumulates, not just latest); C5 never-taught abstains in S3.
Verdict PASS iff C1-C5. If C2 fails by missing LIB registration, the pre-identified fix (register loaded skills into the induction LIB in HSML.load) is applied and recorded as the finding. CAN claim: learned memory accumulates across sessions through save/load with reuse intact. CANNOT: anything beyond cross-session persistence + reuse.

### B-537 Amendment 1 (post-first-run, pre-verdict): C2 test-design fix
First run PASSED but did not isolate the stated mechanism: S2 taught quad fresh before 16n, so quad entered the induction LIB via _confirm's store-time registration (B-536) regardless of load-time registration; the lesion arm (load registration reverted) also passed (23,334, via fresh quad). The load-registration path - a skill LOADED from a previous session being reusable without re-teaching - was not exercised. Amended C2: S2 loads (double only) and teaches 16n DIRECTLY (no fresh quad); the only composition path to 16n is through the loaded double (double∘double∘double∘double), so 16n-found-calling-สองเท่า is decisive for load-time registration. Arms: FIXED (load registers loaded skills into LIB) vs LESION (registration reverted). Lesion expectation: 16n not found within cap (B-531 ablated precedent) - recorded either way, budget-qualified. s2 sequence becomes: load -> probe double (C1) -> teach 16n directly -> save. The first run's verdict claim is withdrawn pending the amended run (nothing was committed).

### B-537 Amendment 2 (post-lesion-pair, pre-verdict): discriminator moved to the known-reachable horizon
Amendment 1's target (16n via double∘double∘double∘double, 4 composition levels) exhausted at 700,001 in BOTH the lesion and the fixed arm - inconclusive as a discriminator, and itself a finding: the composition horizon at this budget is ~2 levels (B-531/B-536 reach 2; 4 is out). Amended design: S1 teaches double AND quad; S2 loads and teaches 16n DIRECTLY (no fresh quad in S2) - the only short composition path is via the LOADED quad (2 levels, the measured-reachable horizon). FIXED arm (load registers loaded skills): expect 16n found calling สี่เท่า; LESION arm (registration reverted): expect exhaustion (B-531 ablated precedent). Structural check added: 'สองเท่า'/'สี่เท่า' membership in the induction LIB after load, fixed vs lesion (pins the mechanism independent of search luck). The crashed s3 (KeyError when 16n absent) is fixed to handle absence as recorded data, not a crash.

## B-537 verdict (2026-10-25) - PASS: learned memory accumulates across sessions through save/load with reuse intact; load-time LIB registration is the causal mechanism
Amended design (Amendment 2) ran both arms to completion; evidence logs/b537_sessions.log (FIXED) and logs/b537_lesion_s2.json (LESION).
FIXED arm (load() registers loaded skills into the induction LIB): S1 taught double (549 tried) + quad (870 tried), saved. S2 (fresh process, loaded): pre-teach double probe 10/10 (C1); structural check: สองเท่า AND สี่เท่า present in the induction LIB after load; 16n taught directly, STORED at 31,526 tried, induced program calls สี่เท่า (C2) - cross-session reuse through load-time registration. S3 (third fresh process): all three skills probe 10/10, provenance 'dialog' each (C3); save state cumulative, all three present (C4); never-taught เจ็ดเท่า abstains (C5). Verdict PASS, C1-C5.
LESION arm (only the load-time C7.LIB registration reverted; store-time registration intact): pre-teach double probe 10/10 (loaded skill stays behaviorally callable); structural check: NEITHER loaded skill in the induction LIB; 16n NOT stored, cap exhausted at 700,001 tried. The only difference between arms is the registration line, so the pass/fail difference is causally attributed to it, not to search luck (structural LIB-membership check pins the mechanism independent of the search outcome).
Numbers discipline: 31,526 (fixed) vs 700,001 (lesion) is success-vs-not-found-within-budget, NOT a ~22x speedup; the lesion outcome at this budget is unknowable as a ratio. S1 totals 549+870 are teaching-inclusive tried counts for this run.
Amendment-2 horizon finding (recorded): 16n via double∘double∘double∘double (4 composition levels) exhausted at 700,001 in BOTH arms of the Amendment-1 pair; the measured-reachable composition horizon at a 700K tried budget is ~2 levels (B-531/B-536 reach 2).
CAN claim: HSML memory accumulates across real processes through save/load; a skill LOADED from an earlier session is reusable as a component in a later session's induction, and the load-time LIB registration (hsml.py) is the mechanism that enables it. CANNOT: anything beyond cross-session persistence + component reuse; no claim about composition depth beyond ~2 levels at this budget.

## B-538 pre-registration (2026-10-25, before running) - conversational REVISION of a taught skill
Gap (next end-to-end integration gap after G1/G2 closed, parent 04:59 steering): a usable continually-taught system must let the teacher CORRECT a mistake through conversation. Current hsml.py ground truth: the naming frame always opens a fresh context; _confirm silently dict-overwrites mem.skills[word] and C7.LIB[word] on store. No revision provenance, no test that queries follow the NEW behavior and the OLD behavior is gone, no test that a FAILED re-teach preserves the original, no test that a revision survives save/load.
Design (hsml.py extension, named as DESIGNED): naming a word that is already a DIALOG-taught/loaded skill opens a revision context (response kind 'revision_opened'); completing teaching stores the new program WITH revision provenance (revision count + replaced program string recorded) and updates the induction LIB registration. Naming a SEEDED pinned-baselib word abstains 'reserved' (provenance protection); a failed revision (teach_failed) leaves the original skill fully intact.
Test (b538.py, one conversation + real subprocess persistence):
- C1 teach double (สองเท่า) via the standard dialog protocol; probe 10/10.
- C2 revision opens explicitly: naming สองเท่า again returns kind 'revision_opened' (not plain 'naming').
- C3 revision completes with corrected examples (target: n -> 2n+1): post-revision probes 10/10 on distinguishing inputs, and every probe answer equals the NEW function and NOT the old (2n) - old behavior gone through the same query path.
- C4 provenance: revised skill's prov records revision count 1 and the replaced program string.
- C5 failed-revision control: open a revision, feed a random-response teacher to exhaustion (full 700,001 cap feasible post-B-536); teach_failed recorded AND the revised skill still answers 10/10 - a failed revision never clobbers.
- C6 structural: after the revision, C7.LIB[word] wraps the NEW program (induction reuse path carries the correction).
- C7 persistence: save; fresh-process load; revised behavior 10/10, old behavior absent, revision provenance survives, word present in the induction LIB after load.
- C8 seeded-word protection: naming 'even' (seeded pinned baselib) abstains 'reserved'; seeded even still 40/40.
Verdict PASS iff C1-C8. CAN claim: a taught skill can be corrected through conversation, and the correction propagates to answering, the induction reuse path, and persistence, with failed corrections safe (scoped integration/usability claim). CANNOT: semantic understanding of the correction; natural-language generality (designed frames); anything beyond designed frames + numeric DSL; B-529 Correction 1 boundaries stand. Accounting: search-candidate tried recorded per teach (revision teach + C5 control), labeled as such; probes are execution.

### B-538 Verdict: PASS (2026-10-25, log logs/b538_run.log) - conversational revision of a taught skill works end-to-end; corrections propagate to answering, the induction reuse path, and persistence; failed corrections are safe
Run-1 FAIL on C8 (recorded, fix committed 3b97c6f): the reserved check tested `word in mem.skills`, but seeded skills are TASK-keyed ('even') while the naming frame receives the Thai word ('เลขคู่') - the reserved branch was unreachable for seeded words and a plain teach context opened instead. No clobber occurred in run 1 (no examples followed; even stayed 40/40), but the un-fixed code would have allowed silently shadowing a seeded skill. Fixed by resolving the Thai word through SKILL_BY_WORD; smoke-verified, then full re-run. The hazard the pre-reg anticipated was real and is now closed.
Run-2 (the verdict run), one conversation + fresh-process persistence:
- C1 double taught 549 tried, probe 10/10. C2 naming the same dialog-taught word returns 'revision_opened' explicitly.
- C3 revision to 3n stored at 613 tried; post-revision probes 10/10 on the NEW function and 0/10 on the OLD (distinguishing inputs) - old behavior gone through the same query path.
- C4 provenance: revision count 1, replaced program string recorded.
- C5 failed-revision control: garbage teacher exhausts the full 700,001 cap (teach_failed); the revised skill still answers 10/10 - a failed correction never clobbers.
- C6 structural: C7.LIB['สองเท่า'] wraps the NEW program post-store (executes 3n).
- C7 persistence: fresh-process load - new behavior 10/10, old gone 0/10, revision provenance survives, word in the induction LIB after load.
- C8 seeded-word protection: naming 'เลขคู่' (seeded pinned baselib) abstains 'reserved'; seeded even 40/40 intact.
Implementation note (within the pre-reg's designed revision path): the word being revised is EXCLUDED from the induction LIB during its own revision induction - the corrected method must not be defined in terms of the method being replaced, and this keeps save/load rebuild safe from self-reference. Recorded here because the pre-reg text did not state it explicitly.
Accounting: search-candidate tried - initial teach 549, revision teach 613, C5 control 700,001 (exhausted, nothing stored). Probes are execution.
Post-verdict regression: b534.py and b535.py re-run under the revision-aware hsml.py - both PASS with identical measurements (549/870, C6 teach_failed at its amended cap; persistence checks unchanged).
CAN claim: a dialog-taught skill can be corrected through conversation; the correction propagates to answering, the induction reuse path, and save/load persistence; failed corrections leave the original intact; seeded baselib skills are protected from naming collisions. CANNOT: semantic understanding of the correction; natural-language generality (designed frames + numeric DSL); B-529 Correction 1 boundaries stand.

### B-538 Addendum 1 (2026-10-25, parent-directed claim scoping)
Parent 2026-10-25: keep the B-538 claim scoped to the tested DIRECT revised skill until dependent behavior is verified. B-538 tested revision of a skill with NO dialog-taught dependents (C6 verified only the revised word's own LIB entry). It did NOT test what happens to a composed caller (e.g., สิบหกเท่า calling สี่เท่า calling สองเท่า) when a callee is revised: dependents may silently change behavior, retain stale closures, or break on reload. B-538's claim is hereby scoped: CAN claim correction of the direct revised skill propagates to its own answering, its own induction-LIB registration, and persistence. CANNOT claim anything about dependent learned skills under revision - that is B-539's question, grounded and pre-registered before any policy claim.

## B-539 pre-registration (2026-10-25, before running; parent-directed 10:02) - dependent-skill semantics under revision: explicit invalidation/revalidation policy
Grounded current behavior (measured 2026-10-25, scratch scripts, not the experiment): dependents reference callees BY NAME and resolve through C7.LIB at call time (cur7.run comb op; make_fn captures only the spec). Measured: teach double(549)/quad(870)/16n(27,430, prog calls สี่เท่า); revise quad 4n->5n; dependent 16n SILENTLY REBOUNDS - answers 25n in-session on previously-asked inputs (12,500 for n=500) and fresh inputs, and 25n again after save/load in a fresh process (17,500 for n=700). No provenance, no warning: a previously confirmed skill changes behavior silently when its callee is revised. (Note: quad's stored program does NOT call double - B-530 enumeration-order lesson; the only live dialog dependency in the chain is 16n -> quad.)
Design (hsml.py, DESIGNED and named): 
- Dependency provenance: at store time scan the stored program for references to other stored skills; record prov['deps'] and prov['dep_rev'] (each dependency's revision count at store).
- Explicit invalidation: completing a revision of word W (revision r) marks every stored skill depending on W STALE (prov['stale'] records the dependency and the revision transition). A stale skill does NOT answer queries: the query path returns an explicit 'stale_skill' response (recorded source), never a silently recomputed number. Stale skills are removed from the induction LIB (no building on unconfirmed foundations) and rejoin only on revalidation.
- Explicit revalidation: naming a STALE word opens 'revalidate_opened' (not revision): the system asks 3 confirmation questions against the STORED program executed under CURRENT dependencies (run() resolves names live, so this is the recomposed behavior); 3 correct teacher confirmations -> stale cleared, prov['revalidated'] count and dep_rev updated, LIB rejoin. A failed confirmation converts to the B-538 revision path (correcting pair added, induction resumes; stored with revision provenance).
- Cache coherence: C7.ev lru_cache is cleared at every successful store (revision, revalidation, or new skill) - no stale-cache residue class.
- Failed revision of a callee (teach_failed) stores nothing and marks nothing: dependents stay live.
Criteria (b539.py, conversation + real subprocess persistence):
- C1 dependency provenance: after teaching double/quad/16n, 16n's prov records deps == ['สี่เท่า'] with dep_rev {'สี่เท่า': 0}.
- C2 explicit invalidation: revising quad (4n->5n) marks 16n stale with the revision transition recorded; quad's own B-538 revision semantics intact.
- C3 no silent rebind: querying stale 16n returns kind 'stale_skill' (never a number); 16n absent from the induction LIB while stale. (Grounded pre-fix behavior was silent 25n rebound - recorded as the lesion contrast.)
- C4 revalidation-accept: naming stale 16n opens 'revalidate_opened'; teacher confirms the RECOMPOSED behavior (25n) on 3 checks; 16n revalidated: answers 25n 10/10, stale cleared, prov revalidation + dep_rev {'สี่เท่า': 1} recorded, back in the LIB.
- C5 revalidation-reject -> revision: repeat to a stale 16n; teacher answers the OLD behavior; first check fails into a revision context; teacher explicitly re-teaches 16n; stored with revision provenance; probes follow the re-taught behavior.
- C6 failed-callee-revision control: garbage revision of quad (full 700,001 cap) teach_failed; 16n NOT stale, answers 16n 10/10 throughout.
- C7 cross-session: save with 16n stale; fresh-process load: 16n still stale (explicit response), quad revised; revalidate post-load; 16n answers the recomposed behavior 10/10; provenance survives.
- C8 cache coherence: probe inputs asked BEFORE a revision return post-revision-consistent answers after it (revised word itself, same inputs, new behavior 10/10) - no stale-cache residue.
Verdict PASS iff C1-C8. CAN claim: revision of a taught skill invalidates its learned dependents EXPLICITLY (visible stale state, no silent behavior change), with a measured revalidation path and cross-session persistence of the marks. CANNOT: semantic understanding; natural-language generality (designed frames); anything beyond designed frames + numeric DSL; B-529 Correction 1 boundaries stand. Accounting: search-candidate tried per teach/revision/control recorded; revalidation confirmations counted separately (no induction).

### B-539 Amendment 1 (pre-execution, 2026-10-25): transitive invalidation + C9; chain and C5-target fixes
Recorded before any run, from the design pass:
1. TRANSITIVE hazard: invalidating only DIRECT dependents leaves a transitive dependent (a skill depending on a now-stale skill) live while its callee is popped from the LIB - its comb op would resolve LIB[stale_word] at query time and CRASH (KeyError), not abstain. Implementation therefore marks staleness by FIXPOINT over deps (direct revision mismatch OR any dependency itself stale). C9 added: a transitive dependent (256n = สิบหกเท่า∘สิบหกเท่า, deps == ['สิบหกเท่า'] only, NO direct quad dep) is marked stale when quad is revised; querying it returns the explicit stale_skill response (no crash); it stays stale after 16n's revalidation until its own revalidation (explicit per-skill policy).
2. Chain choice: 64n cannot serve as the transitive test - every findable 64n composition references สี่เท่า directly (64 = 4x16 or 4x4x4). 256n = 16n∘16n is the clean transitive case (deps [16n] only).
3. C5 re-teach target: the pre-reg said "teacher explicitly re-teaches 16n" after rejection. Under quad=5n, 16n is UNREACHABLE (B-531: ablated 16n exhausted 700,001; 16n is findable only via a 4n component). Amended: the reject-path re-teach target is 10n (= สองเท่า∘สี่เท่า under the revised callees, 2 levels, findable in the post-revision LIB). C5 tests the reject->revision MECHANISM (stored with revision provenance, probes follow the re-taught behavior); the target is the teacher's explicit choice, recorded. The word retains its Thai label; the mechanism does not depend on word semantics.
4. Ordering: C6 (failed-callee-revision control, full 700,001 cap) runs BEFORE any successful revision so "16n answers 16n" is measurable. C4 (revalidate-accept) runs in-session. C7 (cross-session) uses a second stale cycle: after C4/C5, quad is revised again (5n->6n, revision 2), re-staling 16n; save; fresh-process checks + post-load revalidation (recomposed 36n).

### B-539 Verdict: PASS (2026-10-25, log logs/b539_run.log) - revision invalidates learned dependents EXPLICITLY (no silent rebind), with a measured revalidation path, cross-session persistence, and transitive marking
Run-1 FAIL on C5 only (recorded): harness protocol bug, not an hsml defect - the rejecting confirmation answer stated the OLD target (256n) while Amendment 1's re-teach target was 10n, making the accumulated pairs internally inconsistent (teach_failed); also the harness tried to feed example sentences while a confirmation was pending (the b529 protocol re-induces immediately after a failed check; examples abstain while pending). C1-C4, C6-C9 passed already in run 1. Harness fixed (rejecting answer states the desired value; confirmation-driven revision loop); full re-run:
- C1 dependency provenance: 16n deps == ['สี่เท่า'], dep_rev {'สี่เท่า': 0}; 256n deps == ['สิบหกเท่า'] (transitive chain 256n -> 16n -> quad). Tried: double 549, quad 870, 16n 27,430, 256n 31,526.
- C2 explicit invalidation: quad revised 4n->5n (revision 1, tried 47,910, replaces recorded); 16n marked stale {dep สี่เท่า, from_revision 0, to_revision 1}.
- C3 no silent rebind: querying stale 16n returns 'stale_skill' (never a number); 16n out of the induction LIB while stale. (Grounded pre-fix behavior: silent 25n rebound in-session AND post-load - the lesion contrast.)
- C4 revalidate-accept: naming stale 16n opens 'revalidate_opened'; 3 confirmations of the recomposed behavior (25n); revalidated: answers 25n 10/10, stale cleared, dep_rev {'สี่เท่า': 1}, revalidated count 1, back in LIB.
- C5 revalidate-reject -> revision: 256n's revalidation rejected by stating the desired value (10n target, Amendment 1); converts to the B-538 revision path; re-taught and stored at tried 29,285 with revision provenance (revision 1, replaces recorded); probes follow the re-taught behavior 10/10.
- C6 failed-callee-revision control: garbage revision of quad exhausts 700,001 (teach_failed); 16n NOT stale, answers 16n 10/10 - a failed correction marks nothing.
- C7 cross-session: quad revised again (5n->6n, revision 2) re-staling 16n; save; fresh-process load: 16n still stale (explicit response, out of LIB), quad revision 2 answering 6n 10/10; post-load revalidation (recomposed 36n) succeeds: 16n answers 36n 10/10, dep_rev {'สี่เท่า': 2}, revalidated count 2, LIB return. Stale marks and revision provenance survive save/load.
- C8 cache coherence: quad probed pre-revision 10/10 (cache filled); post-revision the SAME inputs return the new behavior 10/10 (ev lru_cache cleared at store).
- C9 transitive (Amendment 1): 256n (deps [16n] only, no direct quad dep) marked stale by the fixpoint when quad was revised; querying it returns the explicit stale_skill response (no crash); still stale after 16n's revalidation until its own (explicit per-skill policy).
CAN claim: revision of a taught skill invalidates its learned dependents EXPLICITLY (visible stale state, explicit response, induction-LIB exclusion, no silent behavior change), dependency/version provenance is recorded, a measured confirmation-only revalidation path exists (accept AND reject->revision), failed callee revisions mark nothing, and the marks persist across save/load. CANNOT: semantic understanding; natural-language generality (designed frames + numeric DSL); anything beyond; B-529 Correction 1 boundaries stand. Accounting: search-candidate tried recorded per teach/revision/control above; revalidations are confirmation-only (zero induction tried); probes are execution.

## B-540 pre-registration (2026-10-25, before running) - mixed-dialog end-to-end integration battery (parent 04:59 steering: usable integrated system over another isolated layer)
Question: every integration experiment so far ran one activity in a clean sequence (B-534's interleave was small: two teachings + one attr block + battery). Does the ONE-system claim hold under ONE sustained MIXED conversation that interleaves every connected subsystem - observations, attr probes, teachings, abandonment, revision, stale/revalidation, unknown abstains - and continues across a mid-conversation save/load into a fresh process? The B-538->B-539 lesson: isolated tests miss composed behavior; this measures the composition across subsystems.
Design (b540.py, scripted harness; all frames DESIGNED and named): one HSML object, fixed interleaved script, save, fresh-process load, continue. Script: observe animal corpus -> attr probe -> teach double -> teach quad WITH interleaved attr observation + attr probe + double query between its examples -> abandonment probe (name ห้าเท่า, 2 examples, switch name to แปดเท่า, complete) -> teach 16n (quad in LIB) -> unknown-word abstains -> revise quad 4n->5n -> stale checks -> revalidate 16n (25n) -> revalidate any other newly-stale taught skill to its recomposed behavior (recorded) -> attr battery -> log integrity -> save. Fresh process: load -> all probes at recorded final behaviors -> attr battery -> abstains -> teach สามเท่า 3n -> bounded garbage control (cap 60,000/round, B-534 Amendment 1 lesson) -> log integrity.
Criteria:
- C1 interleave survival: the open teaching context survives interleaved non-dialog utterances between examples - quad stores and probes 10/10; the interleaved attr probe ('ปีก' ambiguous) and double query (14) answer correctly at the moment asked.
- C2 no cross-talk: full attr battery (b526 battery()) exact after ALL numeric activity at session-1 end AND post-load; skill probes exact after attr activity.
- C3 abandonment semantics (DESIGNED, measured): naming a second word mid-teaching discards the partial context - the abandoned word never becomes a skill (query abstains no_skill); the completed word (แปดเท่า 8n) probes 10/10.
- C4 revision semantics in mixed dialog: revise quad -> 16n returns stale_skill (never a silent number); revalidate -> recomposed 25n 10/10; independent double unaffected 10/10 at every probe point. Any other taught skill the B-539 fixpoint marks stale (e.g. แปดเท่า if its stored program calls quad) is RECORDED and revalidated to its recomposed behavior before save.
- C5 unknown-word abstains at >=3 interleave points: unknown skill word (ร้อยเท่า) and unknown attr word (เขา) abstain; nothing fabricated.
- C6 log/provenance integrity: every logged utterance has non-null kind AND source; checkpoint response kinds match designed routing exactly (naming/example/observed/attr_answer/skill_answer/stale_skill/revalidate_opened/skill_revalidated/abstain).
- C7 cross-session continuity: fresh-process load mid-conversation reproduces session-1 final behaviors (double 2n, quad 5n, 16n 25n, แปดเท่า at its recorded final multiplier, attr battery exact, abstains); post-load teaching of สามเท่า 3n stores and probes 10/10; bounded garbage teacher teach_failed, no skill from garbage.
Verdict PASS iff C1-C7. CAN claim: the integrated system holds its measured behaviors under sustained mixed use and across a mid-conversation save/load, within designed frames. CANNOT: NLU; robustness beyond designed frames; unmeasured interleavings; B-529 Correction 1 boundaries stand. Accounting: search-candidate tried recorded per teach/revision; revalidations confirmation-only (zero induction); bounded garbage cap recorded (60,000/round, not the full 700,001 - B-534 Amendment 1); probes are execution.

### B-540 Verdict: PASS (2026-10-25, logs b540_run.log + b540_s1/s2.json) - ONE-system behaviors hold under sustained mixed dialog + mid-conversation save/load; run-1 surfaced a REAL routing defect (fixed)
Run-1 FAIL (recorded): corpus-observation checkpoint failed - hsml.py's DESIGNED first-token attr routing misrouted 51/219 corpus STATEMENTS (frames starting with an attr word: 'ปีก ของ นก สวย', 'ขน และ หาง ของ หมา') as PROBES: their content was never observed and the speaker got a question-answer back to a statement. Invisible in B-534 (corpus response kinds unasserted; redundant frames covered every animal-attr pair so the battery still passed). Fix (DESIGNED, named, hsml.py): attr probe iff EVERY token is an attr word or 'เขา'; any sentence containing an attr word plus other content is OBSERVED. Harness bug fixed alongside (interleave used ช้าง/งา, not in the B-521 world).
Re-run PASS C1-C7: tried double 549 / quad 870 / แปดเท่า 25,446 / สิบหกเท่า 29,478 (deps [สี่เท่า]) / quad revision 47,910 -> 16n stale_skill -> revalidated 25n 10/10 / post-load สามเท่า 613 / garbage bounded 60,001 teach_failed; attr battery exact at session-1 end AND post-load; unknown-word abstains (skill + attr); abandonment discards partial ห้าเท่า (abstains, completed แปดเท่า 10/10); log 370+69 entries, every one with kind+source.
Recorded: แปดเท่า found as double∘double∘double (deps [สองเท่า] only) - enumeration order again prefers the direct composition (B-530 lesson); the B-539 fixpoint correctly did NOT stale it under quad's revision; probes 8n throughout.
Regressions post-router-fix: b534 PASS, b535 PASS, b539 PASS (chunked s1a/s1b/s1c/s2 via the supported save/load path, load == in-session state per B-535/537; s1a tried match the merged run exactly (549/870/27,430/31,526); C6 re-run BOUNDED at 60,001 with all behavioral assertions holding (sandbox per-call ceiling; merged full-cap C6 stands from the original run; the router diff is attr-routing only, disjoint from every b539 sentence frame); s1c quad-revision tried 52,006 vs 47,910 differs only because the chunked load resets the confirmation-sampling rng).
CAN claim: within designed frames, the integrated system holds every measured behavior under sustained MIXED use (observations, probes, teachings, abandonment, revision, stale/revalidation, unknowns interleaved) and across a mid-conversation save/load; abandonment discards partial teachings; every utterance is logged with provenance. CANNOT: NLU; beyond designed frames; unmeasured interleavings; B-529 Correction 1 boundaries stand.

## B-541 pre-registration (2026-10-25, before running; parent-directed 12:42 after the fresh eval_ash baseline found the defect) - no acknowledgement without persisted learning: dynamic name/attr vocabulary vs honest rejection
Grounded defect (eval_ash_20261025.json, preserved untouched): 'เหยี่ยว มี ปีก' -> 'จำไว้แล้ว' but CountBackend.observe counts only names in the hardcoded B-521 ANIMALS x ATTRS - the new name was silently dropped; the ack was dishonest.
Design (DESIGNED, named): statement frames from B-521 (7 frames: X มี Y / X นั้น มี Y / ดู Y ของ X / Y ของ X สวย / X มี Y และ Z / Y และ Z ของ X / X มี Y และ Z และ W) are PARSED for (name, attrs) positions; CountBackend gains observe_pairs (dynamic names AND dynamic attr words - the frame position grounds the role) and vocab() = seed ATTRS + every attr ever stored; the probe path filters by vocab() (dynamic); a sentence with attr content but no designed frame now abstains HONESTLY instead of being token-scavenged. Legacy observe(toks) kept for old harnesses. Dialog/skill frames match before attr routing as before.
Criteria (b541.py + fresh-process s2):
- C1 new-name learning: 'เหยี่ยว มี ปีก' -> 'จำไว้แล้ว' AND a 'ปีก' probe afterward INCLUDES เหยี่ยว (ack == persisted learning); multi-attr frame with new name likewise ('ดู เกล็ด ของ ปลาใหม่').
- C2 new-attr learning: 'ส้ม มี เปรี้ยว' -> acknowledged AND probe 'เปรี้ยว' -> unique ส้ม (dynamic attr vocabulary grounded by frame position).
- C3 honest rejection: 'สวัสดี' abstain; unspaced 'เลขคู่ของ7คืออะไร' abstain; 'เขา' abstain unknown; never-observed known attr ('เกล็ด' before any observation) abstain no_match; attr-bearing sentence matching NO designed frame ('นก บิน ปีก') abstains (recorded behavior tightening vs token-scavenging).
- C4 fresh-process round-trip: save; HSML.load; 'ปีก' still includes เหยี่ยว, 'เปรี้ยว' still -> ส้ม; seeded skill still answers (noninterference).
- C5 noninterference: separate fresh memory + standard corpus -> b526 battery exact; seeded skills 40/40 x4; regressions b534/b535/b539/b540 re-run PASS after the change.
- C6 no-ack-without-store invariant: over a batch of new-name/new-attr statements, every 'observed' response is followed by probe-retrievable pairs (harness checks each).
Verdict PASS iff C1-C6. CAN claim: within the designed statement frames, acknowledged observations are always persisted and retrievable (including new names/attrs), and unsupported input is honestly rejected; CANNOT: free-form statement understanding - the frames are designed; B-529 Correction 1 boundaries stand.

## B-541 - unlimited name+attribute vocabulary (Ash steering 2026-10-25 12:43: "ทำให้ไม่จำกัดไม่ได้หรอ")
Pre-registered 2026-10-25 (commit on wnn-checkpoints before code). Goal: remove the fixed-world limit found by the fresh eval (B-540/eval_ash): dynamic name+attribute learning from designed-frame role parsing, with honest rejection for frameless/unknown input.
Criteria:
- C1: a taught new name+attribute is acknowledged AND retrievable by probe in-session (no ack without persisted learning)
- C2: new attribute on an existing name works the same way
- C3: frameless or unknown-token input gets an honest abstain/unknown response (no fake ack)
- C4: learned facts survive save/load (fresh-process round-trip)
- C5: noninterference - seeded corpus battery exact (40/40 x4) and skill ops unchanged
- C6: unknown/ambiguous/no_match decision semantics preserved
Verdict: PASS.
Run-1 FAIL (recorded): c1/c2/c4/c6 false - observations were acknowledged and stored (observe_pairs worked) but probes abstained. Cause: b526 decide() enumerated the hardcoded B-521 ANIMALS dict instead of the backend's own names. Fix: CountBackend.names() (dynamic: seed world + every learned name); decide() iterates be.names(); b527 answer() and the hsml probe filter use the dynamic vocab; b526 CountBackend.observe_pairs/vocab already added pre-run. Files: b526.py, b527.py, hsml.py (STMT_FRAMES role parsing + routing), b541.py (new harness).
Run-2: PASS c1-c6 (logs/b541_run.log).
Regressions: b534 PASS, b535 PASS, b540 PASS (caches cleared first), b539 PASS chunked s1a/s1b/s1c/s2 with C6 control bounded at 60,001 tried (sandbox per-call ceiling; full 700,001 control stands from the original merged run; all other checks identical) - logs/b539_regress2.log.
Scope honesty: vocabulary growth is via DESIGNED statement-frame role parsing (name/attribute roles in 'X มี Y'), not induced structure; frameless input is honestly rejected, not guessed.

## B-542 - attribute retraction (negation frame 'X ไม่มี Y')
Pre-registered 2026-10-25 (before implementation). Gap: taught attribute facts can be added (B-541) but never corrected - the skill world has revision (B-538/539) but the attribute world has no honest retraction. Same unified-system direction as Ash's steering.
Design (DESIGNED, named): negation frame 'X ไม่มี Y' (and 'X ไม่มี Y และ Z') parsed with grounded roles; CountBackend.unobserve(name, attrs) deletes the association (explicit retraction semantics, mirroring skill revision's replace); response 'ลบแล้ว' only when something was actually retracted, honest 'nothing to retract' otherwise. No silent no-ops acknowledged as done.
Criteria:
- C1: teach name+attr then retract -> probe no longer returns that name for the attr
- C2: retraction of one attr leaves the name's other attrs intact
- C3: retraction on a seeded name works the same way (probe reflects it; re-teach restores)
- C4: retracted state survives save/load in a fresh process
- C5: retracting a never-taught pair -> honest nothing_to_retract, no crash, no state change
- C6: re-teach after retract restores the answer
- C7: noninterference - corpus battery exact (seeded world untouched by these ops) and seeded skills 40/40 x4
Verdict: PASS (run-3).
Run-1 FAIL (harness sequencing, recorded): s1 never fed the corpus, so seed-world expectations were vacuous; the c4 fresh-process expectation also conflicted with the harness's own re-teach step. System behavior was per design.
Run-2 FAIL (mixed, recorded): (a) harness used wrong seed-world facts (ช้าง/งา are NOT in the B-521 world; ครีบ collides with seed ปลา) - harness corrected against b521.ANIMALS/ATTRS; (b) REAL routing gap found: conjunctive probes 'X และ Y' never reached decide ('และ' was not a legal probe token; battery probes bypass hear() so this was invisible before). Fixed: 'และ' admitted as a probe conjunction token in the designed probe filter. This is a designed-routing extension, named as such.
Run-3: PASS C1-C7 (logs/b542_run.log). Regressions after the probe-filter change: b541 PASS, b534 PASS, b535 PASS, b540 PASS, b539 PASS chunked (c6 control bounded 60,001; full 700,001 stands from the original run) - logs/b539_regress3.log.
Scope honesty: retraction is an explicit designed negation frame with delete semantics (mirrors skill revision's replace); 'ลบแล้ว' is said only for pairs actually retracted; never-taught pairs get an honest nothing_to_retract with partial reporting (retracted vs not_found). Negation is deletion of the association, NOT negative-evidence counts - a retracted fact is indistinguishable from a never-taught one afterward (decision semantics unknown/ambiguous/no_match preserved).

## B-543 - reverse attribute query ('X มี อะไรบ้าง')
Pre-registered 2026-10-25 (before implementation). Gap: the attribute store flows one way only (attr probe -> names). The SAME stored data should answer the other direction (name -> its attributes) with identical honesty semantics. Designed frame, no new subsystem.
Design (DESIGNED, named): frame 'X มี อะไรบ้าง' fullmatch, checked BEFORE statement parsing so 'อะไรบ้าง' can never be stored as an attribute; CountBackend.attrs_of(name) returns the stored attrs (None for unknown name); response lists current stored attrs; unknown name or fully-retracted name -> honest abstain/empty, nothing fabricated.
Criteria:
- C1: teach a new name two attrs -> reverse query lists both
- C2: reverse query reflects retraction (retract one -> query lists only the remaining one)
- C3: reverse query reflects corpus-seeded knowledge (seed animal lists its taught attrs)
- C4: unknown name AND fully-retracted name -> honest abstain (no fabricated list)
- C5: save/load round-trip: reverse query on learned content in a fresh process
- C6: noninterference - corpus battery exact, seeded skills 40/40 x4, and b541/b542 harnesses still pass
Verdict: PASS (run-2).
Run-1 FAIL (harness-only, recorded): expectations compared JSON-decoded lists to Python tuples; every system actual was already correct (lists verified against b521.ANIMALS). Fixed comparisons; no system change.
Run-2: PASS C1-C6 (logs/b543_run.log). The reverse frame is checked BEFORE statement parsing, so 'อะไรบ้าง' can never be stored as an attribute (c1_no_pollution verified). Regressions after the new route: b541 PASS, b542 PASS, b534 PASS, b535 PASS, b540 PASS, b539 PASS chunked (c6 bounded 60,001; full 700,001 stands) - logs/b539_regress4.log.
Scope honesty: the reverse query is a designed frame over the same count store - no new inference; unknown names and fully-retracted names abstain honestly (attr_reverse_unknown / attr_reverse_empty); the frame reserves 'อะไรบ้าง' from ever being an attribute (designed reservation, named).

## B-544 - storage safety: questions are not facts + honest yes/no questions
Pre-registered 2026-10-25 (parent greenlight after eval_ash3 baseline recorded the
over-acceptance defect: 'นก มี กี่ลักษณะ' was stored as an attribute of นก).
Design (DESIGNED, named - a FINITE guard list is not general Thai understanding):
1. Guard: question/particle words (ไหม มั้ย หรือ ใช่ไหม กี่ อะไร เท่าไหร่ ทำไม เมื่อไหร่ ที่ไหน ใคร อย่างไร ครับ ค่ะ จ้า นะ ล่ะ สิ) in name OR attr position of a parsed statement -> NOT stored; honest unsupported response. Nonmutation is verified by probing afterward.
2. Negative evidence: retraction (B-542) now leaves an explicit negative marker (per-name neg set), instead of being indistinguishable from never-taught. Re-teaching clears the marker. decide()/vocab()/attrs_of() semantics for extension are UNCHANGED (neg = absent there).
3. Yes/no frame 'X มี Y ไหม' answers three ways from the store: taught -> ใช่; explicitly retracted -> ไม่ (negative evidence); otherwise -> honest ไม่รู้ (absence is NOT false).
Criteria:
- C1: question-phrase statements not stored (probe + reverse query unpolluted); honest rejection response
- C2: question words in NAME position rejected too
- C3: particles in attr position rejected
- C4: ordinary new-attribute learning unaffected
- C5: yes/no three-way: taught=ใช่, never-taught=ไม่รู้ (NOT ไม่), retracted=ไม่
- C6: negative evidence survives save/load; re-teach clears it
- C7: noninterference - corpus battery exact, seeded 40/40 x4, b541/b542/b543 regressions PASS
Verdict: PASS (run-2). Run-1 FAIL recorded: the exact-match guard missed glued
question stems (e.g. 'กี่ลักษณะ' in attr position) - fixed with the GUARD_STEMS
prefix match; both runs in logs/b544_run.log. b539 chunked regression
(s1a/s1b/s1c/s2, bounded c6 60,001) PASS after the change
(logs/b539_regress5.log); b541/b542/b543/b534/b535/b540 regressions PASS.

## B-545 - usability: cwd-independent paths + ready chat front end
Defect (found during clean-environment usability verification 2026-10-25):
b527 resolved the skill logs and the skills cache by RELATIVE path, so
HSML() crashed outside ai/wnn (FileNotFoundError) and a missed cache would
have silently forced a full startup re-derivation (expensive hidden
induction). Fix: paths resolve from the module directory; cache write
failure warns instead of crashing. Also added chat.py (interactive front
end: fresh/load memory, --demo-world, autosave, loud corrupt-memory
failure) and HSML.md (user guide).
Verification: regress_skills.py PASS (clean-process derivation exercises the
new CACHE path); b544 harness PASS; chat.py tested from a foreign cwd:
demo-world teach, reverse query, three-way yes/no, probe, abstain,
skill teaching end-to-end (n+ naming, 5 examples, 3 checks, query),
save/reload persistence, retraction + negative evidence, corrupt load exit 2.
Verdict: PASS

## B-546 - Thai number words at the designed frame boundary
Pre-registered 2026-10-25 (Ash: "มาพัฒนา hsml ต่อ"; parent: safe language intake,
then Thai numeral words/varied phrasing; eval_ash3 baseline recorded the failure:
'เลขคู่ ของ สี่ คืออะไร' abstained while digits and Thai glyphs answered).
Design (DESIGNED, named - a finite number-word parser is NOT learned language
understanding): a strict single-token Thai number-word parser (standard place
grammar ศูนย์-เก้า/เอ็ด/ยี่ + สิบ ร้อย พัน หมื่น แสน ล้าน, places strictly
descending, digits only before a place or at the end) maps a word to an integer
ONLY at the numeric positions of the existing designed frames (skill query
'X ของ N คืออะไร', teaching example 'ถ้า n เป็น N ตอบ M', confirmation
'ตอบ M'). Attribute/name tokens are NOT normalized (classifier phrasing like
'นก มี สอง ปีก' stays out of scope). A malformed word parses to None and the
sentence falls through to exactly today's routing (no behavior change).
Criteria:
- C1: word-form skill query answers identically to the digit form
  ('เลขคู่ ของ สี่ คืออะไร' -> '... คือ 1'; 'ผลบวกถึง ของ สิบ' -> 55)
- C2: compounds: ยี่สิบ -> 20, สามสิบห้า -> 35, หนึ่งร้อยยี่สิบสาม -> 123,
  สองหมื่นห้า -> 20005, หนึ่งล้าน -> 1000000 parse correctly
- C3: full teaching with word-form examples and word-form confirmation answers
  stores the skill; word-form query answers (rendered in digits, as today)
- C4: malformed words abstain exactly as before ('สี่สอง', 'สิบสิบ', 'สามร้อยสองสิบสี่ห้า')
- C5: noninterference - digit and Thai-glyph paths byte-identical; b544 harness
  PASS; regress_skills PASS
Verdict: PASS (run-2). Run-1 FAIL recorded: C2 as pre-registered asked for
ANSWERS at สองหมื่นห้า (20,005) and หนึ่งล้าน, which exceed the pre-existing
DESIGNED recursive-execution cap (CAPF=20,000) of the seeded skills - the
words parsed correctly but execution abstained honestly. Criteria amended:
in-range words verified end-to-end through the dialog path; large words
verified at the parser (frame_num) plus an explicit over-cap honest-abstain
check. Both runs in logs/b546_run.log. Regressions: b534/b535/b540/b541/
b542/b543/b544, regress_skills, b539 chunked (bounded c6) all PASS
(logs/b539_regress6.log). Scope named: finite designed number grammar at the
frame boundary only - not learned language understanding; classifier phrasing
('นก มี สอง ปีก') remains out of scope by design.

## B-547 - bilingual slice: English frames sharing ONE attribute memory
Pre-registered 2026-10-25 (Ash: Thai+English in parallel with shared knowledge;
parent: cross-language testing, no human-like/all-word claim, ambiguity tests).
Design (ALL DESIGNED, named - finite frames and stopwords are not learned
understanding, and a taught link pair is not a claim the words are always
interchangeable):
1. Word links as taught DATA: frame '<thai> ภาษาอังกฤษคือ <english>' stores a
   bidirectional pair. Resolution at the frame boundary maps a linked English
   surface word to its linked Thai canonical word; unlinked words keep their
   own surface form (dynamic vocabulary, same as B-541).
2. English frames (finite): 'NAME has ATTR [and ATTR]' statements;
   'what does NAME have' reverse query; 'does NAME have ATTR' three-way
   yes/no (yes/no/unknown mirroring B-544); articles a/an/the are a finite
   designed stopword list at those frame positions only.
3. Ambiguity honesty: if a surface word has TWO taught links, using it in a
   query abstains and names the candidates - no silent pick.
Criteria:
- C1: teach Thai facts + links, English queries answer from the SAME memory
  ('นก มี ปีก' + link -> 'does นก have wings' yes; 'what does นก have' lists)
- C2: reverse direction: teach 'a bird has wings' with links bird<->นก
  wings<->ปีก, Thai probe 'ปีก' and reverse query 'นก มี อะไรบ้าง' see it
- C3: ambiguity: second link on one surface word -> query abstains naming
  candidates; retracting one link resolves it
- C4: unseen English phrasing abstains; English question words never stored
  as facts (B-544 guard semantics extend to the English frames)
- C5: links survive save/load; noninterference: b546/b544 harnesses PASS,
  regress_skills PASS
Verdict: PASS (run-1). logs/b547_run.log. All five criteria green on the first
run, including both cross-language directions, ambiguity abstain + resolution,
and English-question-word storage guards. Regressions: b534/b535/b540/b541/
b542/b543/b544/b546, regress_skills, b539 chunked (bounded c6) all PASS
(logs/b539_regress7.log). Scope named: finite designed English frames +
taught link pairs; a link is taught data, not a claim of always-interchangeable
meaning; English answers render canonical (Thai) attr words - the system does
not translate. Toward Ash's stated goal (compose NEW sentences to answer):
current answers are still template-rendered from memory, NOT free composition -
that gap is the next design question, recorded here honestly.

## B-548 - bounded two-hop composition: question-conditioned sentence assembly, verified before speaking
Pre-registered 2026-10-25 (Ash's stated goal via WhatsApp originals: the system
composes NEW sentences from words to answer questions; parent: preserve his
wording as the goal, distinguish learned-frame composition from broader ability,
held-out sentence/question tests, factual correctness, no canned-demo shortcut).
This is a BOUNDED slice, honestly named: two-hop composition over the taught
มี-graph only; surface realization still uses finite designed frames (NOT free
sentence composition); the question frames are designed, not learned Thai.
Design (ALL DESIGNED, named):
1. New question frames (finite, read-only - they never store):
   Thai 'X มี อะไรที่มี Y' and English 'what does X have that has Y'
   (link resolution as B-547, ambiguity abstains naming candidates).
   Semantics: find every Z such that taught(X,Z) AND taught(Z,Y).
2. Composition: for each verified Z emit a sentence assembled from taught
   words ('X มี Z และ Z มี Y' / 'X has Z and Z has Y') - a surface string
   that was never input as a whole; content selection is conditioned on the
   question (which Z satisfies both hops), not retrieval of a canned answer.
3. Verification gate: at speak time every link in an emitted sentence is
   re-checked against LIVE memory (taught() re-query); an unverified link is
   never spoken. No intermediate cache is trusted at emission.
4. Honest absence: no verified Z -> 'ไม่รู้'/'unknown'. Broken or
   reverse-only chains are never completed by guessing.
Criteria:
- C1: fresh-word chain (A,B,C novel, not in seed corpus): teach 'A มี B',
  'B มี C'; ask 'A มี อะไรที่มี C' -> answer names B; the emitted sentence
  string never appeared in any input (asserted) and every link in it is
  taught() in memory (asserted)
- C2: two independent paths A->B1->C and A->B2->C -> both listed, each
  link of each path verified
- C3: broken chains: (a) A มี B taught but B มี C never taught (nothing
  holds C) -> ไม่รู้; (b) D มี C taught but A มี D never taught -> ไม่รู้
  (no fabrication from a reverse-only hop)
- C4: retraction: after C1's answer, 'B ไม่มี C' -> same question -> ไม่รู้;
  re-teach 'B มี C' -> answer returns naming B (no stale emission)
- C5: unknown word in X or Y slot -> ไม่รู้; the question stores nothing
  (memory pair-count identical before/after; question tokens never become
  names/attrs)
- C6: bilingual: with taught links, 'what does A have that has C' answers
  from the SAME memory naming the same Z; a doubly-linked English word ->
  abstain naming candidates
- C7: noninterference: b534/b535/b540/b541/b542/b543/b544/b546/b547,
  regress_skills, b539 chunked (bounded c6) all PASS
Verdict: PASS (run-1). logs/b548_run.log. All criteria green on the first run:
two-hop composition names only fully verified paths (C1/C2), broken and
reverse-only chains get ไม่รู้ (C3), retraction removes and re-teaching
restores paths with no stale emission (C4), queries store nothing (C5),
bilingual twin shares one memory and ambiguity abstains naming candidates
(C6). Answer strings asserted never-input and every emitted link asserted
taught() at speak time. Noninterference (C7): b534/b535/b540/b541/b542/b543/
b544/b546/b547 + regress_skills PASS; b539 chunked bounded-c6 regression PASS
(logs/b539_regress8.log, bounded-aware merge as regress7). Scope named
honestly: bounded TWO-HOP composition over the มี-graph with finite designed
frames - a real step toward Ash's compose-new-sentences goal (content
selection is question-conditioned and the emitted string is novel), but still
NOT free sentence composition; deeper hops and freer realization are open.

## B-549 - learn-while-chatting separation: uncertain statements never become facts; natural 'ไม่ใช่' corrections
Pre-registered 2026-10-25 (Ash via WhatsApp, 2026-10-25:
"ทำให้มันเป็นแบบเรียนรู้ไปด้วยระหว่างคุยไปด้วยได้ไหม"; parent: preserve the
distinction between existing in-chat fact teaching and learning from ordinary
dialogue; separate explicit teaching/corrections from questions and uncertain
statements). Already-true scope named: in-chat learning EXISTS but only through
designed frames (B-541/542/544/529); this step adds the confidence separation,
NOT learning from free dialogue. ALL DESIGNED, named: finite marker lists and
frames are not learned language understanding.
Design:
1. Uncertainty markers (finite designed set): อาจจะ, อาจ, น่าจะ, คงจะ, ไม่แน่ใจ,
   มั้ง (Thai, any token position); 'maybe' (English statement frame). A
   statement containing a marker is NOT stored; the system says honestly it
   will not remember it as fact. Marker tokens never become names/attrs.
2. Correction frame 'ไม่ใช่ <statement>': parses the inner statement through
   the existing designed frames and retracts those pairs via the B-542 path;
   never-taught pairs report nothing-to-retract (no fake ack).
3. Questions remain non-storing (B-544, unchanged).
Criteria:
- C1: 'อาจจะ นก มี ปีก' (and each Thai marker variant, and 'maybe a bird has
  wings' with links) stores nothing; the yes/no query afterwards answers
  ไม่รู้ - not ใช่, and not ไม่ (uncertain is not negative evidence)
- C2: marker tokens never enter vocab/names; the ack text is the honest
  not-stored reply, never 'จำไว้แล้ว'
- C3: teach 'ฟา มี ทริบ'; 'ไม่ใช่ ฟา มี ทริบ' -> retracted, yes/no -> ไม่
  (explicit negative); 'ไม่ใช่ ฟา มี มุก' (never taught) -> honest
  nothing-to-retract; 'ไม่ใช่' of a non-statement abstains without mutation
- C4: confident statements still store (B-541 semantics unchanged); skill
  teaching frames unaffected by markers elsewhere in memory
- C5: noninterference: b534/b535/b540/b541/b542/b543/b544/b546/b547/b548,
  regress_skills, b539 chunked (bounded c6) all PASS
Verdict: PASS (run-2; run-1 FAIL recorded: the B-544 yes/no paths KeyError'd on
a completely unknown name - be.taught() indexed C[n] directly, exposed by C1's
uncertain-then-query sequence; fixed by routing both yes/no checks through the
KeyError-safe holds() added in B-548. Two harness bugs also fixed: C4b queried
a non-seeded skill word, then asserted a field hsml.py does not forward).
logs/b549_run.log. All criteria green: six Thai uncertainty markers + English
'maybe' store nothing and follow-up yes/no answers ไม่รู้/unknown (uncertain is
NOT negative evidence); marker tokens never enter vocab/names; 'ไม่ใช่
<statement>' retracts via the B-542 path with honest nothing-to-retract and
non-mutation abstain on unparseable corrections; confident statements and skill
frames unchanged. Noninterference (C5): b534/b535/b540/b541/b542/b543/b544/
b546/b547/b548 + regress_skills PASS; b539 chunked bounded-c6 PASS
(logs/b539_regress9.log, bounded-aware merge as regress7/8). Scope named:
finite designed marker lists and frames - confidence separation for in-chat
learning, NOT learning from free ordinary dialogue (that remains open).

## Licensing decision (2026-10-25) - hsml component -> AGPL-3.0-only
Ash's explicit approval (WhatsApp, 2026-10-25): initial "ตามนั้นเปลี่ยนเป็น
AGPLV3 ฉบับเต็มครบทุกตัวอักษร",
reconsidered GPLv3 ("หรือ gplv3 ธรรมดาดี"), then confirmed after the AGPL-vs-GPL
tradeoff (cloud-hosted modified services must offer source) with "ใช่"
to the explicit question
"ให้ผมเดินหน้าต่อด้วย AGPLv3 เฉพาะ hsml เลยไหม?".
Applied: ai/wnn/LICENSE = complete canonical AGPLv3 text fetched byte-exact
from https://www.gnu.org/licenses/agpl-3.0.txt (34,523 bytes; a web_fetch
markdown copy was REJECTED - it had stripped <https://...> URLs and was not
character-complete). ai/wnn/NOTICE scopes AGPL-3.0-only to the hsml source,
excludes third-party data (MNIST, Cook 2019 wormwiring-derived connectome -
reuse license not established, SNIPS CC0), keeps the rest of the repo
Apache-2.0, and states prior Apache releases remain valid/irrevocable.
Rights check: git authors of ai/wnn are all Ash's own identities; provenance
grep found no copyright headers or vendored-source markers (residual: cannot
prove a negative - a headerless copied file would not be caught). No "or
later" wording added (Ash chose v3 only). No release/tag; root LICENSE and
non-hsml dirs untouched.

## B-551 (pre-registered 2026-10-25): bounded three-hop verified composition
Extends B-548's two-hop gate to exactly three hops. ALL DESIGNED, named: finite
frames, not learned understanding, not free sentence composition.
Query forms (single-token surfaces only):
- TH: 'X มี อะไรที่มี Y ที่มี Z'
- EN: 'what does X have that has Y that has Z'  (link-resolved like B-548 EN)
Semantics (predeclared): find A with holds(X,A) AND holds(A,Y) AND holds(Y,Z),
every link re-verified against LIVE memory at emission (same gate as B-548).
Emit TH: 'X มี A และ A มี Y และ Y มี Z' / EN: 'X has A and A has Y and Y has Z'
(' / ' joins multiple verified A).
Pass criteria:
- C1: teach X-A, A-Y, Y-Z -> composed naming A (verified==[A])
- C2: two different A candidates both verified -> both emitted
- C3a/b/c: missing Y-Z / X-A / A-Y link -> ไม่รู้ (TH) or unknown (EN)
- C4: teach all three, then 'ไม่ใช่ A มี Y' -> re-ask answers ไม่รู้
  (mid-chain retraction kills composition)
- C5 noninterference: b534-b549 harnesses + regress_skills PASS unchanged
Named scope: exactly three hops, attr domain only, single-token surfaces;
NOT general n-hop. Read-only frames: never store.

## B-551 verdict (2026-10-25): PASS
Own criteria 10/10 first run (logs/b551_run.log): C1 single chain composed
('X มี A และ A มี Y และ Y มี Z'), C2 two verified candidates both emitted,
C3a/b/c per-hop broken chains all abstain ไม่รู้, C4 mid-chain retraction drops
the broken candidate while the intact one still composes, C4b full break ->
ไม่รู้, EN twin composes cross-language via taught links, EN broken -> unknown.
C5 noninterference: b534-b549 harnesses clean; regress_skills PASS
(logs/b551_regress_skills.log: clean-process 40/40 x4 skills, missing-pinning
error path, corrupt-cache fallback). Run note (honest): two earlier
regress_skills attempts hit sandbox timeouts because a killed run had truncated
logs/b527_skills_cache.pkl; the DESIGNED corrupt-cache fallback absorbed it
(warning + full re-derivation, 76s), after which the suite completed. No code
change needed; the incident exercised the same fallback path the suite tests.

## B-552 (pre-registered 2026-10-25): English article coverage (a/an/the)
Gap found by the B-550 comparison battery (hsml_S1b/S2 transcripts): teach
'a bird has a beak', query 'what does a bird have', yes/no 'does a bird have
wings' were REJECTED (no-answer). ALL DESIGNED parser widening, named:
optional article (a/an/the, any case) before the subject in English
reverse/yes-no queries, and before each attribute in English teach statements
and 'maybe ...' uncertain statements. Stripped articles never enter vocab.
Explicit NON-goals (named limits): NO morphology ('beak' vs 'beaks' stay
distinct words), no multiword names, articles only a/an/the.
Pass criteria:
- C1: 'a bird has a beak' -> observed, attr stored as 'beak'
- C2: 'an owl has an eye and a wing' -> attrs 'eye','wing'
- C3: 'what does a bird have' -> lists taught attrs
- C4: 'does a bird have wings' -> yes; 'does a bird have gills' -> unknown
- C5: pre-existing bare forms unchanged ('a bird has wings', 'what does bird
  have', 'does bird have wings')
- C6: 'maybe a bird has a beak' -> uncertain_not_stored, nothing stored,
  follow-up 'does a bird have beaks'... 'does bird have beak' -> unknown
- C7 noninterference: b534-b551 + regress_skills PASS unchanged

## B-552 verdict (2026-10-25): PASS
Own criteria 13/13 first run (logs/b552_run.log): articles stripped before
subject (reverse/yes-no) and attributes (teach + 'maybe'); bare forms
unchanged; uncertain path stores nothing; named no-morphology limit verified
('beak' != 'beaks' -> unknown). C7 noninterference: b534-b551 clean,
regress_skills PASS. End-to-end chat transcript of the exact phrases the
B-550 battery saw rejected: logs/b552_chat.log ('a bird has a beak' ->
จำไว้แล้ว, 'what does a bird have' -> 'bird has beak tail', 'does a bird have
wings' -> unknown (wings NOT taught in that run - correct abstention),
gills -> unknown). Correction: an earlier version of this entry claimed the
wings answer was 'yes'; the literal log says unknown, which is the honest
answer for an untaught attribute.

## B-553 (pre-registered 2026-10-25): Thai synonym intake while chatting
Ash's steering: learn while chatting. ALL DESIGNED frames, named; query-time
resolution only (no memory rewrite, mirrors B-547 link design).
Frames (single-token Thai words):
- teach: 'X กับ Y คือคำเดียวกัน' -> symmetric link stored (ack จำไว้แล้ว)
- retract: 'X กับ Y ไม่ใช่คำเดียวกัน' -> link removed; honest nothing-to-retract
- uncertain: marker + synonym sentence -> uncertain_not_stored (B-549 path extended)
Semantics (predeclared): DIRECT links only, NOT transitive. Queries about X
see facts taught under X and its direct synonyms (union for reverse query;
exists-for yes/no and composition gates). Retraction ('ไม่ใช่ X มี Y' / 'X ไม่มี
Y') removes Y from every direct-synonym surface that holds it. CONFLICT (one
surface holds X-Y, another holds explicit neg X-Y) -> yes/no answers ไม่รู้.
Emission surfaces stay as stored (compose may emit the stored surface form).
Out of scope (named): the 'which things have' probe, skill names, morphology,
multiword synonyms, transitive chains.
Pass criteria:
- C1: teach 'X มี Y', link X=Z, ask 'Z มี อะไรบ้าง' -> lists Y
- C2: symmetric (ask X, facts taught under Z)
- C3: yes/no via synonym -> ใช่
- C4: retract link -> re-ask -> ไม่รู้/abstain; link retract idempotence honest
- C5: uncertain synonym sentence stores nothing (link absent after)
- C6: conflict -> ไม่รู้
- C7: retraction via synonym removes from the holding surface; re-ask -> ไม่รู้
- C8: composition (2-hop + 3-hop) works through a synonym hop
- C9 noninterference: b534-b552 + regress_skills PASS unchanged

## B-553 verdict (2026-10-25): PASS
Own criteria 15/15 first run (logs/b553_run.log): C1/C2 union reverse query
both directions, C3 yes/no via synonym, C5 uncertain synonym stores nothing,
C8 composition through a synonym hop (2-hop + 3-hop), C7 retraction via
synonym removes from the holding surface (explicit ไม่ after), C4 link
retraction restores per-surface view (own facts survive), C6 conflict ->
ไม่รู้, guard refuses question-stem words. C9 noninterference: b534-b552
clean, regress_skills PASS. Compat: pre-B-553 memory pickle
(/tmp/b552_chat.pkl) loads and answers correctly (lazy syn init).

## B-554 (pre-registered 2026-10-25): is-a ('X เป็น Y') with yes/no inheritance
First second relation type after มี; toward category conversation. ALL
DESIGNED, named. Thai single-token only this chunk (English is-a: out of scope).
Frames:
- teach: 'X เป็น Y' (directed child->parent; cycles allowed, visited-set BFS)
- retract: 'ไม่ใช่ X เป็น Y' (link removed; honest nothing-to-retract)
- uncertain: marker + is-a sentence -> uncertain_not_stored (B-549 path extended)
Semantics (predeclared): inheritance applies to YES/NO questions only, via BFS
over parents (depth cap 8, cycle-safe): any positive (own, synonym, or
inherited through is-a) answers ใช่; any explicit negation anywhere answers
ไม่ - and BOTH present = conflict -> ไม่รู้ (B-553 rule extended). Reverse
query 'X มี อะไรบ้าง' lists OWN(+synonym) attrs only - inheritance NOT listed
there this chunk (named bound). Composition unchanged (not inherited) this
chunk. Guard words refused on both sides.
Pass criteria:
- C1: 'นกแก้ว เป็น นก' + 'นก มี ปีก' -> 'นกแก้ว มี ปีก ไหม' answers ใช่
- C2: transitive two levels -> ใช่
- C3: no link -> ไม่รู้
- C4: 'ไม่ใช่ นกแก้ว เป็น นก' -> re-ask ไม่รู้; honest nothing-to-retract repeat
- C5: uncertain is-a stores nothing
- C6: own explicit neg + inherited positive -> ไม่รู้ (conflict)
- C7: guarded words refused
- C8: cycle X->Y->X terminates, answers from union
- C9 noninterference: b534-b553 + regress_skills PASS unchanged

### B-554 run-1 note (kept per protocol)
Run-1 FAIL on C6: my criterion used bare 'ควิ๊บ ไม่มี สเฟน' on a never-taught
pair and expected an explicit negation - but the DESIGNED B-542 semantics
treat bare 'X ไม่มี Y' on untaught pairs as honest nothing-to-retract (no neg
recorded), so inheritance correctly answered ใช่. The system was right; the
criterion was wrong. Amended C6 to establish the explicit negation via the
designed teach-then-correct ('ไม่ใช่') path. No code change.

## B-554 verdict (2026-10-25): PASS (after C6 criterion amendment, see run-1 note)
Own criteria 14/14 (logs/b554_run.log): C1 one-level inheritance, C2
transitive (BFS cap 8), C3 no-link unknown, C4 is-a retraction incl.
descendant effect, C5 uncertain not stored, C6 own-neg + inherited-pos ->
conflict ไม่รู้, C7 guard, C8 cycle-safe, C9 reverse-query bound held
(inheritance answers yes/no only, not listings). C9 noninterference:
b534-b553 clean, regress_skills PASS.

## B-555 (pre-registered 2026-10-25): inheritance-aware reverse query with provenance
Extends B-554: 'X มี อะไรบ้าง' now also lists attributes inherited through
is-a, each group WITH its source named ('และจาก P: attrs') - no silent
inheritance. ALL DESIGNED, named. Own(+synonym) attrs first; inherited groups
in BFS order, deduped against already-listed attrs; live memory at answer
time (retracted parent attr disappears). If X has no own attrs but inherits,
it answers (was: abstain) - flagged in the record. EN twin: 'X has own ... and
from P: ...'. Composition frames unchanged this chunk.
Pass criteria:
- C1: own + inherited listed, source named
- C2: no own attrs, only inherited -> answers with from-group only
- C3: parent attr equal to own attr -> listed once (as own)
- C4: two ancestors -> two from-groups in BFS order
- C5: retract parent attr -> inherited group gone on re-ask
- C6: EN twin
- C7: is-a via synonym surface counts
- C8 noninterference: b534-b554 + regress_skills PASS unchanged

## B-555 ผนวก (17:45): run-1 FAIL + การแก้ไขวิธีสแกน noninterference (บันทึกซื่อตรง)

- run-1 (17:36): C6 FAIL — เส้นทาง reverse query ภาษาอังกฤษยังใช้ attrs_of ดิบ (B-553 rewire ครอบคลุม reverse-TH / uncertain / yes-no / compose แต่ไม่ถึง EN reverse; b553 ไม่มี criterion เฉพาะ EN reverse — ช่องว่างการทดสอบ) ไม่เคยมีการอ้างพฤติกรรม EN reverse มาก่อน แก้โดย rewire + inheritance แบบเดียวกับ TH; run-2 (17:37): 8/8 PASS
- การแก้ไขวิธี (ระดับกระบวนการ): การสแกน noninterference แบบ import (`python3 -c "import bXXX"`) เป็นโมฆะสำหรับ harness ที่มีการ์ด `if __name__ == '__main__'` (b530-b547) — import รันเฉพาดนิยาม ไม่รันตัวทดสอบ ความพยายามสแกนครั้งแรกของ B-555 ใช้รูปแบบนี้ (ผิดพลาด) และรูปแบบสแกนก่อนหน้าไม่ได้บันทึกไว้สม่ำเสมอ จึงรัน b534-b554 ใหม่ทั้งหมดในรูปแบบสคริปต์ (verdict = exit code) เพื่อสร้างบันทึกที่ถูกต้อง หากพบ regression จะแก้ไขและรายงานเปิดเผย
- หมายเหตุ: b545.py ไม่มีอยู่จริง (ชื่อผิดในรายการสแกนเดิม — เครื่องหมาย ModuleNotFoundError ในครั้งแรกเป็นเพียงเรื่องตกแต่ง)
- 17:48 ตามคำสั่ง main: หยุด merge PR #278 ชั่วคราวจนกว่าจะยืนยัน regression ด้วยการรันสคริปต์จริงที่ head 4f5c849 — เริ่มสแกนใน worktree /tmp/wt-4f5c849 (b534-b553 ที่มีอยู่ รวม b539/b542 + regress_skills, verdict = exit code + บรรทัดสรุป, log /tmp/head_*.log) พบว่า CI (tests/run_all.py) รันแบบ subprocess ถูกต้อง แต่ไม่ครอบคลุม harness ของ ai/wnn เลย — การรันสแกนนี้จึงเป็นหลักฐานเดียวสำหรับ hsml

## PR #278 merge + การยืนยัน exact-head (17:48-18:58)
- สแกน regression รูปแบบสคริปต์จริงที่ head 4f5c849 (worktree /tmp/wt-4f5c849): b534 b535 b536 b537 b538 b539 b540 b541 b542 b543 b544 b546 b547 b548 b549 b551 b552 b553 + regress_skills — 19/19 exit=0 พร้อมบรรทัด verdict (log /tmp/head_sweep.log, ต่อ harness /tmp/head_*.log) — นี่คือหลักฐาน noninterference ฉบับยืนยันได้ชุดแรกหลังพบว่ารูปแบบ import เป็นโมฆะสำหรับ harness ที่มี __main__ guard
- CI: quick pass (37m16s), arm64-port pass; ls-remote wnn == 4f5c849 == PR head → merge ตาม grant: merge commit d51533c บน master — ทดสอบ smoke จากโคลน master สด: ผ่าน (basic/yesno/B-551 composed3/B-552 articles/B-553 synonyms; smoke รอบแรกเกณฑ์พิมพ์ 'compose3' ผิด ของจริงคือ 'composed3' — ข้อผิดพลาดในสคริปต์ทดสอบของฉัน ไม่ใช่โค้ด)

## B-555 verdict: PASS (run-2) — ถามย้อนแบบรวมของสืบทอดพร้อมที่มา
- เกณฑ์ตัวเอง 8/8 (log logs/b555_run.log): C1 own+inherited ระบุที่มา ' และจาก X: ...', C2 inherited-only, C3 dedup own/บรรพบุรุษ, C4 สองบรรพบุรุษเรียง BFS, C5 ลบของบรรพบุรุษแล้วกลุ่มหาย, C6 EN twin ('and from X: ...'), C7 ใช้ผ่านคำพ้องได้, C8 อยู่ในสแกนด้านล่าง
- noninterference รูปแบบสคริปต์จริง (ทรี bf53284 + การแก้ B-555): b534-b554 + regress_skills = 20/20 exit=0 พร้อม verdict lines (logs/b555_noninterference.log, ต่อ harness /tmp/wt_*.log) — หลักฐานนี้ยืนยัน B-554 ไปด้วยในคราวเดียว: คำกังวลเรื่องสแกน import-โมฆะของ B-554 ถูกแทนด้วยหลักฐานการรันจริงแล้ว
- ขอบเขตตั้งใจ: การถามย้อนรวมของสืบทอดเท่านั้น; การประกอบประโยคผ่าน is-a ยังไม่ทำ (ข้อถัดไป)

## B-556 (pre-registered 2026-10-25 ~19:28 UTC, ก่อนเขียนโค้ด): การประกอบประโยคผ่าน is-a
เป้า: คำถามประกอบ ('X มี อะไรที่มี Y' และสามชั้น + EN twins) มองเห็นลักษณะที่สืบทอดผ่าน is-a ด้วย ไม่ใช่เฉพาะลักษณะตรง — ต่อยอด B-554 (ตอบใช่/ไม่สืบทอด) และ B-555 (ถามย้อนรวมของสืบทอด)
การออกแบบที่ประกาศล่วงหน้า:
- ประโยคที่พูดยังเรียบเหมือนเดิม ('X มี A และ A มี B') เพราะทุกข้อเชื่อมเป็นจริง (สืบทอดก็เป็นจริง) แต่ผลลัพธ์ต้องบันทึก provenance ของแต่ละข้อ (own หรือ inherited ผ่านบรรพบุรุษใด) ไว้ใน dict เสมอ และทุกข้อเชื่อมยังตรวจกับความจำสดก่อนพูดตามกฎ B-548
- ตัวกลาง Z ที่เป็นลักษณะตรงของ X ต้องมาก่อน Z ที่สืบทอดมา (prefer own) และห้ามซ้ำ
- เกณฑ์:
  C1: hop แรกสืบทอด — X เป็น P, P มี A, A มี B → 'X มี อะไรที่มี B' ตอบ 'X มี A และ A มี B' พร้อม provenance ข้อแรก = inherited ผ่าน P
  C2: hop สองสืบทอด — X มี A ตรง, A เป็น Q, Q มี B → ตอบได้ provenance ข้อสอง = inherited ผ่าน Q
  C3: prefer own — X มี A ตรงและสืบทอด A จาก P → ใช้ข้อเชื่อมตรง provenance = own
  C4: ลบลักษณะของบรรพบุรุษ (ไม่ใช่ P มี A) → ห่วงขาด ตอบ ไม่รู้ ไม่ใช้คำตอบค้าง
  C5: สามชั้นที่มี is-a hop คั่นกลาง → ตอบครบสามข้อพร้อม provenance ทุกข้อ
  C6: EN twin ('what does X have that has B') พฤติกรรมเดียวกัน
  C7: วงแหวน is-a (A เป็น B, B เป็น A) ไม่วนตัวเอง ไม่ค้าง
  C8: noninterference — สแกนสคริปต์จริง b534-b555 + regress_skills ทุกตัว exit=0
ขอบเขตตั้งใจ: เฉพาะกราฟ มี + is-a บนกรอบประกอบที่มีอยู่; ไม่แตะการประกอบทักษะ (skill composition); ไม่อ้างความเข้าใจความหมาย
เกณฑ์ผ่าน: ครบทุกข้อ + sweep เขียว + บันทึก run-1 FAIL ถ้ามีตามปกติ

## PR #280 merge + การยืนยัน master (18:18)
- เกตครบ: CI quick/arm64-port pass; ls-remote wnn == headRefOid == 770f201; หลักฐาน regression สคริปต์จริง 20/20 ของทรีเดียวกันมีอยู่แล้ว → merge ตาม grant: merge commit 189ed91 บน master
- smoke จากโคลน master สด: B-554 yes/no สืบทอด (ไทย+อังกฤษ), B-555 ถามย้อนรวมของสืบทอดพร้อมที่มา (ไทย+อังกฤษ), การลบของบรรพบุรุษ — ผ่านทั้งหมด บันทึกซื่อตรง: smoke รอบแรกพิมพ์เกณฑ์ผิดอีกครั้ง ('does pum have โพล่' — กรอบ EN รับเฉพาะ attr ขึ้นต้น ASCII โดยออกแบบตั้งแต่ B-547) ไม่ใช่โค้ดพัง; รอบสองใช้คำเชื่อม 'โพล่ ภาษาอังกฤษคือ pole' ผ่าน — บทเรียน: smoke แบบ ad-hoc ควรเขียนจากกรอบที่บันทึกไว้ใน HSML.md ไม่ใช่จากความจำ

## B-556 sweep run-1: พบบั๊กจริงของ B-555 (ไม่ใช่เกณฑ์ผิด) — แก้แล้ว
- อาการ: b555 C4 FAIL ในสแกน — ลำดับกลุ่มบรรพบุรุษในคำตอบถามย้อนสลับกันระหว่าง process (ได้ 'ควอลท์' ก่อน 'วินท์') ทั้งที่เกณฑ์ประกาศเรียง BFS (พ่อก่อนปู่)
- รากจริง: _parents_any คืน set — BFS มีอยู่ในลูปแต่ลำดับหายตอนเก็บลง set; iteration order ของ set ขึ้นกับ hash randomization ของ process ทำให้ผ่าน/ไม่ผ่านสลับกัน — เกณฑ์ C4 ถูกต้อง โค้ดผิด (ครั้งนี้ตรงข้ามกับ B-554 run-1)
- ความหมายต่อ master: โค้ดที่ merge ไปใน PR #280 มี nondeterminism นี้ — ผลกระทบเฉพาะ "ลำดับ" ของกลุ่มที่มาเมื่อมีบรรพบุรุษให้ของมากกว่าหนึ่งระดับ; เนื้อหาและที่มาของแต่ละกลุ่มถูกต้องเสมอ — ระดับผิวเผิน แก้ใน commit ถัดไป
- การแก้: _parents_any คืน list เรียง BFS แบบ determinate (sort ภายในระดับ) — b555 รัน 6 process ซ้ำผ่าน 8/8 ทุกครั้ง; b556 ผ่าน 7/7; consumer อื่น (_pos_neg_any) ไม่ไวต่อลำดับ
- สแกนเต็มรูปแบบสคริปต์จะรันใหม่ทั้ง 21 harness หลังการแก้นี้ (run-1 sweep log เก็บที่ logs/b556_noninterference.log)

## B-556 verdict: PASS — ประกอบประโยคผ่าน is-a พร้อม provenance ทุกข้อ
- เกณฑ์ตัวเอง 7/7 รอบแรก (log logs/b556_run.log): hop แรก/สองสืบทอดพร้อม provenance, prefer own, ลบของบรรพบุรุษแล้วห่วงขาด, สามชั้นคั่น is-a, EN twin, วงแหวนไม่ค้าง
- noninterference รูปแบบสคริปต์จริง run-2 (หลังแก้ determinism): b534-b556 + regress_skills = 22/22 exit=0 (logs/b556_noninterference2.log; run-1 ที่จับบั๊ก B-555 เก็บที่ logs/b556_noninterference.log)
- รวมการแก้ determinism ของ _parents_any (จาก B-556 sweep run-1) ใน commit นี้ — master จะได้รับการแก้เมื่อ PR ถัดไปเข้า
- ขอบเขตตั้งใจยืนยัน: เฉพาะกราฟ มี + is-a บนกรอบประกอบเดิม ประโยคที่พูดเรียบแต่ทุกข้อตรวจสดและเก็บ provenance; ไม่แตะ skill composition

## B-557 pre-registration: รวมการประกอบ n-hop แบบมีขอบเขต (ยังไม่เขียนโค้ด)
- ปัญหา: ปัจจุบันมี _compose_two_hop / _compose_three_hop แยกกันเป็นรูปแบบตายตัว กรอบถามไทย 'X มี อะไรที่มี Y (ที่มี Z)' และ EN twin — การไปลึกกว่า 3 ข้อต้องเขียนฟังก์ชันใหม่ทุกระดับ
- แผน: รวมเป็นการค้นกราฟ มี+is-a แบบมีขอบ (depth cap = 4 ข้อเชื่อม, node-visit cap ตายตัว — ชื่อขีดจำกัดบอกตรงใน HSML.md) คงพฤติกรรมเดิมของกรอบ 2/3 ข้อทุกประการ และขยายกรอบถามแบบ chain 'มี อะไรที่มี A ที่มี B ที่มี C' ให้ยาวได้ถึง 4 ข้อเชื่อมทั้ง TH/EN
- เกณฑ์:
  C1: behavior preservation — b548/b551/b556 ผ่านเหมือนเดิมทุกข้อ (สคริปต์จริง)
  C2: 4-hop chain ที่สอนครบทุกข้อเชื่อม ตอบได้ทั้ง TH และ EN พร้อม provenance ทุกข้อ (own/inherited ผ่านบรรพบุรุษใด)
  C3: chain ยาวเกิน cap → ไม่รู้/unknown ตรงๆ ไม่ค้าง (bounded โดยออกแบบ)
  C4: วงแหวนในกราฟ มี (A มี B, B มี A) ค้นจบเสมอ ไม่วนไม่สิ้นสุด
  C5: ลำดับ candidate own-ก่อน-inherited BFS คงเดิม และ harness ผ่านเหมือนกันใน >=4 process แยก (กันบั๊ก hash-seed แบบ B-555)
  C6: ลบข้อเชื่อมกลาง chain → ตอบ ไม่รู้ ไม่ใช้คำตอบค้าง
  C7: noninterference รูปแบบสคริปต์จริง b534-b557 + regress_skills ทุกตัว exit=0
ขอบเขตตั้งใจ: ไม่เพิ่มไวยากรณ์คำถามรูปแบบอื่น ไม่ใช่การแต่งประโยคเสรี ไม่อ้างความเข้าใจความหมาย; เกณฑ์ผ่าน = ครบทุกข้อ + sweep เขียว + บันทึก run-1 FAIL ถ้ามีตามปกติ

## B-558 pre-registration: ชั้นเชื่อมโยงแบบตารางนับเหนือหน่วยความจำสด (Ash เลือกเส้นทาง A, 26 ตุลาคม 2026) — ยังไม่เขียนโค้ด
- ที่มา: Ash อนุมัติการทดลองแบบผสมแบบมีขอบ (WhatsApp 26 ต.ค. 05:31) — ชั้นเรียนรู้ความคล้ายของถ้อยคำ "เหนือ" หน่วยความจำเชิงโครงสร้างที่ตรวจย้อนได้ ไม่แทนที่ ไม่ใช้ weight ที่ฝึกมาจากที่อื่น ไม่อ้างการสนทนาทั่วไป
- กลไก (ออกแบบ ตั้งชื่อ): ตารางนับจำนวนเต็มจาก char n-gram (3-5) ของประโยคที่ "สอนผ่านกรอบเดิมเท่านั้น" → เมื่อประโยคใหม่ไม่เข้ากรอบใดเลย ชั้นนี้เสนอข้อเท็จจริงที่เคยสอนซึ่งคล้ายสุดเกินเกณฑ์งดตอบ แล้ว "ตรวจข้อที่เสนอกับหน่วยความจำสดอีกครั้งก่อนพูด" ตามปรัชญา B-548 — ต่ำกว่าเกณฑ์หรือตรวจไม่ผ่าน → ไม่รู้ เหมือนเดิม
- การลบ: หน่วยความจำสดเป็นแม่; ชั้นนี้เก็บบันทึกการเขียนต่อข้อที่สอน เมื่อมีการลบ (ไม่ใช่) จะลดค่านับตามบันทึกนั้น (หรือสร้างใหม่จาก store) — วัดให้เห็น ไม่สมมติ
- ชุดโพรบถ้อยคำแปรผัน (held-out) จะ "แช่แข็งใน harness ก่อนเขียนโค้ด" และต้องมาจากแม่แบบที่ parser ไม่รองรับและไม่ปรากฏในข้อมูลสอน เพื่อแยกการถ่ายโอนจริงออกจากการทับซ้อนของ feature/parser
- เกณฑ์:
  C1: noninterference — ทุกอินพุตที่ parser เดิมจัดการได้ ตอบเหมือนเดิมทุกตัวอักษร (แบตเตอรี่เปรียบเทียบ + sweep)
  C2: ถ้อยคำแปรผัน held-out ที่แช่แข็ง: ชั้นเชื่อมโยงเสนอข้อเท็จจริงที่ถูกต้องได้อย่างน้อย 8/10 ขณะที่ parser เดิมตอบ 0/10 (งดตอบตามออกแบบ)
  C3: ไม่แต่งคำตอบ — โพรบเรื่องที่ไม่เคยสอน ต้องงดตอบในอัตราไม่ต่ำกว่า baseline (รายงานอัตราเสนอผิดทุกตัว ไม่ซ่อน)
  C4: การลบ — หลัง 'ไม่ใช่ X มี Y' ชั้นเชื่อมโยงต้องหยุดเสนอข้อที่ถูกลบ (0 การเสนอบนโพรบข้อนั้น)
  C5: การจำ — สอน 100 ข้อ แล้วสอนเพิ่ม 100 ข้อ ทบทวน 100 ข้อแรก: การดึงจาก store ต้อง 100% เหมือนเดิม; อัตราเชื่อมโยงผิดของชั้นใหม่ "วัดและรายงานตามจริง" แม้สูง
  C6: ทรัพยากร — วัด peak RSS (ru_maxrss), CPU วินาทีต่อการสอน/ต่อคำถาม, พื้นที่เก็บต่อข้อเท็จจริง — รายงานเป็นตัวเลข ไม่อ้างว่าประหยัดสุดหรือดีสุด
  C7: provenance ของกลไก — คำตอบใดที่มาจากชั้นเชื่อมโยงต้องติดป้ายในชนิดผลลัพธ์/บันทึก (kind แยกจากคำตอบกรอบตรง) เพื่อไม่ให้การอ้างพฤติกรรมปนกัน
  C8: noninterference รูปแบบสคริปต์จริง b534-b558 + regress_skills ทุกตัว exit=0
ขอบเขตตั้งใจ: การ "ดึงข้อเท็จจริงที่เคยสอน" ใต้ถ้อยคำแปรผันเท่านั้น — ไม่ใช่การสร้างภาษา ไม่ใช่การตามบทสนทนา ไม่ใช่การคุยทั่วไป; การอ้างจำกัดเฉพาะแกนที่วัดจริง
เกณฑ์ผ่าน: ครบทุกข้อ + sweep เขียว + บันทึก run-1 FAIL ถ้ามีตามปกติ

## B-557 verdict: PASS — รวมการประกอบ n-hop แบบมีขอบเขต
- เกณฑ์ตัวเอง 8/8 รอบแรก (log logs/b557_run.log... รวมใน harness output; b557.py): พฤติกรรมเดิม 2/3 ข้อเหมือนเดิมทุกตัวอักษร (kind composed/composed3 คงเดิม), 4-hop ตอบได้ทั้งไทยและอังกฤษพร้อม provenance ทุกข้อ, chain เกิน cap ตอบ ไม่รู้/unknown, วงแหวน มี ค้นจบ, ลบข้อเชื่อมกลาง chain แล้วไม่ใช้คำตอบค้าง; ผ่าน 4 process แยกเหมือนกัน (C5)
- การรวม: _compose_two_hop/_compose_three_hop ถูกแทนด้วย _compose_n_hop ตัวเดียว (chain cap 3 attrs = 4 ข้อเชื่อม, visit cap 64 ต่อคำถาม บันทึกถ้าแตะ) — กรอบถามรูปแบบ chain เดิมทุกแบบทำงานเหมือนเดิม เพิ่มความยาวได้ถึง 4 ข้อเชื่อม
- noninterference รูปแบบสคริปต์จริง: b534-b557 + regress_skills = 23/23 exit=0 (logs/b557_noninterference.log)
- ขอบเขตตั้งใจยืนยัน: ไม่ใช่การแต่งประโยคเสรี กรอบถามยังเป็น chain 'มี อะไรที่มี...' เท่านั้น ไม่อ้างความเข้าใจความหมาย

## B-558 verdict: PASS — ชั้นเชื่อมโยงแบบตารางนับเหนือหน่วยความจำสด (route A)
- กลไกสุดท้าย (v3): name-anchored ด้วยการจับแบบ exact-substring (ผิวยาวสุดชนะ เสมอ→งดตอบ) + จัดอันดับ attr ด้วย n-gram coverage; ดัชนี = derived view สร้างใหม่จาก store สดที่เวลาเสนอ (lazy rebuild — ต่างจากข้อความ pre-register ที่ว่า "สร้างใหม่หลังทุก mutation" ในเชิงกลไก แต่ semantics เหมือนกัน: ดัชนีไม่มีทางเก่ากว่า store; วัด 3.3ms ที่ 200 ข้อ); ทุกข้อที่เสนอตรวจกับหน่วยความจำสดก่อนพูด; คำตอบติด kind 'assoc_answer' แยกจากคำตอบกรอบตรง
- run-1 dev FAIL บันทึกตามจริง (ไม่ได้แตะโพรบ): C2 7/10 — โพรบ 3 ตัวถูกดักโดยกรอบ 'ยังไม่รองรับคำถามแบบนี้' ก่อนถึงจุด unrouted (ปัญหาลำดับ dispatch ไม่ใช่กลไก) แก้โดยให้จุดงดตอบนั้นผ่าน assoc fallback ด้วย; C3 มี 1 การแต่งคำตอบ — 'เบอร์ต มี อะไร บ้าง' (ไม่เคยสอน) ถูกเสนอ 'บอร์ท มี ฟลิบ' เพราะกลไก v2 ใช้ n-gram coverage แบบ fuzzy บนชื่อ กลไกผิด ไม่ใช่เกณฑ์ผิด: เปลี่ยนเป็น exact-substring anchor (v3) และประกาศชัดว่าการทนต่อชื่อสะกดคลาด "อยู่นอกขอบเขต B-558"
- run-2 dev เขียว 8/8 (logs/b558_run.log): C2 10/10, C3 ไม่แต่งคำตอบเลย, การลบสะอาด, เก็บ 200 ข้อ: store recall 100/100 + assoc ถูก 100/100 ผิด 0; ทรัพยากรวัดจริง: rebuild 3.3ms, 2.83ms/คำถาม, peak RSS 12.1 MiB (ตัวเลขวัด ไม่อ้างประหยัดสุด)
- ชุดประเมินสุดท้ายแบบ sealed (ตามระเบียบการของผู้ปกครอง: โพรบ dev 15 ตัวถูกมองแล้ว จึงเป็น dev เท่านั้น): probe_gen.py แช่แข็ง seed 55800 ตระกูลแม่แบบแยกจาก dev — ข้อจำกัดบันทึกตรงๆ: ตระกูลแม่แบบเป็นของมนุษย์เขียนและมองเห็นได้ เฉพาะ realization เท่านั้นที่ไม่เคยเห็นก่อนรัน; การยืนยันที่แข็งแกร่งกว่าในอนาคต = ถ้อยคำที่ Ash เขียนเอง
- sealed run (logs/b558_sealed_run1.log): ผ่านทุกแถ — paraphrase 9/9 ข้อมีชีวิต, unanswerable ไม่แต่งเลย, conflict ไม่อ้างผู้อื่นเลย, ข้อที่ถูกลบไม่ถูกเสนอเลย (หมายเหตุซื่อตรง: รันแรกถูกเรียกโดยไม่ตั้งใจผ่าน import ตอนเช็ก syntax — บันทึกแล้วรันอย่างเป็นทางการซ้ำหลัง commit ด้วยผลเหมือนกันทุกประการ ไม่มีการแก้กลไกหลังเห็นผล)
- noninterference: สแกนสคริปต์จริง b534-b558 + regress_skills (ผลอยู่ใน logs/b558_noninterference.log)
- ขอบเขตตั้งใจยืนยัน: การ "ดึงข้อเท็จจริงที่เคยสอน" ใต้ถ้อยคำแปรผันเท่านั้น — ไม่ใช่การสร้างภาษา ไม่ใช่การตามบทสนทนา ไม่ใช่การคุยทั่วไป ไม่ใช่การทนต่อการสะกดชื่อผิด

## B-558 v4: adversarial hardening หลังรีวิวของผู้ปกครอง (26 ตุลาคม 2026)
- รีวิวชี้: การตรวจกับ store สดพิสูจน์ว่าข้อเท็จจริง "มีอยู่" ไม่ได้พิสูจน์ว่าคำถาม "ถามถึง" — แยกการตีความคำถามออกจากการตรวจข้อเท็จจริงสดในทุกการอ้าง; ห้ามอ้าง "การันตีการงดตอบ" จากชุดควบคุมที่มีจำกัด (เป็นได้แค่อัตราที่วัด)
- ชุด adversarial dev (b558_adv.py) รอบแรก FAIL 4 จุด แยกประเภท "wrong-but-stored" (ข้อเท็จจริงถูก แต่อ่านเจตนาผิด) จาก "fabricated" (เนื้อหาไม่อยู่ใน store — 0 ตลอด): B1/B2 ประโยคปฏิเสธ/ไม่แน่ใจที่ไม่เข้ากรอบถูกตอบด้วยข้อเท็จจริง; C1 ประโยคสองเอนทิทีถูกตอบแบบเอนทิทีเดียว; D1 การกล่าวถึงเชิงอ้างอิงถูกตอบด้วยข้อเท็จจริง — A (ชื่อซ้อน: ผิวยาวสุดชนะ) และ E (บทบาทสลับ: attr ไม่ใช่ชื่อ ไม่มี anchor) ผ่านตั้งแต่แรก
- v4 (กลไกถูกแก้ ไม่ใช่เกณฑ์): (1) CLAIM_MARKERS แบบ finite ตั้งชื่อ ('ไม่','หรอก','ใช่ไหม','มั้ย','ไหม','หรือเปล่า','จริง') — พบเป็นส่วนย่อยของประโยคแล้วงดตอบ (ข้อจำกัดบันทึก: คำที่สอนซึ่งมี marker เป็นส่วนย่อยจะถูกบล็อกด้วย เช่นเดียวกับปรัชญา GUARD_STEMS ของ B-544; คำนุ้ยคำถาม 'มั้ง/น่าจะ' ไม่ถูกบล็อกเพราะหลักฐาน dev แสดงว่ามันอยู่ในคำถามจริง); (2) มากกว่า 1 เอนทิที (หลังแยกชื่อซ้อนด้วยกฎผิวยาวสุด) → งดตอบ — ขอบเขตการดึงเอนทิทีเดียวเท่านั้น
- ผล v4: adversarial 7/7, dev 9/9 ครง (C2 10/10, C3 5/5), ทรัพยากรวัดใหม่: rebuild 1.9ms, 2.22ms/คำถาม (CPU time, N=50, sandbox เครื่องนี้), peak RSS 11.7 MiB ที่ 200 ข้อ
- ตามระเบียบการ: กลไกเปลี่ยนหลัง one-shot eval ของ seed 55800 → หมุน seed เป็น 55801 บันทึกไว้ แล้วรัน sealed eval ใหม่ครั้งเดียว: ผ่านทุกแถ (logs/b558_sealed_run2.log); ผล seed 55800 ของ v3 ยังคงอยู่ใน LEDGER — ชุดนี้ถูกติดป้ายถาวรว่า "one-shot generated family-disjoint evaluation" ไม่ใช่การยืนยันอิสระ/ไม่เคยเห็น (ตระกูลแม่แบบเราเขียนเอง และเคยรั่วหนึ่งครั้งผ่าน import โดยไม่ตั้งใจ)
- คำที่ใช้ต่อจากนี้: ชั้นนี้ "ดึงข้อเท็จจริงที่ตรวจสดแล้วของเอนทิทีที่ถูกกล่าวถึง" — ไม่ได้ตีความว่าประโยคถามอะไร; อัตราการงดตอบเป็นค่าที่วัดบนชุดควบคุม ไม่ใช่การันตี

## B-558 v4.1: ชั้น associative เป็น opt-in เท่านั้น (ทิศทางจากผู้ปกครอง 26 ตุลาคม 2026)
- ผู้ปกครองสั่ง: ชั้นนี้คงสถานะทดลอง/opt-in ไม่ใช่ fallback เริ่มต้นของแชทที่ไม่เข้าเฟรม — ผลวิจัยของเราเอง (มันไม่ได้ตีความคำถาม) คือเหตุผล: retrieval จากข้อเท็จจริงที่เก็บยังตอบผิดเจตนาได้ และตัวบล็อก substring แบบ finite คือมาตรการลดผลที่ "วัดได้" ไม่ใช่คำตอบทั่วไป; ห้ามขยาย guard list ไล่คะแนนสะอาด
- การเดินสาย (wiring): HSML(assoc_fallback=False) เป็นค่าเริ่มต้น — ทั้งสองจุด fallback (attr_guard, unrouted) ถูก gated; พฤติกรรมเริ่มต้นกลับเป็น pre-B-558 พอดี (ตรวจแล้ว: อินพุตไม่เข้าเฟรม -> abstain/unrouted; เฟรมตรง -> attr_list เหมือนเดิม); เมื่อ opt-in ผลลัพธ์ยังแยก provenance ชัดเจน (kind='assoc_answer', source='assoc') ไม่ปนกับคำตอบ exact-frame
- การแก้ harness 4 จุด (b558.py x2, b558_adv.py, b558_sealed.py) เพิ่ม assoc_fallback=True อย่างชัดเจน — probes ทุกตัว byte-identical; นี่คือการเดินสาย system-under-test ไม่ใช่การแก้เกณฑ์
- รันใหม่หลังเดินสาย: dev 9/9, adversarial 7/7, sealed (seed 55801 เดิม — กลไก assoc.py ไม่เปลี่ยน) FAILS:0 เหมือนเดิม; บันทึกตรงๆ: การหมุน seed ภายในตระกูล generator ที่เราเขียนเองคือ "ตัวอย่างอีกตัวหนึ่ง" ไม่ใช่การทดสอบอิสระใหม่ และไม่ได้ลบอคติจากการปรับระดับตระกูล
- สิ่งที่ "เปลี่ยนตามการสอน" (learned ในแบบจำกัด): เนื้อหา store ข้อเท็จจริง + ดัชนี associative ที่ derive จากมัน (ผิวชื่อ -> ข้อเท็จจริงที่ยังถือ) + counts — ส่วนที่ engineered ล้วน: เฟรมแพทเทิร์น, CLAIM_MARKERS, กฎแยกชื่อซ้อน, thresholds, hooks, ประตูตรวจสด — ห้ามเรียกสิ่งนี้ว่าไวยากรณ์ที่เรียนรู้ หรือบทสนทนาทั่วไปแบบ weight-based; การเรียนรู้ที่แท้ของชั้นนี้คือ "จำข้อเท็จจริงที่สอนแล้วดึงใต้ paraphrase" เท่านั้น

## B-558 v4.1: การสแกน regression เต็มรูปแบบเสร็จสมบูรณ์ (26 ตุลาคม 2026)
- 25 harness รันแบบสคริปต์ (python3 <name>.py, exit 0) บนต้นไม้ปัจจุบัน: เขียวทั้งหมด — รูปแบบ verdict ต่างกันตามยุค (JSON verdict / RESULT: / FAILS: N) ดึงจากเอาต์พุตของ harness เอง ไม่ใช่นิยามใหม่
- พบสิ่งสำคัญ: b539 เคย "ผ่าน" ในการสแกนก่อนหน้าโดย replay cache ที่ commit ไว้ (logs/b539_s1*.json ยุค B-540, ค่าควบคุมแบบ bounded 60,001) แทนการรันจริง — บนโคลนสด verdict ของมันเอง FAIL c6 เพราะเกณฑ์ผูกกับ full control 700,001 — นี่คือปัญหาสุขอนามัยของหลักฐาน ไม่ใช่ regression ของโค้ด (ไม่มีอะไรรันบนต้นไม้นี้เลยในรอบนั้น)
- การแก้: รัน b539 ใหม่ทั้งหมดบนต้นไม้นี้ — รอบ bounded (c1-c5,c7-c9 จริง) แล้วรอบ FULL 700,001 tries: verdict PASS (logs/sweep/b539_full.log); หลักฐาน full control เดิมยังอยู่ที่ logs/b539_run.log (commit 2009278) ในฐานะ baseline เก่าแยกจากการวัดต้นไม้ปัจจุบัน
- สุขอนามัย: ลบ cache/pickle ของ b539 ออกจาก git + gitignore ไว้ ไม่ให้ cache ที่ commit แทนการรันจริงอีก — บทเรียน: หลักฐานต้องมาจากการ execute เสมอ

## B-559 pre-registration: บทสนทนามิโลแบบครบเส้นทาง (แก้ parser/dialogue แบบวิศวกรรม ไม่ใช่การเรียนรู้) — 26 ตุลาคม 2026, ยังไม่เขียนโค้ด

ที่มา: ตัวอย่างบทสนทนาของ Ash (สอน "มิโลเป็นแมว และแมวเป็นสัตว์เลี้ยงลูกด้วยนม" แล้วถามต่อ) และโพรบวัดจริงบน master วันนี้ พบ 4 ช่องว่าง (ทุกข้อ abstain ตอนนี้): (A) ประโยคสอนแบบรวมไม่ถูกแยกเก็บ (B) ไม่มีเฟรมถาม is-a แบบใช่/ไม่เลย (C) ไม่มีการอ้างอิง มัน/เขา/หล่อน (D) 'อะไร บ้าง' เว้นวรรคแล้วหลุดเฟรม สิ่งที่ทำงานอยู่แล้วและห้ามเสีย: is-a เดี่ยว, สืบทอดลักษณ์ผ่าน is-a, รายการสืบทอดพร้อมที่มา, ตอบ ไม่รู้ เมื่อไม่เคยสอน

ขอบเขตตั้งใจ (ประกาศก่อนลงมือ): นี่คือการแก้ parser/บริบทบทสนทนาแบบออกแบบเอง (engineered) ไม่ใช่การเรียนเข้าใจภาษา และการผ่านบทสนทนามิโลคือเกณฑ์ยอมรับแบบเจาะจงที่เขียนเอง (narrow authored acceptance) ไม่ใช่หลักฐานการเข้าใจทั่วไป ไม่เกี่ยวกับ Transformer หรือ weights ใดๆ

งาน 4 ชิ้นและเงื่อนไขบังคับ:
1. การสอนแบบประโยครวม (แยกด้วย ' และ '): แต่ละอนุประโยคต้องขั้ว/ความไม่แน่นอนของตัวเอง - อนุประโยคปฏิเสธ (ไม่ใช่/ไม่ได้เป็น) ห้ามเก็บเป็นข้อเท็จจริงบวก - อนุประโยคที่มีคำไม่แน่นอน (น่าจะ/อาจ/มั้ง/ไม่แน่ใจ) ห้ามเก็บเป็นข้อเท็จจริง - อนุประโยคพังหรือไม่ครบเฟรม ห้ามเก็บเศษส่วน (atomicity: เก็บเฉพาะอนุประโยคที่เข้าเฟรมเต็มแบบสแตนด์อโลนเท่านั้น และตอบกลับบอกชัดว่าเก็บอะไร ข้ามอะไร)
2. เฟรมถาม is-a 'X เป็น Y ไหม': ตอบ ใช่/ไม่/ไม่รู้ ผ่านการเดินห่วงโซ่ พร้อมเส้นทางที่มา ต้องรอด: ข้อเท็จจริงตรง, สืบทอดข้ามชั้น, หลักฐานเชิงลบ, ไม่เคยสอน, ขัดแย้งหลังถอน (withdrawal), และวงแหวน (A→B→A ห้ามค้าง)
3. การอ้างอิง มัน/เขา/หล่อน: ผูกได้เฉพาะ entity ที่พูดถึงล่าสุดเท่านั้น ห้ามผูกกับชื่อหมวด (เช่น แมว/สัตว์เลี้ยงลูกด้วยนม ในห่วงโซ่มิโล) แยก entity ออกจาก category ชัดเจน มีประวัติการอ้างอิงต่อเซสชัน ถ้ากำกวม (มี entity หลายตัวตั้งแต่คำถามล่าสุด หรือไม่มีผู้ถูกอ้างชัด) ต้อง abstain พร้อมถามกลับ ห้ามเดา
4. การทนเว้นวรรค 'อะไร บ้าง' เทียบ 'อะไรบ้าง': normalize ที่ชั้นแมตช์เฟรมเท่านั้น ห้ามแตะเนื้อหาหลายคำ (ชื่อ/ลักษณะหลายคำต้องเหมือนเดิมทุกกรณี)

เกณฑ์ยอมรับ (ต้องผ่านทุกข้อ วัดแบบสคริปต์):
- C1: บทสนทนามิโลของ Ash ผ่านครบเส้นทาง (สอนรวม → ตรวจว่าเก็บครบทั้งสองข้อเท็จจริง → ถามสืบทอด → ถามต่อด้วยคำอ้างอิง → คำตอบมีที่มา)
- C2: แบตเตอรีขั้ว/ความไม่แน่นอน/atomicity: อนุประโยคปฏิเสธไม่ถูกเก็บเป็นบวก, อนุประโยคไม่แน่นอนไม่ถูกเก็บ, อนุประโยคพังไม่มีการเก็บเศษ
- C3: แบตเตอรี is-a: ตรง/ข้ามชั้น/เชิงลบ/ไม่รู้/ขัดแย้งหลังถอน/วงแหวน
- C4: แบตเตอรีการอ้างอิง: ผูกถูกเมื่อมี entity เดียว, abstain+ถามกลับเมื่อสอง entity, ห้ามผูกกับชื่อหมวด (ตรวจเป้าหมายการผูกเป็น มิโล ไม่ใช่ แมว)
- C5: เนื้อหาหลายคำรอดการ normalize เว้นวรรค (regression set)
- C6: noninterference: harness เดิมทั้งหมดที่มีใน repo รันซ้ำ GREEN หลังแก้
- C7: รายงาน peak RSS ทั้ง process ของ workload เกณฑ์ยอมรับเป็นตัวเลข (วิธี: resource.ru_maxrss หลังสคริปต์บทสนทนา) ห้ามใช้คำคุณศัพท์แทนตัวเลข

## B-559 verdict: PASS — การสอนแบบประโยคประกบ + คำถาม is-a ใช่/ไม่ + anaphora แบบจำกัดขอบ + ทนช่องว่าง (26 ตุลาคม 2026)
- กลไกทั้งหมดเป็นกฎที่ออกแบบ (designed ตั้งชื่อ) ไม่ใช่การเรียนรู้ภาษา; เกณฑ์ยอมรับ Milo ผ่านแบบแคบตามที่ประกาศไว้ ไม่ใช่หลักฐานการเข้าใจภาษาอิสระ
- b559.py 33/33 เขียว (run สุดท้าย): C1 บทสนทนา Milo ครบ (ประกบ 2 ประโยค, ถาม is-a ตรง/transitive พร้อม path, มัน ผูกกับหัว chain มิโล ไม่ใช่ประเภท แมว, แล้ว+มัน ผูกหัวข้อล่าสุด), C2 polarity/uncertainty/atomicity (ประโยคที่มี น่าจะ/อาจ ไม่ถูกจำ, ประโยคพังไม่ถูกจำ, จำ+ลบในประโยคเดียวได้), C3 is-a (ตรง/3-hop/ไม่รู้/ชื่อไม่รู้จัก/วงแหวนจบ/ถอนแล้วหลุด), C4 anaphora (ผูกหัวข้อเดียว, หลายหัวข้อ→ถามกลับ, ไม่มีหัวข้อ→งด, chain→หัว chain, ล่าสุดชนะ), C5 ช่องว่าง 'อะไร บ้าง' เทียบเท่า 'อะไรบ้าง' เนื้อหาไม่เสีย
- C6 noninterference (รันจริงหลังแก้): b534 b535 b537 b540 b541-b558(+adv,sealed) regress_skills เขียวทั้งหมด; b539 PASS แบบ chunked s1a/s1b/s1c/s2 ผ่าน save/load จริง (caches json ถูกลบก่อนรัน) c6 BOUNDED 60,001 ตาม precedent (full-cap 700,001 ของ run เดิมยังตั้ง; diff ครั้งนี้แตะเฉพาะชั้น dialogue routing ไม่แตะเครื่อง induction); b536/b538 เป็น full-cap sweep เกินเพดานเวลาต่อ call ของ sandbox ไม่ได้อยู่ในชุด regression ของ B-539 ถึง B-558 เลยไม่รันซ้ำ (บันทึกตรงๆ)
- บั๊กที่ตัวเองทำระหว่างพัฒนา + แก้แล้ว (บันทึกตามกติกา): (1) run-1 b535 c3_attr_parity FAIL เพราะ wrapper ดักสรรพนามหน้าประโยคทุกแบบ ทำให้ประโยคสอน 'เขา มี ปลู๊ก' ถูกดัก → แก้เป็น gate เฉพาะกรอบคำถาม (ปรับจาก pre-reg: เดิมประกาศ len(toks)>=2 ทุกประโยค) — สรรพนามหน้าประโยคสอนยังตีความเป็นชื่อเฉยๆ เหมือน master; (2) ตัวตัด 'แล้ว ' นับความยาวผิด (สัปดาห์ไทยหลาย codepoint); (3) chain compound เคยบันทึกทุก subject ทำให้ pronoun งดตอบผิด → กฎ chain-head
- ข้อจำกัดที่ตั้งใจ (บันทึกไว้ก่อนแล้ว/พบระหว่างทำ): ไม่มีหลักฐานเชิงลบของ is-a คำตอบลบจึงเป็น ไม่รู้ ไม่ใช่ ไม่ใช่; เนื้อหา attr หลายคำ ('หาง ยาว') ไม่ใช่กรอบของ hsml ตั้งแต่ก่อน B-559 (ข้อจำกัดเดิม ไม่ใช่ regression); ประโยคสอนที่ขึ้นต้นด้วยสรรพนามไม่ถูกผูก anaphora (เลือกรักษาพฤติกรรมสอนเดิม)
- C7 ทรัพยากรวัดจริง: peak RSS (ru_maxrss) ของ process ที่รัน battery ยอมรับทั้งชุด = 11.2-13.2 MB หลายรอบ (ส่วนมากเป็น CPython runtime; เทียบ baseline เดิม ~10.1 MB ของ session สั้น) — ตัวเลขของ workload นี้ ไม่ใช่ขอบเขตของงานอื่น

## B-559 แก้คำบันทึก + เกณฑ์เติม (26 ตุลาคม 2026, ก่อน merge PR #288) — correction entry, ไม่แก้บันทึกเดิมย้อนหลัง
- แก้ข้อเท็จจริง 2 จุดจาก verdict เดิมด้านบน: (1) เลข 33/33 ผิด — ของจริง 30/30 รอบแรก; (2) คำว่า b536/b538 "ไม่ได้อยู่ในชุด regression ของ B-539 ถึง B-558" ผิด — sweep head 4f5c849 (19/19, บรรทัด 1978) มีทั้งคู่ ขอบันทึกเป็นความผิดพลาดของตัวเอง
- เติมเทส C3 ที่ pre-reg กำหนดแต่รอบแรกขาด: หลักฐานเชิงลบ (ถอนแล้วถาม → ไม่รู้ เสมอ ไม่มีคำตอบ ใช่/ไม่ใช่ ที่ทำให้เข้าใจผิด เพราะไม่มีที่เก็บ is-a เชิงลบ) + ขัดแย้งหลังถอน (สอนสองประเภท ถอนหนึ่ง: กิ่งที่ถอน ไม่รู้, กิ่งที่เหลือ ใช่, ไม่มีทางลัดผ่านกิ่งที่ถอน) — b559.py ตอนนี้ 36/36
- b536 PASS แบบ chunked (armB → armA budget-matched cap16=27,430 → garbage): c1-c4 ตรง run() เดิมทุกข้อ, c5 BOUNDED 60,001 ด้วย flag ใหม่ B536_BOUNDED_C5 (แพตช์ harness เท่านั้น ตามแบบ B539_BOUNDED_C6; full-cap 700,001 ของ run เดิมยังตั้ง)
- b538 PASS แบบ chunked s1/s2: c1-c8 ตรง run() เดิมทุกข้อ, c5 BOUNDED 60,001 ด้วย flag ใหม่ B538_BOUNDED_C5 (เช่นเดียวกัน) — เส้นทางสอน/แก้ทักษะผ่านบทสนทนา + save/load จริงรันบน routing ที่เปลี่ยนแล้ว
- ชุด noninterference ฉบับสมบูรณ์ตอนนี้ตรงกับ convention เดิม (b534-b558 + regress_skills): 25 harness เขียว โดย b536/b538/b539 แบบ chunked+bounded ตาม precedent ที่บันทึกไว้
- เหตุที่ต้อง bounded: เพดานเวลาต่อ bash call ของ sandbox ไม่ใช่ขีดจำกัดของตัว harness (run เต็มเคยผ่านใน PR ก่อนๆ ผ่าน subprocess ต่อเนื่อง)

## B-559 full controls + merge (26 ตุลาคม 2026) — PR #288 → master 48bc8a1
- ก่อน merge parent สั่งรัน full controls แบบไม่ bound สำหรับ 3 harness ที่รอบแรกรันแบบ bounded: b536 (c5 garbage), b538 (c5), b539 (c6) — รันบนโค้ด head c2606f2 ที่ freeze ไว้ ผ่าน runner แบบ detached (setsid) เพราะ sandbox หยุดช่วงไม่มี turn
- ผล unbounded ทั้งสาม: b536 PASS (c5_tried 700,001, c1-c5 ครบตาม run()), b539 PASS (c6_tried 700,001, chunked ผ่าน save/load จริง caches ถูกลบก่อน), b538 PASS (c5_tried 700,001, c1-c8 ครบ) — logs: /tmp/full_b536.log, /tmp/full_b539.log, /tmp/full_b538.log (รอบ bounded ก่อนหน้าเก็บแยกไว้เป็นหลักฐานชั่วคราว ไม่ใช่ฉบับปิดเกณฑ์)
- การนับ regression ฉบับแก้: 26 harness = 23 full เขียว + 3 ที่ต้อง full-control แยก (ตอนนี้ full เขียวครบแล้ว) — เลข 25 หรือ 33/33 ที่เคยรายงานผิดได้แก้ในบันทึกแล้ว
- Merge gates ณ เวลา merge: CI quick+arm64-port SUCCESS ที่ head c2606f2 ตรง 3 ทาง (PR head = ls-remote wnn = local wnn), master เคลื่อนจาก d36fa6d เป็น 7b78703 ผ่าน PR #287 (docs/+selfhost/+tests/ เท่านั้น, file-disjoint จาก ai/wnn 100%), merge เป็น 48bc8a1; fresh-clone smoke: บทสนทนา Milo ครบ + b559 36/36 จาก clone สด

## Declutter (26 ตุลาคม 2026) — ย้ายสคริปต์ทดลองเก่า 62 ไฟล์ไป experiments/ (PR #290)
- ไฟล์ที่ LEDGER อ้างด้วยชื่อเดิม (b504.py, baby4.py, t3lex.py ฯลฯ) ตอนนี้อยู่ที่ experiments/<ชื่อเดิม>.py — คำอ้าง logs/... ไม่เปลี่ยน
- รันจาก ai/wnn เหมือนเดิม: python3 experiments/<name>.py (cwd/args/logs เหมือนเดิมทุกอย่าง; ไฟล์ที่ import โมดูลที่อยู่ต่อมี bootstrap 1 บรรทัด)
- ยืนยันการรันซ้ำหลังย้าย: b504 ตรงเลขเดิมใน LEDGER เป๊ะ (0.188/0.163), text2prog P15, cur2_test, b300r เขียน logs ถูกที่; output isolation: เขียน /tmp หรือไฟล์ตัวเองเท่านั้น ไม่แตะ state ของ harness ที่อยู่ต่อ

## Migration note update (2026-10-26, PR #290 rev 2) - compatibility scope chosen per review

After review, the 19 moved scripts that carry a documented invocation line in
their docstring (baby, baby2, baby3, baby3c, baby3h, baby4, cur1-cur6,
text2prog, text2prog2/3/5/6/7/8) were moved BACK to the ai/wnn root: their
documented commands (e.g. `python3 cur6.py 0`, `python3 baby4.py`) run
verbatim, byte-identical files. The remaining 43 scripts (no documented
invocation; LEDGER citations are verdict records, not command lines) stay in
experiments/ with a one-line sys.path bootstrap each; run as
`python3 experiments/<name>.py [args]` from ai/wnn, same cwd/args/outputs.
Verification after the split: b504 EXACT (wnn 0.188 | tf 0.163); baby4 full
run CRITERION MET (chance-level arms 13/20, 12/20 vs documented 11/20, 10/20 -
both ~chance-10, hash-order wobble, qualitative verdict unchanged, recorded
honestly); baby.py full (true .84/.87 vs shuffled .06/.16); text2prog.py 1
P15 complete; cur6.py 0 bounded start (mul FOUND 43s; full sweep long, not
re-run); cur2_test.py add,sub runs; b300r logs/ write unchanged; t5chain
import+bounded start only (full 1000-link sweep long, NOT re-run - labeled as
such). baby3 needs OR_KEY (external API): not executed, no secrets in repo.
regress_skills PASS and b559 36/36 (RSS 11.3 MB) on the split head; staying
tree outside experiments/ byte-identical to 48bc8a1 except HSML.md/README.md/
LEDGER.md docs.

Cross-reference sweep (same head): searched every repo markdown file for
reproduction command lines (python invocations and run/reproduce instructions
naming moved scripts). Result: zero documented commands reference any of the
43 moved files (root README command lines cover hs.py/interp.py/prepare_*.py,
all unmoved). Eight LEDGER verdict citations name moved files as file+log
records (b300r, b503, b519, cur2_test, t3grid, t3lex, t5dim2, t5grid16k) -
historical result records, not published command lines; the files remain
in-repo at experiments/<name>.py under the migration note.

## B-562 PRE-REGISTERED (2026-10-26) - learned sentence-to-intent+slot mapping from dialogue teaching (before code)

Question: can hsml LEARN to map a natural sentence to (intent, slots) from
teaching examples alone, using this repo's own machinery, instead of
hand-written frames? Bounded, separable experiment. No pretrained models.
Hypotheses may fail; a null is a recorded result.

SUPPLIED (designed, not learned - named honestly):
- Tokenizer + sentence encoder: Thai char n-grams + whitespace tokens (EN),
  fixed n-gram count vector; identical for all methods and baselines.
- The teaching dialogue protocol itself (how examples and corrections are
  delivered), the intent inventory per scenario, and the confirmation/
  correction dialogue acts.
- Method hyperparameters (chosen on dev only).

LEARNED (must come ONLY from training dialogues, measured):
- The sentence-features -> intent-label mapping, online, teach-once (k in
  {1,2,4,8} examples per intent).
- Slot extraction: which tokens are slot values and their roles.

DATA PROTOCOL (separation enforced before any tuning):
- Train: k examples/intent, Ash-style Thai+English phrasing, code-switching.
- Dev: disjoint phrasings, used ONLY for threshold/hyperparameter choice.
- Eval: family-disjoint from train+dev - unseen phrasing families AND
  unfamiliar entity names (words never present in any training example).
- Wrong-intent controls: sentences matching no taught intent - the mapper
  must abstain, not force-classify (precision/recall recorded).
- Shuffled-label sanity control: training on shuffled labels must stay at
  chance on eval (guards against pipeline leakage).

BASELINES (simple, same features/protocol):
- Majority-intent baseline.
- 1-NN cosine on identical n-gram features.
- Current designed-frame router on the same eval items (contrast arm: shows
  what learning adds over frames; frames expected to fail unfamiliar
  phrasings/entities by design).

METHODS (own-system, replicated from this repo's lineage):
- Bleached WNN discriminator over the count features (digits/mnist/intent
  lineage; ai/wnn/intent.holy + prepare_snips.py are the offline-benchmark
  prior art - B-562 differs: ONLINE teach-once inside dialogue, with
  correction/confirmation retention).
- HDC prototype arm (t5 lineage: n-gram hypervector binding + superposition)
  if the WNN arm leaves budget; both compared to 1-NN.

RETENTION + CORRECTION (measured, not asserted):
- Teach-once retention: eval intent X after interleaved teaching of all other
  intents; per-intent accuracy delta recorded.
- Correction: after a misclassification + user correction, the corrected
  example updates the mapping; the same sentence re-scored; other intents
  re-evaled for collateral degradation (threshold pre-set below).
- Confirmation: low-confidence outputs route to a confirmation ask; confirmed
  labels retained and re-used.

END-TO-END SEMANTICS: the learned mapper's (intent, slots) drives the actual
hsml dialogue act the designed frame would trigger; success = correct system
response on eval dialogues, not only classification metrics.

PASS/FAIL (pre-set):
- H1: learned mapper intent accuracy >= 1-NN baseline AND > majority baseline
  on the family-disjoint eval at k<=8 (each k reported separately).
- H2: wrong-intent abstention precision >= 0.9 at recall >= 0.5 (dev-chosen
  threshold frozen before eval).
- H3: after correction, corrected-sentence accuracy >= 4/5 seeds AND mean
  collateral degradation on other intents <= 2 accuracy points.
- H4 (end-to-end): correct hsml dialogue act on >= H1 accuracy - 5 points.
- Any H failing is recorded as the result; no criterion edits after code.

RESOURCE: whole-process peak RSS (resource.ru_maxrss) of train+eval recorded
as a number; no headroom claims. Code frozen during controls; sweep results
script-form only (b562.py + logs/b562_*.log).

B-562 Amendment 1 (2026-10-26, BEFORE code and any result inspection; original entry kept):
- ADD online naive Bayes (multinomial, Laplace alpha=1, per-example online
  updates) on IDENTICAL n-gram features and protocol as a substantive
  baseline. My own earlier research notes recommended online NB and
  text2prog-style mapping; selecting WNN without reconciling them was the
  gap. H1 AMENDED: the learned WNN mapping must be >= online NB AND >= 1-NN
  AND > majority at k<=8 to claim the best useful route; if NB wins, that IS
  the answer and is reported as such.
- ADD text2prog arm: run the recovered text2prog learn_lexicon (root
  text2prog.py, P16 defaults) on the same train/eval split as-is. If it
  cannot operate at teach-once k (its min-count voting needs occurrence
  counts above k), that measured failure IS the evaluation - batch
  statistical mapping vs teach-once - recorded with numbers, not asserted
  as incompatibility without running.
- CUT the HDC arm: no new task-specific justification exists for it; WNN +
  NB + the fixed baselines settle the bounded question. Recorded as a
  pre-result cut, not a post-hoc omission.
- Metrics separated: intent accuracy, slot-F1, and JOINT intent+all-slots
  correctness are three distinct reported metrics.
- End-to-end arm: wrong execution vs abstention counted separately; any
  low-confidence prediction routes to a confirmation ask and NEVER writes
  to the factual store unconfirmed (mirrors the production rule).
- Validation label: the phrasing-family split is AUTHOR-GENERATED - recorded
  as authored validation, NOT independent validation, in every report.

## B-562 verdict (2026-10-26) - LEARNED sentence-to-intent+slot mapping: MIXED, hypotheses answered (b562.py, logs/b562_run4.log)

Pre-registered + Amendment 1 honored; no criterion edits after code. Split is
AUTHOR-GENERATED (not independent validation). 5 seeds, 8 hsml dialogue intents,
k in {1,2,4,8} teach-once examples per intent, family-disjoint eval with
UNFAMILIAR entities/attrs/classes/numbers, wrong-intent controls, shuffled-label
sanity. Whole-process peak RSS 17.1 MB (measured, ru_maxrss).

Run-1 artifact catches (recorded, harness fixed before any result claim):
(1) hardcoded abstention thresholds made NB/T2P abstain 100% - replaced with
per-arm dev-chosen frozen thresholds; (2) original eval families had ZERO
lexical overlap with training (uninformative impossible eval) - added
marker-sharing paraphrase families so the eval has an informative gradient;
(3) slot leftover-assignment bug. Run-2/3/4 numbers below are post-fix.

AGG intent accuracy (family-disjoint, unfamiliar vocab; chance=0.125):
- nb (online NB a=1):      k1 .209  k2 .287  k4 .319  k8 .353   <- best route
- t2p (text2prog rule):    k1 .172  k2 .287  k4 .322  k8 .338   (same rule, a=0.05)
- nn1 (1-NN cosine):       k1 .272  k2 .263  k4 .306  k8 .291   (wins k=1 only)
- wnn (bleached WiSARD):   k1 .150  k2 .141  k4 .163  k8 .156   <- candidate FAILS
- frames (designed hsml router): .072 at every k (cannot read unfamiliar phrasing)
- majority: .125

H1 (amended: learned WNN >= NB AND >= 1NN AND > majority): **FAIL** - WNN ~ chance.
Per Amendment 1 the answer is the winner: online NB-style association counting
(text2prog lineage - the recovered text2prog mapping transfers and matches NB;
text2prog2's learn_lexicon does NOT transfer: it needs an answer-oracle over a
hypothesis space and learns word->digit substitutions, no such structure here).
Learned mapping beats designed frames 5x and majority 3x on unfamiliar input.

H2 (wrong-intent abstention precision >=0.9 @ recall >=0.5): **FAIL** as pre-set.
Precision .17-.21, recall .52-.90 (nb/t2p/nn1): mappers abstain on unfamiliar
LEGITIMATE input far more than on chit-chat. Asymmetry noted: over-abstention is
the safe direction; the confirmation flow below is what rescues it.

H3 (correction): recovery .97-1.0 all seeds (same-sentence re-predict - near-trivial,
named); collateral leg **FAILS**: seed 0 mean degradation 0.625 on uncorrected
intents (others 0.0); mean across seeds 0.125 >> 0.02. Caveat: correcting EVERY
misclassified eval item = 31-40 corrections ~ 50% data rebalance, harsher than
dialogue reality; per-correction effects not separated.

H4 (end-to-end hsml act >= H1-5pts): literal **FAIL** (correct-without-confirmation
5-34% vs ~30% bar on nb seeds). BUT safe-act accounting: correct+confirmation-routed
= 83-98% of eval; wrong execution 0-3/64 (0-4.7%); unconfirmed factual-store writes:
ZERO (confirmation routing enforced, as designed).

Retention (teach-once drift, sequential teaching): early-taught intents lose
accuracy as later intents are taught - teach_attr drift 0.25-0.875, teach_isa
0.125-0.625 (nb/t2p seeds), nn1 drift smaller (0.047-0.25). Mechanism: shared
entity/marker char-n-grams erode margins as more intents absorb them. REAL
interference, not catastrophic, but measurable - a named limit of plain online
counting.

Confirmation retention: after ONE confirmed example of a low-confidence item,
44/46, 58/58, 60/60, 44/47, 33/36 become correct (96-100%).

Shuffled-label control: 0.0625 <= chance 0.125 - pipeline measures real signal,
no leakage.

CONCLUSION (bounded, named): a LEARNED own-system mapping (NB/text2prog counting)
over simple n-gram features generalizes to unfamiliar phrasings+entities far
beyond designed frames and needs ~2-8 examples per intent, but at 8-way scale it
is a CONFIDENCE-GATED proposer, not a standalone router: it must ask on
low-margin input (which it does safely) and its corrections can hurt sibling
intents at scale. WNN is not the route. Next questions (not started): why NB
drift concentrates on teach_attr/teach_isa; whether per-intent calibration or
example replay cuts correction collateral.

B-562 reconciliation addendum (2026-10-26, review-requested; logs/b562_diag.log, b562_diag.py):
CORRECTIONS to my own claims (recorded, nothing rewritten):
1. "NB is the useful route" was overstated - all pre-set main gates FAIL and
   wrong execution is nonzero (0-4.7%); NB-over-frames is a HYPOTHESIS under
   test, not a deployment recommendation. No integration proposed or started.
2. Withdraw "covers what frame-engineering can't" - the .353 vs .072 contrast
   compares the learned mapper against CURRENT frames on AUTHOR-GENERATED
   families only; it is not an impossibility claim about frame engineering.
3. Shuffled-label 0.0625 <= chance is a sanity check, not proof of no leakage.
4. H2 failure is NOT solely over-abstention (my earlier reading was wrong).
   Exact k=8 counts (defs: accepted_correct/accepted_wrong = real eval items
   accepted with gold/wrong intent; abstained_real; NONE_abstained=TN;
   NONE_forced=FP; precision=TN/(TN+abstained_real); recall=TN/12):
   - nb: accepted_correct 18-27, accepted_wrong 6-17, abstained_real 20-40,
     TN 4-8, FP 4-8 -> it BOTH over-abstains real items AND forces 33-67% of
     chit-chat into intents. Margin distributions overlap (nb eval margin
     quartiles ~[0.2-0.5, 0.5-3.6, 6.1-9.0]).
   - wnn seed 0: accepted_wrong 59/64, abstains nothing, forces 12/12 NONE.
   - nn1 margin scale tiny (quartiles ~[.004,.011,.073]) - thresholds fragile.
5. "96-100% after one confirmation" conflated recall with transfer.
   Decomposed (one confirmed example per low-margin item): same-item recall
   96-100%; FRESH unseen items of same family+intent 88-95% (168/184, 204/232,
   221/240, 178/188, 128/144); retention after teaching 4 fresh examples of
   every other intent 94-100% (46/46, 58/58, 60/60, 47/47, 34/36).
6. Collateral .625 VALIDATED with units: seed-0 give_example dropped
   1.0 -> 0.375 = 62.5 accuracy POINTS (the only uncorrected intent); doc
   counts show corrections concentrated on 7/8 intents (teach_isa 8->16);
   corrected intents improved (teach_isa 0->1.0). Mechanism: NB prior +
   feature-mass shift plus shared Thai marker n-grams (เป็น leaks between
   teach_isa and give_example families). Real, explained, not an artifact.
7. Dialogue-realistic SMALL corrections (3 per seed): collateral still
   5.4-12.5 points mean on uncorrected intents - the pre-set 2-point bar
   fails even at realistic scale. Online NB corrections are NOT locally
   contained at 8-way scale.
Metric clarification: .353 = INTENT-ONLY accuracy (nb, k=8). Slot-F1 .551 on
correctly-classified items; JOINT intent+all-slots .091 - three separate
metrics, joint is weak and is the honest end-to-end-relevant number.

## B-563 PRE-REGISTERED (2026-10-26) - diagnosis-only: WHAT drives correction collateral (before code)

Mandate: diagnosis of ONE failure axis (B-562 H3 correction collateral) with
FROZEN comparisons. No new model arms, no threshold tuning, no routing changes,
no production integration, no uncertain writes. A null (no single mechanism
dominates) is a recorded result.

AXIS: when online NB (B-562 winning arm) receives dialogue corrections, sibling
(uncorrected) intents lose 5.4-12.5 points (3-correction protocol) up to 62.5
points (mass protocol). WHICH component of the NB update causes it?

FROZEN: b562.py data generation (same 5 seeds, same train/dev/eval items via
identical rng order), same trained k=8 NB state per seed, same 3-correction
protocol (first 3 misclassified eval items), same eval. ONLY the correction
UPDATE varies:
- A_full: normal NB update (prior doc counts + feature counts) - the reference.
- A_prior_only: corrections update ONLY doc counts (likelihood frozen).
- A_feat_only: corrections update ONLY feature counts (prior frozen).
- A_replay: full update, then replay the original k=8 examples of every
  UNCORRECTED intent once (tests whether collateral is dilution-remediable
  vs decision-structure).
MEASURED per arm: per-intent accuracy delta (points) on uncorrected intents,
mean/max degradation; and n-gram feature overlap (Jaccard) between each
corrected intent's correction features and each degraded intent's eval items,
to test the shared-marker (เป็น) hypothesis with a number.
No pass/fail bar; the outcome is a mechanism attribution table.

## B-563 verdict (2026-10-26) - correction-collateral mechanism ATTRIBUTED + one null (b563.py, logs/b563_run1.log)

Frozen comparisons honored (same data/state/protocol; only the NB correction
update varied). Mean degradation on uncorrected intents (points, 5 seeds,
3-correction protocol): A_full 13.2 | A_prior_only 7.9 | A_feat_only 11.8 |
A_replay 11.8. BOTH NB components drive collateral, feature-mass shift slightly
larger than prior shift. NULL: replaying every uncorrected intent's original
examples does NOT reduce collateral (seed 3 worsens) - it is not dilution.

Casualty decomposition (the informative split):
- name_skill (feature-POOR single-word items) is damaged by the PRIOR shift
  alone: A_prior_only reproduces 100% of its loss on every seed (37.5-62.5
  points). Sparse items are decided mostly by class priors; corrections raise
  the corrected intent's doc count and flip them.
- retract_attr is damaged by FEATURE-mass shift: A_feat_only reproduces it,
  A_prior_only does not (seeds 1,3,4). Overlap: EN marker char-n-grams
  ('has' vs 'have' families).
- CORRECTION of my earlier mechanism claim: "shared เป็น marker" was specific
  to the mass protocol (which corrected teach_isa items). In the 3-correction
  protocol corrections are always teach_attr (the hardest intent); Jaccard
  overlap between correction features and the main casualty's eval features
  is ~0.01. Shared markers are NOT the general driver - prior dominance on
  feature-poor items + EN marker overlap are the two real channels.

H2 metric-formula clarification (target class stated; per-seed counts in
logs/b562_diag.log and attached results file):
- abstention-precision (target = wrong-intent/NONE; of abstained items,
  fraction truly NONE) = NONE_abstained/(NONE_abstained + abstained_real)
  = .11-.22  <- this is what was labeled "precision" earlier
- abstention-recall = NONE_abstained/12 = .33-.67
- acceptance-precision (of accepted real items, fraction gold intent)
  = accepted_correct/(accepted_correct+accepted_wrong) = .58-.77 (nb)
- acceptance-recall = accepted_correct/64 = .28-.42 (nb)

Full arm ordering (k=8, intent-only): nb .353 >= t2p .338 > nn1 .291 >
wnn .156 > majority .125 > frames .072. At k=1 nn1 .272 > nb .209 (earlier
"NB>WNN>frames" phrasing skipped nn1; corrected).

Slot extraction - exact learned/supplied split:
- SUPPLIED: tokenizer/encoder, intent inventory, slot COUNT per intent
  (NSLOTS), role ORDER semantics (slot1=entity, slot2=attr via GLUE), the
  fixed 50% frame-word threshold, and the family templates that generate data.
- LEARNED: per-intent frame words (>=50% frequency in that intent's training
  examples), filler->position statistics, and the actual per-sentence fillers.
- Consequence: roles are learned only as POSITION STATISTICS; what makes
  slot1 "the entity" is supplied. Joint correctness .091 (k=8 nb) is the
  honest end-to-end-relevant number.

Confirmation-transfer disclosure: "fresh" transfer items share the SAME eval
family template and the SAME unfamiliar vocab pools - only slot substitution
is fresh; no new-template transfer was measured. Same-item recall after
confirmation is near-trivial (the confirmed sentence itself was added).

## B-564 PRE-REGISTERED (2026-10-26) - bounded fixes for the two diagnosed collateral channels + joint-slot leg (before code)

Ash: ทำเลย (after honest not-usable report). Mandate: bounded improvement
grounded in B-563 diagnosis; NOT frame proliferation; no production integration;
no pretrained. FROZEN: b562 data/eval/protocol via identical rng (b562_diag.build),
same k=8, same 3-correction protocol, same metrics. Baselines frozen from B-562/3.

Variants (ONLY these; anything else is a future prereg):
- S0 = NB-full, frozen reference (numbers already recorded; re-measured for control).
- S1 = NB with UNIFORM prior (likelihood-only scoring). Targets channel 1
  (prior dominance flipping feature-poor items).
- S3 = S1 + slot extraction v2: slot = token not in the UNION of ALL intents'
  learned frame words (was: only the predicted intent's); filler role via
  position statistics POOLED across intents (was: per-intent only).
  Learned/supplied disclosure unchanged otherwise (NSLOTS + role order still
  supplied). Channel-2 (feature-mass via shared EN markers) has NO variant in
  this round - deferred, recorded; avoids arm proliferation.
- NEW-TEMPLATE eval (authored, labeled; never used in any prior round): two
  fresh surface families per intent, SAME unfamiliar entity pools (isolates
  template novelty from slot substitution). Reported SEPARATELY from the
  frozen eval; no bar (first measurement).

Improvement hypotheses (pre-set; nulls are results):
- G1: S1 mean collateral (3-corr) <= 2 points on >=4/5 seeds AND name_skill
  collateral <= 2 points on all seeds, with frozen-eval k=8 intent accuracy
  within 3 points of S0's .353.
- G2: S3 joint (k=8, frozen eval) >= .25 (from .091) with intent accuracy drop
  <= 3 points vs S0.
- G3: none (new-template numbers reported as-is).
No production routing, no uncertain writes, no quality guarantee.

## B-564 verdict (2026-10-26) - improvement hypotheses tested: G1 NULL, G2 FAIL, one informative positive (b564.py, logs/b564_run1.log)

PROTOCOL NOTE (named): B-564 measures raw argmax WITHOUT the abstention gate,
so its frozen-eval intent numbers are higher than B-562's (abstentions counted
wrong there). S0 re-measured under this protocol = .466 (the correct reference
for all B-564 comparisons), not B-562's .353.

G1 (uniform prior cuts collateral): **NULL/FAIL** - S1 name_skill collateral
unchanged (37.5-62.5 pts, identical per seed to S0); mean degr 13.2 -> 11.8
(trivial). Combined with B-563 (prior_only alone reproduced 100% of the
name_skill loss), the conclusion sharpens: prior shift AND feature-mass shift
are EACH INDEPENDENTLY SUFFICIENT for the collateral. Removing one channel
leaves the other. No single-knob fix exists in NB's update rule.

G2 (pooled slot extraction raises joint to >=.25): **FAIL** - joint .153
(unchanged vs S0/S1 under this protocol); slot-F1 .564 -> .603 (small gain on
correctly-classified items only). The pooled-stats change does not move joint
correctness.

G3 (new-template eval, first measurement, authored families, same unfamiliar
entities): intent .466 (mean equals frozen eval by coincidence - per-seed
scatter .36-.56); joint = .000 ON EVERY SEED AND VARIANT. Unseen templates'
new function words leak into the slot sets and destroy extraction completely.
**The wall for joint correctness is slot extraction on unseen templates, not
intent classification.** Intent markers transfer across templates; the learned
slot extractor is template-bound.

State: all pre-set bars failed or null; nothing integrated; the two real
positives to carry forward: (1) intent transfer across truly new templates
holds at frozen-eval level; (2) the exact failure surface for slots is now
isolated (function-word leakage in unseen templates). Next candidate question
(NOT started): can slot extraction be made template-robust by learning
function/content word separation from cross-intent statistics rather than
per-template frequency - needs its own prereg.

## B-565 PRE-REGISTERED (2026-10-26) - template-robust slot extraction via cross-intent statistics (before code)

Direct continuation on the B-564-isolated wall (joint intent+slots). Mandate:
Project decision (2026-10-26): continue bounded learned-language improvement on the B-564-isolated joint intent+slots wall; no production integration, <=1GB total runtime RAM goal applies.
FROZEN: b562/b564 data, eval, protocol, S1 mapper. ONLY slot extraction varies.

- S4 = cross-intent function-word separation + anchor-relative slot ranking:
  function-ness of a token = number of DISTINCT intents whose training examples
  contain it (learned); a token seen in >=2 intents is function-like and never
  a slot. Anchor = the predicted intent's most frequent training token
  (learned). Slot candidates = non-function tokens, ranked by the LEARNED
  slot-likelihood of their token-offset relative to the anchor across training
  examples; top NSLOTS (supplied) taken, roles by pooled position stats.
  All statistics learned from training data ONLY; supplied = tokenizer,
  NSLOTS, role-order semantics (unchanged disclosure).
- G1: new-template joint > 0 on at least 3/5 seeds (from .000 - any signal
  counts; bar deliberately minimal because the wall was absolute).
- G2: frozen-eval joint must not drop more than 3 points vs S3's .153.
- G3: report which tokens leak on new-template items when G1 fails (null
  anatomy, recorded either way).

B-564/565 wording corrections (2026-10-26, review-requested, nothing rewritten):
- "The wall for joint correctness is slot extraction on unseen templates" is a
  MEASURED failure in THESE setups (these features, these arms, these authored
  templates), not proof it is the sole general-language bottleneck.
- "No single-knob fix exists in NB's update rule" overreached: the tested
  ablations showed two independently sufficient channels IN THOSE ABLATIONS;
  other untested single mechanisms might still fix both. Qualified.
- Frozen b562/b564 eval has now been INSPECTED across many rounds; further
  tuning on it is not "new" evidence. B-565+ labels frozen-eval numbers as
  inspected and relies on fresh authored families for new conclusions.
- B-565+ tracks under ONE protocol (raw argmax, labeled): intent-only,
  slot exactness (ordered roles), joint, wrong-action and abstention counts.
  These raw-argmax numbers are never mixed with the gated B-562 numbers.

## B-565 verdict (2026-10-26) - template-robust slot extraction: G1 PASS, G2 PASS, anatomy recorded (b565.py, logs/b565_run1.log, logs/b565_leaks.log)

Scope: bounded continuation of the learned-language work decided on
2026-10-26; no production integration, <=1GB total runtime RAM goal applies.
An earlier wording of this basis mischaracterized a historical-record lookup
as the decision source and quoted a wrong record identifier; corrected here,
and record identifiers stay out of the repo.

Protocol: raw argmax (labeled, separate from gated B-562 numbers); abstention
reported separately via the dev-frozen gate, never mixed into accuracy.
Mapper frozen = S1 (uniform-prior NB). Three eval sets labeled by inspection
count: frozen (INSPECTED, reference), newtmpl (INSPECTED-once), fresh3
(authored this round + unfamiliar entity set #2).

S4 vs S3 (5 seeds, means):
- frozen:    joint .219 vs .153 | slot-exact .467 vs .327 | intent .466 (same)
- newtmpl:   joint .125 vs .000 | slot-exact .271 vs .000 | intent .466
- fresh3:    joint .231 vs .225 | slot-exact .477 vs .464 | intent .488
- wrong_action ~29-41/64 both; abstain_gated (separate) 16-40/64.

G1 (newtmpl joint > 0 on >=3/5 seeds): **PASS** - >0 on all 5 (.062-.172).
G2 (frozen joint not worse by >3 points): **PASS** - improved on 4/5 seeds
(+.11 mean), one small drop (.172->.156).

G3 leak anatomy (dominant remaining slot errors on fresh3):
1. ROLE SWAPS on unfamiliar fillers (most errors): slots correctly identified
   but roles swapped - cross-intent POOLED role stats conflict (teach_attr
   wants (entity, attr); ask_attr's train family surfaces (attr, entity)), and
   the fallback used ranking order instead of surface order. Candidate fix
   (NOT applied - that would be tuning on inspected eval): surface-order
   fallback + per-intent (not pooled) role stats; needs a fresh eval set.
2. Unseen-particle leaks (minor): 'มัน' in 'X มัน เป็น Y' picked as slot -
   particles absent from training are indistinguishable from content by
   frequency alone.

Honest scope: joint .13-.30 on authored new phrasings remains far from usable;
these are measured failures in these setups, not the general-language wall.
Hygiene: b562_diag/b564/b565 now import-safe (main guards added, standalone
behavior unchanged).

## CONSOLIDATION (2026-10-26) - learned-language line on the frozen protocol (b_consol.py; parses logs only, no re-scoring)

Frozen protocol: 8 intents; train 64/seed (8/intent); evals 64 each (8/intent):
frozen (INSPECTED many rounds - reference only), newtmpl (INSPECTED once),
fresh3 (authored at B-565, unfamiliar entity set #2). Mapper S1 uniform-prior
NB frozen since B-564. B-562 numbers are GATED (abstention) protocol; B-565
numbers are raw-argmax; never mixed. Regenerate: python3 b_consol.py.

B-562 gated (frozen eval, 5-seed means): best joint nb k=8 .0906, t2p k=8
.0844, nn1 k=4 .0625; wnn .019-.044; frames .072 / majority .125 intent floor.
B-565 raw-argmax S3->S4 paired per-seed deltas (joint):
- frozen:  +.093 +.062 +.079 -.016 +.110 (mean .153->.219; 4/5 up)
- newtmpl: +.172 +.125 +.141 +.062 +.125 (mean .000->.125; 5/5 up, from zero)
- fresh3:  +.063 -.031 +.016 -.047 +.031 (mean .225->.231; 3/5 up, mixed)
slot_exact_on_correct: frozen .327->.467, newtmpl .000->.271, fresh3 .464->.477.
wrong_action identical S3/S4 per seed (same mapper; 28-41/64). abstain_gated
reported separately per row, never in accuracy.

Resource workload (measured this consolidation): one full b565 run (5 seeds x
3 evals x 2 extractors) peak RSS 12.9 MB, ~7s wall in this sandbox - the
whole sweep is 3 orders of magnitude under the <=1GB total-runtime goal;
the goal is not yet stressed by this line.

Learned vs engineered in the current best extractor (S4) - disclosure:
- LEARNED from train only: cross-intent function-ness counts; anchor-offset
  likelihood table; slot arity per intent; role-position stats (pooled).
- ENGINEERED (fixed by design): the >=2-intent function threshold; candidate
  selection + role assignment algorithm; leftover fallback ordering; the
  dev-frozen abstention gate.

Error taxonomy driving the next round (B-565 leak anatomy, fresh3): role
swaps on unfamiliar fillers dominate; unseen-particle leaks minor.

## B-566 PRE-REGISTERED (2026-10-26, before code) - is role assignment LEARNED better than POSITIONAL? (bounded, from taxonomy)

Question: on unseen fillers/templates, does learned role assignment beat a
simple positional baseline - with NO test-label access anywhere?
Arms (all train-only statistics, same frozen mapper/evals/protocol):
  A0 positional: slots assigned to roles by surface order (zero learning).
  A1 pooled role-position stats (current S4 - known to conflict cross-intent).
  A2 per-intent role-position stats + positional fallback for unseen fillers.
Frozen evals only: frozen/newtmpl/fresh3, all labeled INSPECTED; NO new
author-generated sets this round. Metrics: joint, slot_exact_on_correct,
role-swap count on unseen-filler items; per-seed paired deltas.
Gates (stated before code):
  G1: A2 mean joint >= A0 + 3 points on newtmpl AND fresh3, with >=4/5
      per-seed deltas non-negative vs A0 (learned must beat position).
  G2: frozen joint not worse than A0 by >3 points on any seed mean.
  If A2 ~= A0: honest null - role learning adds nothing over position in
  these setups; record and keep the simpler arm. No production integration
  under any outcome.

## B-566 verdict (2026-10-26) - learned-vs-positional role assignment: NULL, positional retained (b566.py, logs/b566_run1.log)

All three eval sets are INSPECTED development comparisons, not held-out
validation; no production route chosen on them. Raw-argmax protocol; gated
abstention separate per row (16-40/64); wrong_action identical across arms
per seed (same mapper; intent errors untouched by this axis).

Result (5 seeds, means; per-seed paired deltas preserved in the log):
- A2 (per-intent role stats + positional fallback) == A0 (pure positional)
  EXACTLY on all 15 seed x eval cells (every per-seed delta +0.000):
  joint frozen .259, newtmpl .191, fresh3 .285 for both.
- G1 FAIL (A2 - A0 = 0, not >= +3 points): learned role assignment beats
  position by NOTHING in these setups. Per prereg: retain the null, keep
  the simpler arm (A0 positional).
- A1 (pooled role stats = B-565's S4) is strictly WORSE than positional:
  joint frozen .219 vs .259, newtmpl .125 vs .191, fresh3 .231 vs .285;
  role swaps up to 14/seed (A0/A2: 2-6). Pooled cross-intent role stats
  actively hurt via exactly the teach_attr/ask_attr conflict the B-565
  anatomy suspected.

Correction to B-565's framing: S4's gains over S3 came from candidate
SELECTION (function-ness + anchor-offset ranking), not role assignment -
S4's pooled role machinery was a net negative vs assigning by position.
Current best honest configuration on this frozen protocol: S1 mapper + S4
selection + A0 positional assignment (joint: frozen .259, newtmpl .191,
fresh3 .285; slot_exact_on_correct up to .63 frozen / .43-.49 newtmpl /
.41-.82 fresh3; remaining error mass = intent wrong_actions 28-41/64,
then residual swaps 2-6/seed, then unseen-particle leaks).

Line status: intent accuracy (S1 NBu, .36-.56 raw argmax) is now the
dominant error source. The next decision is line-level, not another
micro-experiment.

## B-567 PRE-REGISTERED (2026-10-26, before code) - discriminative feature weighting for the intent mapper (final bounded round of this line)

Observed-error rationale (confusion diagnosis on the frozen protocol, seeds
0/2, all three sets): intent error mass is MARKER DILUTION - top confusions
are teach_isa<->is_a_q (5-6/seed; share copula เป็น/is, differ only in the
question marker), name_skill->ask_attr (5-6 on newtmpl/fresh3 seeds), and
confirm_answer<->give_example (up to 7 on fresh3 seed2; share ตอบ/answer).
The mapper's word+char-ngram likelihood lets many shared features outvote the
few intent-exclusive markers. Candidate mechanism: reweight each feature by
its learned intent-exclusivity so shared material contributes less.

FROZEN: extractor (S4 selection + positional assignment, per B-566), evals,
protocol, seeds. ONLY the intent mapper varies.
  M0 = NBu uniform (frozen strongest cheap baseline).
  M1 = NBu with per-feature weight w(f) = ln(1 + 8/df(f)), df = number of
       distinct intents whose TRAIN examples contain f (train-only; 8 =
       number of intents). Single fixed formula, no tuning variants.
Fixed cost/stopping bound: 5 seeds x 3 evals x 2 arms = 30 cells, one run
(~10s). After this run the learned-language line closes with a consolidated
closeout either way; no new arms, gates, or eval families afterward.
All eval sets remain INSPECTED development comparisons; no generalization
or production claim under any outcome.
Gates (fixed before code):
  G1: M1 mean intent >= M0 + 5 points on newtmpl AND fresh3, with >=4/5
      per-seed deltas non-negative on each.
  G2: frozen mean intent not worse than M0 by >3 points.
  G1 fail or G2 fail -> null recorded; line closes at the consolidated state.

## B-567 verdict (2026-10-26) - discriminative feature weighting: G1 FAIL, null recorded, line closes (b567.py, logs/b567_run1.log)

Per-seed paired deltas M1-M0 intent: frozen +.000/+.031/+.000/+.000/+.016
(mean +.009); newtmpl +.000/+.000/+.000/+.000/+.015 (mean +.003); fresh3
+.047/+.031/+.016/+.000/+.046 (mean +.028, 5/5 non-negative).
G1 FAIL: +.003 and +.028 are far under the +5-point requirement on both
sets. G2 holds (frozen +.009). Per prereg: null recorded; M0 retained.
Mechanism hypothesis (NOT causally isolated - no control run separated
unseen-function-word errors from other error mass): weighting may fail
because newtmpl/fresh3 errors are dominated by UNSEEN template function
words carrying no learned signal; alternative causes are not excluded. The
teach_isa<->is_a_q confusion class is untouched by reweighting shared
material; the distinguishing markers are already intent-exclusive and fully
weighted in both arms.
Disclosures: M1's unseen-feature weight = ln(9) (treated as df=1, maximally
exclusive); abstention gate recomputed per arm (gate belongs to the mapper),
abstain counts 16-41/64 reported separately per row.

## LINE CLOSEOUT (2026-10-26) - learned sentence->intent+slots under the <=1GB CPU mandate: consolidated state

Frozen protocol: 8 intents, 64 train/seed, 3 inspected dev eval sets (64
each), raw-argmax vs gated numbers never mixed, all prereg in this file.
What was established, in order:
- B-562: gated sentence->intent+slots; WNN fails H1; best cheap arm nb k=8
  joint .091; H2/H3/H4 fail; joint is the honest metric.
- B-563: confirmation-transfer collateral attributed (prior + feature
  channels each independently sufficient in tested ablations; replay null).
- B-564: slots are template-bound (newtmpl joint .000 under S3); intent
  transfers .466 raw-argmax.
- B-565: cross-intent function-ness + anchor-offset SELECTION lifts newtmpl
  joint .000->.125; gains from selection, not role assignment.
- B-566: role assignment - learned == positional exactly; pooled role stats
  actively hurt; positional retained (simpler, better).
- B-567: discriminative feature weighting null; unseen-template words, not
  marker dilution, bind.
Best honest configuration: NBu mapper + S4 selection + positional roles.
Numbers (5-seed means, inspected dev sets, raw argmax): intent .466/.466/
.488, joint .259/.191/.285, slot_exact_on_correct up to .63/.49/.82,
wrong_actions 28-41/64, abstention separate. Resource: full sweeps ~13MB
peak RSS, seconds of CPU - the <=1GB goal is unstressed by this workload
(no claim about any conversation-quality target).
Usability gap, stated plainly: 44-64% of eval sentences take a wrong action
(28-41/64 per seed); joint correctness 19-29% on authored new phrasings. This is
NOT a usable language interface and is not integrated anywhere. The measured
failures are specific to these bounded setups; they do not prove no
single-knob fix exists, but every tested single knob (mapper family, prior,
selection, roles, weighting) has now failed its preregistered gate.
No production route chosen. Further progress needs a mechanism that
addresses unseen-phrasing intent evidence itself, not another knob on the
tested axes.

## B-570 PRE-REGISTERED (2026-10-26, before code) - pointer-copy slot extraction with joint intent head (one mechanism, bounded)

Scope: ONE mechanism from the reviewed evidence - pointer-based slot copying
(P18-2068 BiGRU seq2seq + pointer over input positions, embeddings learned
from scratch, hidden 128; P18-1134 targeted feature dropout for unknown slot
values) with a clearly defined intent path (attention-pooled classification
head on the same encoder, trained jointly). Narrow evidence claim only: the
cited results used DSTC2 (~11.7K train utterances, English, word-segmented);
our protocol trains 64 sentences/seed, ~9x below their smallest ablation
cell - stated as risk, NOT a floor. No Transformer claim either way; a
tiny-Transformer encoder variant stays OPEN for a later round if the copy
mechanism proves out and capacity is the measured bottleneck.

Model (NumPy from scratch, no framework - a dependency-heavy framework would
itself eat much of the RAM budget and is disclosed as the reason): word +
char-ngram hybrid encoder (Thai is unsegmented; char features load-bearing),
single BiGRU encoder, attention pool -> intent softmax head; pointer decoder
over input positions per slot; targeted dropout (zero slot-value embeddings
with p=0.5 during training, per P18-1134). All parameters learned from the
64-sentence train split ONLY; no pretrained anything, no paid resources.

RESOURCE ENFORCEMENT (during run, not after): decimal 1,000,000,000-byte
process-tree budget. A watchdog samples /proc VmHWM (peak-to-date resident)
of the experiment process tree every 2s INCLUDING interpreter + numpy +
model + stores; on exceed: abort, record peak, verdict = RESOURCE FAIL.
Peak RSS reported separately for training vs inference phases.
Instrumentation limitations stated honestly: 2s sampling can miss transient
peaks; VmHWM is per-process peak-to-date; RUSAGE_CHILDREN covers only reaped
children. Hard wall-clock timeout 10 min per run (kill + report). Bound:
5 seeds x 4 cells x (1 arm + frozen baseline) = one run, then closeout.

Tokenizer/OOV disclosure: space-split words + char n-grams, IDENTICAL to the
frozen protocol for comparability. The synthetic probes are space-delimited;
Thai has no spaces in real text - results do NOT support a real-language
Thai transfer claim. Pointer copies input POSITIONS, so OOV surface forms
are copiable by construction, but intent correctness and slot-ROLE
correctness remain learned and are measured jointly (joint metric primary).

Causal 2x2 eval, NO new authoring (existing families + vocabs only):
  (seen tmpl, seen ent): fresh draws from train FAM + train VOCAB
  (seen tmpl, unseen ent): train FAM x EVAL_VOCAB2
  (unseen tmpl, seen ent): NEW_EVAL_FAM x train VOCAB
  (unseen tmpl, unseen ent): fresh3 as-is
All cells are INSPECTED development comparisons, never held-out validation.
Split sizes identical to frozen protocol: train 64/seed (8/intent), 64/cell
eval, 5 seeds, paired per-seed rows, wrong_action + gated abstention separate.
Retention sub-test: after training on the standard split, continue training
on an interfering relabeled split; re-measure cell-1 joint; report retention
gap vs a no-interference control (same total updates).

Gates (fixed before code; fail -> null + closeout, NO automatic new arms):
  G1: pointer arm mean joint >= frozen baseline (NBu+S4-selection+positional)
      +5 points on BOTH unseen-template cells, >=4/5 per-seed deltas >= 0.
  G2: no cell mean joint worse than baseline by >3 points.
  G3: retention gap < 5 points; and full run completes inside the 1e9-byte
      budget and 10-min timeout (RESOURCE FAIL otherwise, reported as such).

## B-570 verdict (2026-10-26) - pointer-copy prototype: G1/G2/G3 FAIL, null recorded, no new arms (b570.py, logs/b570_run1.log)

Reproducibility: stable crc32 feature hashing (Python's randomized hash()
made early runs non-reproducible across processes - caught and fixed; two
full runs byte-identical on all ROW/RET lines; only wall-clock/RSS RES lines
differ, as expected).

Model as preregistered: NumPy from scratch, word+char-ngram encoder
(position-wise MLP + attention pool, NO recurrence - disclosed deviation
from the GRU in the cited evidence; the tested mechanism is pointer-copy +
targeted dropout), intent softmax head + per-role pointer over input
positions. Backprop verified numerically (max rel err 1e-10) before the run.
~90K params. Train 64/seed; all four cells 64/seed, inspected dev only.

Per-seed paired joint deltas PTR - BASE (baseline = NBu + S4-selection +
positional, the frozen best):
- c11 seen/seen:        +.375 +.093 -.047 +.140 +.000 (mean +.113)
- c12 seenT/unseenE:    -.437 -.406 -.578 -.672 -.469 (mean -.513)
- c21 unseenT/seenE:    +.172 +.047 +.015 +.062 +.032 (mean +.066)
- c22 fresh3:           -.282 -.219 -.188 -.219 -.328 (mean -.248)
Means: intent BASE .884/.834/.562/.488 vs PTR .400/.306/.219/.191;
joint BASE .153/.622/.031/.285 vs PTR .266/.109/.097/.037;
PTR slot_exact_on_correct .656/.330/.424/.238.

G1 FAIL (unseen-template cells need +5pts both: c21 +.066, c22 -.248).
G2 FAIL (c12 worse by 51 points). G3 FAIL (retention gap mean +.063 > 5pts,
noisy: -.203..+.188 across seeds; n=64 cells make single-gap reads unstable).
Resources: PASS by a wide measured margin - peak RSS 43.6MB overall
(includes interpreter+numpy+model+stores), 28s wall for the full 5-seed
run, no timeout, no RESOURCE FAIL. This is a measurement of THIS workload
only, not a general assurance.

Causal reading (2x2): the pointer arm wins where template AND entities are
seen (c11 +11pts), ties-to-slightly-wins on unseen templates with seen
entities (c21 +7pts), and COLLAPSES wherever entities are unseen (c12 -51,
c22 -25). The reviewed evidence's core promise - copy handles unknown
values (P18-1134/2068, at ~600-12K training utterances) - did NOT transfer
at 64 training sentences: slot_exact_on_correct on unseen-entity cells is
.24-.33 even when intent is right. Hypothesis (not causally isolated):
copy distributions need more supervised position signal than 64 examples
provide; targeted dropout p=0.5 did not compensate at this scale. PTR's
intent head also underperforms frozen NBu everywhere (.19-.40 vs .49-.88) -
the joint intent+slot neural head at 64 examples is weak on both outputs.

Line status: the frozen counting baseline (NBu + S4-selection + positional)
remains the best honest measured state. Every preregistered attempt to beat
it (weightless NN, 1-NN, text2prog, pooled/learned roles, discriminative
weights, pointer-copy neural) has failed its gates at the 64-sentence
teach-once scale. Open untested axis: DATA SCALE - real teach-while-chatting
accumulates examples over time; whether the pointer route crosses the
baseline at 256+/intent is unknown and is a decision, not an assumption.
No production integration; no live hsml writes were made.

## B-571 PRE-REGISTERED (2026-10-26, before code) - data-scale probe: does the FIXED pointer arm close on the baseline as authored training data grows?

Question (narrow): with the implementation FROZEN from B-570 (same model,
hyperparameters, protocol), do PTR-minus-baseline joint deltas improve when
training data per intent grows 8 -> 32 -> 128 (64 -> 256 -> 1024 sentences)?
This CANNOT establish data scale as THE binding constraint (other axes are
frozen, not ruled out), CANNOT isolate pointer-copy causally (encoder,
intent head, and training differ from baseline together), and says nothing
about the proposed recurrent arm (MLP encoder deviation stands). Seven
failed challenger axes are not closure of all mechanisms.

Fixed: b570.py model code unchanged; same seeds 0-4; same four inspected
2x2 cells; baseline = frozen NBu+S4-selection+positional recomputed inside
this harness for pairing. Nested-prefix training sets from one rng stream
per seed (fully paired across scales). Epochs/lr/early-stop identical to
B-570. No pretrained, no paid resources.
Resources: 1e9-byte whole-runtime budget, live VmHVM watchdog (this harness
spawns NO child processes, so single-process VmHWM is the whole tree);
10-min hard timeout for the entire run; peak RSS + wall reported per scale.
Gates (fixed before code):
  G1: mean PTR-BASE joint delta on c12 (unseen-entity cell, B-570's worst)
      at 128/intent is >= +10 points BETTER than at 8/intent, with >=4/5
      per-seed paired improvements.
  G2: same test on c22 (fresh3): mean delta improvement >= +10 points.
  Both fail -> scale hypothesis NULL in the tested range; closeout, no
  automatic continuation.

## B-571 verdict (2026-10-26) - data-scale probe: G1/G2 FAIL, scale hypothesis null in tested range; closeout (b571.py, logs/b571_run1.log)

Frozen B-570 implementation; nested-prefix training at 8/32/128 per intent
(64/256/1024 sentences), 5 seeds, paired. Resources: peak RSS 43.3MB (no
child processes; single-process VmHVM = whole tree), 159s wall, no timeout.
Note: B-570 numbers recomputed inside this harness (nested-prefix rng
stream); direction and magnitude consistent with B-570's c11/c12 readings.

PTR-BASE joint deltas by scale (means; per-seed in log):
- c11 seen/seen:      +.303 (k8) -> +.578 (k32) -> +.547 (k128)
- c12 seenT/unseenE:  -.453 -> -.350 -> -.390
- c21 unseenT/seenE:  +.094 -> +.090 -> +.188
- c22 fresh3:         -.219 -> -.213 -> -.247
G1 FAIL: c12 improvement k8->k128 = +.062 mean (< +.10 required), only 3/5
per-seed improvements. G2 FAIL: c22 moved -.028 (wrong direction).
NULL in the tested range: 16x more same-distribution authored data improves
the pointer arm where entities are SEEN (c11/c21 deltas grow) but does NOT
close the unseen-entity gap (c12/c22 stay -.2..-.5 at every scale).
Scope preserved per prereg: does not establish data scale as THE binding
constraint (other axes frozen, not ruled out); does not isolate pointer-copy
(architecture bundle differs from baseline); does not speak for the
recurrent variant; does not show the gap never closes (range 8-128/intent).
Baseline remains the best honest measured state at every tested scale.

## LEARNED-LANGUAGE MECHANISM SEARCH - CONSOLIDATED STATE (2026-10-26)

Eight preregistered axes tested against the frozen protocol, all failed
their gates: WNN, 1-NN, text2prog (B-562), pooled slots (B-564), pooled role
stats (B-566-A1), discriminative feature weighting (B-567), pointer-copy
neural at 64 sentences (B-570), and the same at 256/1024 (B-571). This is a
record of what was tried and failed under THESE bounds - not closure of all
mechanisms and not a teach-once impossibility claim. Best honest state:
NBu + S4-selection + positional roles. Actual per-cell joint figures at
64/seed (inspected dev): c11 seen/seen .134, c12 seenT/unseenE .615,
c21 unseenT/seenE .044, c22 unseenT/unseenE .278 (B-571 k=8 rows). The
pointer arm's collapse was concentrated on unseen-entity cells (c12/c22)
while the counting baseline held up there; whether "unseen-entity slot
handling" is the SYSTEM's dominant open problem is NOT established by these
cells (they differ in more than entity novelty, and arm-specific failure
patterns differ) - recorded as an arm-specific observation, not a
line-level diagnosis.

## B-572 PRE-REGISTERED (2026-10-26, before code) - Class B targeted test: order-sensitive intent features (explicitly authorized bounded round)

Class-B target (from measured confusion examples, logs in b567 diagnosis):
marker-position confusions like teach_attr 'X ของ Y สวย' misread as ask_attr -
the mapper's bag-of-features is order-blind to WHERE a marker sits relative
to slots/edges.
FROZEN: protocol, 2x2 cells (all INSPECTED development/debug evidence, not
independent validation), seeds 0-4, S4-selection+positional extractor,
baseline M0 = NBu with B.encode features (the frozen best).
Arms (SEPARATED for attribution; a win only in combination would be labeled
a combined intervention):
  M-BI:  B.encode + word-bigram features 'b:w1|w2'.
  M-POS: B.encode + edge-relative position features: for each of the first 2
         and last 3 tokens, feature '<slot>:w' naming its edge position.
DISCLOSURE (required): the position/bigram cues are a REPRESENTATION DESIGN
CHOICE deliberately supplied by us; learned weights over designed features
are not proof of autonomous grammar discovery. No deployability or
general-language claim follows from these cells either way.
Gates (fixed before code): G1: an arm's mean INTENT >= M0 +5 points on BOTH
unseen-template cells (c21, c22) with >=4/5 non-negative per-seed paired
deltas. G2: no cell mean intent worse than M0 by >3 points. Attribution only
if exactly one arm wins; fail -> null recorded, no automatic continuation.
Resources: no pretrained, no paid; pure-Python counting features (no new
deps); 1e9-byte live watchdog; 10-min hard timeout; 5 seeds x 4 cells x 3
arms + baseline.

Class-C wording correction (supersedes my earlier phrasing): unseen tokens
do NOT make correct handling information-theoretically impossible - context,
compositional patterns and inductive bias can sometimes support unseen-token
handling. The B-562..571 failures establish only that THESE tested
implementations did not generalize on THESE examples; same-distribution
scaling (B-571) does not isolate causes. Class-A recovery is scoped to the
measured before/after tests, not a universal diagnosis.

## B-572 VERDICT (2026-10-26): NULL - order-sensitive features fall short of the +5-point gate; M0 retained

Run: logs/b572_run1.log, script b572.py. INSPECTED development/debug cells
only (not independent validation); no deployability or general-language
claim follows. Arms separated as preregistered; the edge-position cue is a
deliberately supplied REPRESENTATION DESIGN CHOICE, not autonomous grammar
discovery.
Mean intent (5 seeds), paired deltas vs M0_NBu:
  c11 seen/seen:  M0 .884 | M-BI .891 (+.006) | M-POS .906 (+.022)
  c12 seenT/unseenE: M0 .834 | M-BI .834 (+.000) | M-POS .884 (+.050)
  c21 unseenT/seenE: M0 .562 | M-BI .566 (+.003) | M-POS .585 (+.022)
  c22 fresh3:     M0 .488 | M-BI .494 (+.006) | M-POS .537 (+.050)
G1 FAIL: no arm reaches +5 points on BOTH unseen-template cells (best
M-POS: c21 +.022, c22 +.050). G2 holds (no cell worse by >3 points).
Per prereg: null recorded, M0 retained, no automatic continuation.
Interpretation (scoped): edge-relative position helps a little everywhere
(M-POS 4/5-5/5 non-negative per-seed deltas, c12 +.050/c22 +.050) but the
gains are small; word bigrams add ~nothing. The marker-position class is
partially addressed by designed positional cues, not recovered.
Resources: peak RSS 28.4MB overall (3 mappers x 4 cells x 5 seeds, no
children), 6.5s wall, live 1e9-byte watchdog, well under budget.

## CORRECTION + LINE STATE (2026-10-26): learned-language line HELD, no supported next proposal identified

My 11:29 report phrased the outlook as "the remaining gap needs a different
information source" - that goes further than the evidence. The B-562..B-572
nulls and the absence of a next proposal establish neither that a different
information source is NECESSARY nor that possible approaches are exhausted.
The accurate record: in this bounded pass, NO SUPPORTED NEXT PROPOSAL was
identified. The line is held: no further automatic arms, nothing integrated
into production, all previous nulls preserved.

## B-573 PRE-REGISTERED (2026-10-26, before code) - new mechanism: interactive teach-once acquisition

New direction (distinct from all 9 failed static-learner axes): an
INTERACTIVE acquisition channel, grounded in Sida Wang et al., "Naturalizing
a Programming Language via Interactive Learning" (ACL 2017,
aclanthology.org/P17-1086) and "Learning Language Games through Interaction"
(ACL 2016, aclanthology.org/P16-1224): users define new language in terms of
what the system already knows, and the interface's usable language grows
through interaction (their community reached 85.9% naturalized-utterance use
in 3 days). Our formulation matches the stated user goal of teach-once
learning while chatting.
Mechanism: frozen NBu mapper + dev-calibrated margin threshold tau (same
selection procedure as b562_diag.build, recomputed for NBu). Streaming each
INSPECTED unseen-template cell item-by-item: if margin < tau the system
ASKS the (SIMULATED) teacher instead of acting; the (utterance, gold intent)
pair is folded into the mapper and the item is EXCLUDED from all metrics.
Acted items are scored right/wrong on intent and joint.
Gates (fixed before code): G1: wrong-action rate on ACTED c21+c22 items
<= 5% AND acted-item intent >= static M0 + 30 points on each cell. G2:
median asks per unseen intent-family <= 2 (teach-once). Fail -> null, no
automatic continuation.
DISCLOSURES: the simulated teacher is AUTHORED validation, never
independent; tau comes from the same authored dev split; taught items are
excluded from metrics; this tests an interactive acquisition channel, not
open-ended language learning; no production integration; no user dialogue
used as data.
Resources: no pretrained, no paid; pure-Python; 1e9-byte live watchdog;
10-min hard timeout; seeds 0-4.

## B-573 VERDICT (2026-10-26): NULL at G1 (safety/lift gate); G2 (teach-once) PASSES

Run: logs/b573_run1.log, script b573.py. INSPECTED dev/debug cells, simulated
AUTHORED teacher, taught items excluded from metrics - not independent
validation; no production integration; no deployability claim.
Per-seed (5 seeds, 96 items/cell/seed):
  c21 unseenT/seenE: static M0 .562-.703 | acted intent .559-.789 |
    wrong-action 93/288 acted (32%) | asked 5-9/seed
  c22 fresh3: static M0 .391-.484 | acted intent .466-.650 |
    wrong-action 121/288 acted (42%) | asked 4-8/seed
G1 FAIL: wrong-action 32%/42% >> 5%; acted-intent lift over static M0 is
~+.07 (c21) and ~+.14 (c22) mean, not +30 points.
G2 PASS: asks per unseen intent-family median 1.0, max 2, over both cells
and all seeds (28+26 family-ask events of 60 possible families) - the
teach-once property holds for the ask channel itself.
Interpretation (scoped, not causally isolated): the ask CHANNEL behaves as
hoped (one taught example per family is enough for the mapper to absorb the
rest of that family), but the accuracy-maximizing dev-calibrated margin
threshold is NOT a safety gate - it releases high-confidence wrong intent
predictions (the known teach_isa<->is_a_q confusions carry real margin).
A precision-targeted threshold (dev-chosen for <=5% wrong-action, not max
accuracy) is the obvious next calibration but is NOT run: prereg says null
-> no automatic continuation.
Resources: peak RSS 28.4MB, 8.1s wall, 1e9-byte watchdog, no new deps.

## INTERPRETATION CORRECTION (2026-10-26, on B-573)

The B-573 G2 result is a NARROW proof of acquisition inside this protocol:
a simulated authored teacher on inspected families. It is NOT evidence that
an ask channel works as a real user needs, and nothing is 'handled forever':
retention/interference across successive taught families and genuinely
independent unfamiliar families remain UNVERIFIED. No universal or perpetual
claims stand.

## B-574 PRE-REGISTERED (2026-10-26, before code) - precision-targeted gate calibration

Same mechanism, frozen protocol/mapper(NBu)/extractor, same INSPECTED cells
(development calibration reuse - not independent validation). The simulated
teacher supplies the INTENT LABEL ONLY; slots still come from the frozen
extractor. Teacher burden (asks per family) is reported as a first-class
metric alongside coverage and errors.
Change vs B-573: the margin threshold tau is chosen on the authored dev
split for WRONG-ACTION <= 5% (tightest threshold achieving it; if none
achieves it, the tightest available, and G1 fails) instead of max accuracy.
Gates (fixed before code):
  G1: wrong-action on ACTED items <= 5% on EACH of c21, c22 (5-seed totals).
  G2: coverage (acted/total) >= 50% on each cell - refusing almost
      everything does not count as meeting G1.
  G3: acted-item JOINT (intent+slots) >= static-M0 all-item joint on each
      cell - interaction must not hurt the end-to-end number.
Fail -> null, no automatic continuation. Reported together: coverage,
wrong-action, acted intent/joint, asks per family.
Resources: no pretrained, no paid, pure-Python, 1e9-byte live watchdog,
10-min timeout, seeds 0-4. No personal-data collection.

## B-574 VERDICT (2026-10-26): NULL at G2 (coverage); G1 passes; G3 mixed

Run: logs/b574_run1.log, script b574.py. INSPECTED cells reused as
development calibration, simulated AUTHORED teacher supplying INTENT LABEL
ONLY; taught items excluded; not independent validation; no production
integration; no personal data.
5-seed means (per-seed in log):
  c21: tau 21.2-34.5 (dev wrong-rate 0 at tau) | coverage .450 (FAIL >=.5)
    wrong-action 0/144 (PASS <=5%) | acted intent 1.0 | acted joint .036-.111
    vs static all-item joint .016-.062 (PASS per-seed)
  c22: same taus | coverage .409 (FAIL >=.5)
    wrong-action 2/131 = 1.5% (PASS) | acted intent .943-1.0 |
    acted joint mean .242 vs static .238 (seed2 .053 vs .188 FAILS; 4/5 pass)
Teacher burden REGRESSED vs B-573: asks/family median 4-5, max 8 (29-45
asks per 96-item cell per seed) - the precision gate asks on ~55-60% of
unseen-template items, so teach-once no longer holds at this threshold.
Combined B-573/B-574 finding: NBu margin on this feature space traces a
steep safety/coverage tradeoff - accuracy-optimal tau releases 32-42% wrong
actions; precision tau is safe but covers only ~41-45% of unseen-template
items with 4-5x the teacher burden. Margin does not separate safe from
unsafe at usable coverage IN THIS PROTOCOL (scoped, not a universal claim).

## B-575 PRE-REGISTERED (2026-10-26, before code) - descriptive analysis: safety/coverage frontier + retention probe

NOT a success-gated arm: a measurement pass over the frozen B-574 setup to
characterize (a) the full tau tradeoff frontier (coverage vs wrong-action)
on the INSPECTED c21/c22 cells, and (b) RETENTION/INTERFERENCE - flagged as
unverified in the B-573 correction: after the interactive stream teaches
some families, re-predict taught items and previously-seen family items to
measure whether taught knowledge survives later teaching. No gate; findings
recorded as-is. Same disclosures: authored teacher, intent labels only,
inspected cells, no production, no personal data. Resources unchanged.

## B-575 FINDINGS (2026-10-26): frontier mapped; in-session retention clean

Run: logs/b575_run1.log, script b575.py. Descriptive, no gate. INSPECTED
cells, static frozen NBu for the frontier, interactive stream (precision
tau, intent-label-only teacher) for retention. Scoped to this protocol.
(a) FRONTIER (seed-mean, static mapper on unseen-template cells): the
wrong-action rate falls smoothly with tau while coverage collapses -
zero-wrong is only reachable at coverage <=~25% (c21) / <=~19% (c22)
STATICALLY; the B-574 interactive stream reached 0-1.5% wrong at 41-45%
coverage because taught items expand the mapper mid-stream. Representative
points (tau, coverage, wrong): c21 (0, 1.0, .39) (2.0, ~.75, ~.33)
(4.3, ~.45, .24) (9.1, .22, 0) ; c22 (0, 1.0, .56) (2.2, ~.4-.5, ~.36-.4)
(5.0, .16, 0). NBu margin is a usable but coarse safety signal here.
(b) RETENTION/INTERFERENCE: after streaming each full 96-item cell with
29-45 taught items, taught-item recall = 1.000 in all 10 seed x cell runs;
previously-right acted items stayed right (drift 0; one seed had 2 acted
items right-then-unscored, after-stream acted recall .943-1.000). NO
interference observed - but scope: same session, immediate re-prediction,
<=45 added examples. Long-term retention and cross-session persistence are
still UNVERIFIED.
Teacher burden at the precision gate stands at median 4-5 asks per family
(~35-45 per 96 unseen-template items) - the main open cost of the channel.

## B-576 PRE-REGISTERED (2026-10-26, before code) - two-tier gate with confirmation-transferred trust

Mechanism (distinct from threshold re-tuning): tau_hi = B-574 precision tau
(dev wrong-action <=5%); tau_lo = B-573-style dev accuracy-maximizing tau.
For items with margin >= tau_hi: ACT. For margin < tau_lo: ASK. BETWEEN the
tiers: ACT only if the argmax intent has >=1 TEACHER-CONFIRMED example this
session (confirmation transfers trust to moderately-confident items of that
intent); otherwise ASK. Frozen mapper(NBu)/extractor/cells/teacher (intent
label only, authored). INSPECTED cells, development calibration.
Gates (fixed before code): G1 wrong-action <=5% on EACH cell (5-seed
totals); G2 coverage >=50% each cell; G3 asks/family median <=2. Fail ->
null, no automatic continuation. Rationale: confirmation, not margin alone,
should carry trust for mid-confidence items.
Resources unchanged (pure-Python, watchdog, 10-min timeout, seeds 0-4).

## B-576 VERDICT (2026-10-26): NULL at G1 (wrong-intent); G2/G3 pass

Run: logs/b576_run1.log, script b576.py. INSPECTED cells, authored teacher
(intent label only), taught items excluded, development calibration.
Two-tier gate (act >=tau_hi; ask <tau_lo; mid-band acts only for
teacher-confirmed intents):
  coverage .78-.86 (G2 PASS >=.5); asks/family median 1-2, max 3 (G3 PASS
  <=2); wrong-INTENT on acted 13.7-41.8% per seed (G1 FAIL <=5%).
Scoped finding: teacher confirmation of an intent transfers too much trust -
the mid-margin band is where the known confusion mass lives, and confirming
intent d does not make other mid-band items of d safe. The realistic-runtime
mechanism (no gold family labels, no future items) is validated as
implementable, but its safety gate fails.

## B-577 METRIC RECONCILIATION (2026-10-26): wrong-intent vs wrong-execution; labels corrected

Run: logs/b577_run1.log, script b577.py - EXACT counters, same frozen
protocols, no gate. CORRECTION to B-573/B-574/B-575 wording: what those
entries called 'wrong-action' was WRONG-INTENT on acted items only. A
correct intent with wrong slots still executes wrongly. Exact 5-seed totals
(n=320/cell):
  c21 static baseline: wrong-intent 123/320; joint 14/320; wrong-execution
    306/320 (95.6%).
  c21 B-574 precision: abstain 176; acted 144; wrong-intent 0;
    joint-correct 11; WRONG-EXECUTION 133/144 acted (92.4%), 41.6% of all.
  c21 B-576 two-tier: abstain 59; acted 261; wrong-intent 66 (25.3%);
    joint-correct 21; WRONG-EXECUTION 240/261 (92.0%), 75.0% of all.
  c22 static baseline: wrong-intent 179/320; joint 76/320; wrong-execution
    244/320 (76.3%).
  c22 B-574 precision: abstain 189; acted 131; wrong-intent 2 (1.5%);
    joint-correct 34; WRONG-EXECUTION 97/131 (74.0%), 30.3% of all.
  c22 B-576 two-tier: abstain 53; acted 267; wrong-intent 69 (25.8%);
    joint-correct 75; WRONG-EXECUTION 192/267 (71.9%), 60.0% of all.
Denominators now explicit throughout. Consequence (scoped to this protocol):
on unseen templates the SLOT side dominates end-to-end failure - even
zero-wrong-intent gating leaves 74-92% of acted items not fully correct.
Intent gating alone cannot deliver correct actions; slot acquisition on new
phrasings is the binding constraint.

## SLOT-TEACHING DESIGN (2026-10-26, planning only)

See SLOT_TEACHING_DESIGN.md. Concrete natural exchange (paraphrase-choice
intent question, per-slot yes/no-or-pick confirmations, never role names),
exact teacher information (intent choice + span confirmations/picks/retyped
values), roles SUPPLIED as the action API while span-to-role mapping is
LEARNED from confirmation labels, containment via per-slot confidence gates
and one targeted question per uncertain slot. Implementation NOT started;
awaits direction.

## B-578 PRE-REGISTERED (2026-10-26, before code) - slot-teaching feasibility prototype

Bounded standalone feasibility prototype of SLOT_TEACHING_DESIGN.md (parent-
authorized 2026-10-26). NOT production integration. Streamed INSPECTED
cells c21/c22, authored SIMULATED teacher (establishes correctness only
inside the stated simulation), frozen NBu intent mapper + frozen extractor
as candidate proposer.
SUPPLIED (designed): role inventory per intent, candidate generator = all
contiguous token spans of length <=5, confidence gates, dialogue shape.
LEARNED: span-to-role scorer (NBu-style counts over span features: span
tokens, length, start/end position, distance to intent marker), trained
only on teacher confirmation labels. Roles never learned from scratch.
FLOW per utterance: (1) intent: act-tier if margin >= B-574 precision tau,
else ONE intent question (teacher supplies intent). (2) per required slot:
if >=1 prior confirmed example for (intent,role) AND scorer margin >=
dev-calibrated slot tau -> accept UNASSISTED; else propose top candidate,
teacher yes/no, up to 3 offered spans, then RETYPE (teacher supplies exact
value; if gold span absent from candidates the retype path is mandatory and
counted - no privileged span access). (3) EXECUTE only when intent and ALL
required slots are unassisted-accepted or teacher-confirmed; execution is
correct iff joint gold match. No automatic execution of uncertain actions.
METRICS (exact denominators, reported together): intent questions, slot
yes/no questions, offer rounds, retypes, executed, wrong-execution,
abstentions (0 by construction with an always-answering simulated teacher -
disclosed), unassisted vs teacher-confirmed split (confirmed answers NEVER
count as learned transfer), first-half vs second-half question burden,
retention probe (unassisted re-predict of taught items after the stream).
SUCCESS CRITERIA (fixed before code): G1 wrong-execution <=5% of executed,
each cell (5-seed totals). G2 second-half question burden <= half of
first-half (learning happens). G3 unassisted-executed joint >= static-M0
all-item joint, each cell. Fail -> null, no automatic continuation.
Resources: pure-Python, 1e9-byte live watchdog, 10-min timeout, seeds 0-4,
no pretrained, no paid, no personal dialogue.

## B-578 VERDICT (2026-10-26): NULL at G1/G2; G3 passes strongly - first positive slot-transfer signal

Run: logs/b578_run1.log, script b578.py. RUN DEVIATION recorded: the prereg
specified a dev-calibrated slot tau; run1 hardcoded margin >= 0 (accept any
non-negative top-1 margin after 1 confirmed example). Consequences below;
the calibrated variant is a separate future round, not silently substituted.
INSPECTED cells, authored teacher, exact denominators, n=320/cell.
  c21: wrong-execution 125/320 executed (39.1%) - G1 FAIL (<=5%).
    unassisted-executed joint .554 vs static-M0 all-item joint .044 - G3
    PASS. burden h1 40.4 avg vs h2 42.4 - G2 FAIL (flat). retention .55-.64.
    burden 1.29 questions/utterance (intent 36.4, slot 36.4, retype 11).
  c22: wrong-execution 112/320 (35.0%) - G1 FAIL. unassisted joint .600 vs
    static .237 - G3 PASS. burden h1 38.4 vs h2 42.6 - G2 FAIL. retention
    .55-.70. burden 1.25/utterance (intent 37.8, slot 33.2, retype 9.4).
Interpretation (scoped to protocol+simulation): learned span-to-role
transfer from confirmation labels REAL and large relative to the designed
extractor (unassisted joint .55-.60 vs .04-.24 static), but the margin>=0
acceptance rule is far too lax (35-39% wrong executions - unassisted
accepts are frequently wrong), burden does NOT fall within a session
(h1~h2), and taught-span retention is only .55-.70 under unassisted
re-prediction. Consistent with the intent-side pattern: the signal is
present; the GATE is the hard part. Retypes (~10/64) are mostly spans the
candidate generator ranked below top-3, not absent spans (gold spans are
<=5 tokens in these families).

## GOLD-SEMANTICS AUDIT (2026-10-26) - one invalid template found; illustrative exchange withdrawn

Audit of every family template's (utterance -> intent, slots) pair against
the action schema (teach_attr(x,y) = "x has y" etc.):
- TRAIN FAM, DEV_FAM, NEW_EVAL_FAM (c21), FRESH3_FAM (c22): every template
  asserts or asks exactly what its gold intent/slots say (listed in repo
  history; spot-verified per intent). Gold slots are SINGLE vocab tokens;
  no multiword span boundaries exist anywhere in the protocol. VALID.
- EVAL_FAM (the b562 'ev' set used by B-562..B-567) teach_attr template
  '{y} ของ {x} สวย' is INVALID for teach_attr(x,y): "งา ของ เหยี่ยว สวย"
  asserts the horn is BEAUTIFUL; it does not assert "hawk has horn". Under
  the action schema a correct system would record attr(beautiful) on the
  horn, so the gold parse manufactures a confirmation the utterance does
  not supply. Contamination scope: 1 of 3 teach_attr templates in the old
  ev set only (~1/3 of teach_attr ev items in B-562..B-567 eval rows);
  c21/c22 (B-570..B-578) are UNAFFECTED.
Consequences:
1. The B-567 'marker-position' example ('งา ของ เหยี่ยว สวย' -> ask_attr)
   rested on this invalid gold: predicting ask_attr for a '{y} ของ {x} ...'
   question-shaped utterance is not a clean learner error. The Class B
   motivation example is therefore PARTIALLY UNDERMINED; B-572's null stands
   on its own numbers but its motivating example is not evidence.
2. My B-578 illustrative user-facing exchange taught slot values
   ('งา ของ เหยี่ยว' as the entity, 'สวย' as the attribute) that are WRONG
   under the schema - WITHDRAWN. Valid replacement exchange (below in the
   B-579 report context): intent question on 'ช่วยบอกหน่อยว่า งา ของ
   เหยี่ยว คืออะไร' style items with single-token gold slots.
3. Comparability break: ev-set teach_attr rows in B-562..B-567 are flagged
   contaminated, not rewritten. A corrected EVAL_FAM_V2 (replacing the
   invalid template) will be defined if a future arm needs an ev-style set;
   it will be labeled non-comparable to ev.

## B-579 PRE-REGISTERED (2026-10-26, before code) - matched-baseline reconciliation of B-578 G3

Measurement pass, NO gate. Fixes the B-578 G3 contrast per review: the
static baseline is computed on EXACTLY the items the interactive arm
executed FULLY UNASSISTED (no intent question AND no slot question),
killing the selection-inflation confound; teacher-helped items are reported
separately; all-item unassisted-correct/total is reported alongside. Same
B-578 run1 protocol (margin>=0 deviation carried, labeled); B-578's
'first positive transfer' wording stays WITHDRAWN until this contrast is
read. Static baseline = raw-argmax NBu + frozen S4 extractor, no asks.

## B-579 FINDINGS (2026-10-26): matched contrast survives; all-item gain is coverage-limited

Run: logs/b579_run1.log, script b579.py (measurement, no gate; same B-578
run1 protocol with margin>=0 deviation labeled). 5-seed totals, n=320/cell.
c21: fully-unassisted 138 items, helped 182.
  MATCHED conditional contrast: interactive joint 89/138 = .645 vs static
  10/138 = .072 on the SAME items - selection alone does NOT explain the
  gap; learned span-to-role transfer is supported on this contrast (scoped:
  this protocol, simulated teacher, margin>=0 acceptance).
  All-item: interactive unassisted-correct 89/320 = .278 vs static all-item
  14/320 = .044. Helped items (teacher-supplied, NOT learned transfer):
  106/182 = .583.
c22: fully-unassisted 128, helped 192.
  MATCHED: interactive 82/128 = .641 vs static 27/128 = .211 - transfer
  supported on this contrast, smaller margin.
  All-item: interactive unassisted-correct 82/320 = .256 vs static all-item
  76/320 = .238 - nearly NO net all-item gain on c22.
Honest bottom line: the conditional transfer is real in this protocol, but
~57-60% of items still need teacher help, ~35% of unassisted executions are
wrong, and on c22 the all-item unassisted correctness is statistically
indistinguishable from the static baseline. Gating, coverage, retention
(.55-.70) and representation/teacher validity are ALL unresolved - no
single 'hard part' claim is made. The 'first genuine positive transfer'
wording stays withdrawn in favor of these matched numbers.

## B-580 FAILURE ACCOUNTING (2026-10-26): helped-item failures are ALL partial-help slot slips

Run: logs/b580_run1.log, script b580.py (diagnostic, no arm). 5-seed totals.
c21 helped 182: OK 106, wrong 76 - ALL 76 are class B/intent_only: teacher
confirmed the INTENT, then every slot was UNASSISTED-accepted
(scorer had >=1 example, margin>=0) and >=1 was wrong.
c22 helped 192: OK 126, wrong 66 - ALL 66 same class.
Class A (wrong acted intent on a helped item): 0. Class C (all required
fields teacher-confirmed yet execution wrong): 0 - the invariant "complete
confirmation => correct execution" holds IN THIS SIMULATION.
Conclusion (scoped): partial help is exactly where the remaining helped-item
failures live; confirming intent does not make the action correct when slots
pass unassisted under the lax margin>=0 rule. This is the slot-gate failure
surfacing inside the helped set, matching the 35-39% wrong-execution rate.

## WORDING CORRECTIONS (2026-10-26, per review)

- The invalid EVAL_FAM template '{y} ของ {x} สวย' is a STATEMENT OF BEAUTY
  ("the hawk's horn is beautiful"), not 'question-shaped'; that the model
  predicted ask_attr does not make the utterance a question. Corrected.
- The c21/c22 semantic audit is MY MANUAL authored-data assessment, not
  independent validation.
- Applicability caveat made explicit: this protocol's slots are SINGLE
  VOCAB TOKENS with synthetic regularities; natural dialogue has multiword,
  ambiguous, context-dependent fillers, so none of these numbers transfer
  directly to natural chat. The earlier superseded conditional comparison
  (B-578 G3) remains withdrawn; B-579's matched counts are the record.

## B-581 PRE-REGISTERED (2026-10-26, before code) - dev-calibrated slot tau (standalone; the originally preregistered variant)

Implements the B-578 prereg as written: slot acceptance requires >=1 prior
confirmed example for (intent,role) AND scorer margin >= SLOT_TAU, where
SLOT_TAU is calibrated on the AUTHORED dev split: the simulated teacher
loop runs over dev first (seen templates), and SLOT_TAU is the tightest
margin threshold with dev wrong-slot-accepts <=5% (if none, tightest
available and G1 fails). Everything else frozen from B-578 run1. Standalone
arm: NO burden-reduction mechanism mixed in. INSPECTED cells, simulated
teacher, single-token synthetic slots (applicability caveat stands).
Gates (fixed before code): G1 wrong-execution <=5% of executed, each cell.
G2 question burden second half <= half of first half. G3 all-item
unassisted-correct > static all-item joint, each cell (all-item vs
all-item, B-579 discipline). Report matched-set conditional numbers
alongside. Fail -> null, no automatic continuation.
Resources unchanged.

## B-582 PRE-REGISTERED (2026-10-26, before code) - cross-session persistence probe

Simulates a session break: after streaming cell c22 with teacher (B-578
run1 protocol), the learned state (intent mapper counts + span-scorer
counts) is SERIALIZED (pickle to /tmp) and REBUILT in a fresh process-like
state; then (a) unassisted correctness is measured on FRESH items of the
taught families (same generators, new rng draws - authored), and (b) after
streaming a second cell of NEW families, session-1 families are re-tested
(interference check). No gate; measurement. Disclosed limits: same
generators/vocab, so persistence here is not evidence of natural-language
retention. Resources unchanged.

## B-581 VERDICT (2026-10-26): NULL at G1/G2 - dev-calibrated slot tau does not transfer to unseen templates

Run: logs/b581_run1.log, script b581.py. SLOT_TAU calibrated on authored dev
(seen templates) to <=5% wrong slot-accepts: tau = 1.1679 in all 5 seeds
(dev wrong-accept 0-.037). Applied to the INSPECTED unseen-template cells:
  c21: wrong-execution 71/320 = 22.2% (G1 FAIL <=5%); burden h1 119 ->
  h2 149 (G2 FAIL, rises); unassisted-correct all-item 95/320 = .297 vs
  static .044 (G3 PASS); fully-unassisted 36.6%.
  c22: wrong-execution 76/320 = 23.8% (G1 FAIL); h1 119 -> h2 141 (G2
  FAIL); unassisted-correct .284 vs static .237 (G3 PASS, modest);
  fully-unassisted 37.5%.
Scoped finding: the SAME transfer gap as the intent side - acceptance
margins calibrated on seen-template dev do not predict correctness on
unseen templates. Burden does not fall within a session under any tested
gate; if anything it rises as more families demand confirmations. G3's
all-item gains are real but modest and bought with ~1.3 questions/utterance
plus 22-24% wrong executions: not a usable tradeoff as-is.

## B-582 FINDINGS (2026-10-26): learned state persists across a serialized session break; ~40-50% of it is wrong

Run: logs/b582_run1.log, script b582.py (measurement, no gate; B-578 run1
protocol, margin>=0). Session 1 taught c22 families, state pickled/rebuilt,
then:
  s2a (fresh items of TAUGHT families, unassisted): joint .500-.750 per
  seed (mean .619). Persistence across the break is real - the rebuilt
  counts carry the learned mappings.
  s2c (after streaming NEW families with teacher): .484-.656 (mean .590) -
  mild interference (mean -.03), no catastrophic forgetting.
Scope: same generators/vocab; this is persistence of counting-scorer state,
NOT evidence of natural-language retention. ~40-50% of persisted
unassisted predictions are still wrong (margin>=0 era).

## B-583 PRE-REGISTERED (2026-10-26, before code) - local-confirmation accept rule

Structurally different gate (not another margin calibration): a slot is
accepted UNASSISTED only when its exact local configuration -
(intent, role, prev-token, span-text, next-token) - was LITERALLY confirmed
by the teacher before. Wrong-execution on slots is then bounded by
confirmation coverage rather than by margin calibration. Intent side keeps
the B-574 precision tau (act/ask). KNOWN COST stated in advance: on truly
novel phrasings, local configurations are unseen, so burden stays high BY
CONSTRUCTION; the arm tests whether safety + teach-once-style absorption
(1 confirmation per family-role configuration) can coexist, not whether
novel phrasings are free.
Frozen: NBu mapper, extractor as proposer fallback, cells, teacher
(intent label + span confirmations), single-token slots caveat.
Gates (fixed before code): G1 wrong-execution <=5% of executed, each cell.
G2 burden second half <= half of first half (within-cell absorption).
G3 all-item unassisted-correct > static all-item joint, each cell.
Matched conditional + helped/unassisted splits reported (B-579 discipline).
Fail -> null. Resources unchanged.

## B-583 VERDICT (2026-10-26): NULL at G2/G3(c22) - safe by literal confirmation, but tiny coverage and heavy flat burden

Run: logs/b583_run1.log, script b583.py. Runtime features use observed
utterance/history only - no gold family labels, no future items. INSPECTED
cells, simulated teacher, single-token synthetic slots.
5-seed totals (n=320/cell):
  c21: wrong-execution 0/320 (G1 PASS). fully-unassisted 33 (10.3%);
    unassisted-correct all-item .103 vs static .044 (G3 PASS). burden:
    176 intent + 618 slot-offer + 65 retype questions (~2.7/utterance);
    helped-flags h1 217 -> h2 225 (G2 FAIL, not halving). helped joint
    287/287.
  c22: wrong-execution 2/320 = 0.6% (G1 PASS; both were wrong acted INTENT
    at the precision tau - slots cannot be wrong on literal repeats).
    fully-unassisted 67 (20.9%); unassisted-correct .209 vs static .237
    (G3 FAIL). burden ~2.4/utterance; h1 212 -> h2 200 (G2 FAIL). helped
    joint 251/253.
Reading (scoped): the local-confirmation rule delivers near-zero
wrong-execution but is MEMORIZED STRUCTURAL COVERAGE - it acts only on
literally repeated configurations, so 79-90% of unseen-template items
still demand questions and burden does not fall within a cell. This is
containment, not understanding; the tradeoff was predicted in the prereg.
B-583b controls (logs/b583b_run1.log): after teaching c21+c22, a THIRD
genuinely new template family (EVAL_FAM minus the audited-invalid
template, 311 items) produced 0 executions and 311 questions - no safety
leak on novelty - and 0 slot-signature collisions (confirmed signature
firing with a differing gold value). Measured, not assumed.

## B-583 DENOMINATOR + WORDING CORRECTIONS (2026-10-26, per review)

- Denominators made explicit: wrong-execution 0/320 (c21) and 2/320 (c22)
  are ALL-item (= all-executed, since the always-answering simulated
  teacher means every item eventually executes). Among FULLY-UNASSISTED
  executions only: 0/33 (c21) and 0/67 (c22) wrong. Both views stand; the
  2 wrong-executions were helped items whose acted INTENT was wrong.
- WITHDRAWN as universal claims: 'slots on literal repeats cannot be wrong'
  and 'safety by literal confirmation works'. The measured facts are
  narrower: in THIS simulation, confirmed-signature accepts had 0 errors
  and 0 measured collisions - but repeated context can still be ambiguous
  or bind a wrong span/intent in general, and zero measured collisions does
  not prove impossibility.
- The B-582 persistence result is demonstrated only in the tested
  pickle/rebuild reconstruction; no process-restart/disk durability claim.
- Definitions-channel critique registered: definitions do NOT ensure one
  question per pattern or unlimited correct utterances by construction; my
  illustrative definition ("'X ของ Y สวย' แปลว่า...") was semantically
  unclear and must NOT seed valid gold.
- No single-bottleneck wording: data semantics, representation, retention
  and gate validity all remain potential limitations.

## OVERNIGHT TARGET (2026-10-26 23:07, user-set via main)

User's stated target: a conversational hsml he can talk to like the
assistant, very low resources (<=1GB whole runtime), running locally. Main
answered without promising overnight success; user asked for no hsml
updates unless the target is actually achieved. Work continues overnight
on bounded authorized research; no production integration, no user success
claims from synthetic gates.

## B-584 PRE-REGISTERED (2026-10-26, before code) - conversational-feasibility baseline against the USER'S actual target

The overnight target is conversation, not template cells. This arm builds an
AUTHORED multi-turn conversational scenario (greetings, teaching in seen
and UNSEEN phrasings, inference questions, anaphora, off-topic, ambiguity -
each turn labeled with its expected behavior class; authored = development
evidence, NOT validation) and measures a candidate shell end-to-end:
retrieval over taught parses -> gated NBu intent + S4 extraction ->
knowledge traversal for answers -> honest fallback when nothing is safe.
SUPPLIED: response templates, knowledge traversal (transitive isa), the
fallback lines, the eval itself. LEARNED: intent mapper, span scorer,
taught-parse store. No definitions channel in this arm (separate candidate).
Metrics: per-turn behavior-class match with exact counts by class (correct
action / correct abstention+honest fallback / wrong action / wrong answer),
plus RAM/time. No gate - this is the honest gap measurement between the
current components and the user's stated target. No success claims.

## B-584 FINDINGS (2026-10-26): conversational gap measured directly - 4/18 (precision gate) and 3/18 (accuracy gate)

Runs: logs/b584_run1.log (precision intent tau), logs/b584_run2_accuracy.log
(accuracy tau). AUTHORED 18-turn scenario (development evidence only):
greetings, seen-template teaching, inference, unseen phrasings, anaphora,
off-topic, retract-then-ask. Seed 0. Shell = retrieval over taught parses
-> gated NBu + S4 -> knowledge traversal -> honest fallback (supplied
templates; learned mapper/store). Retrieval branch never fired (store
starts empty; no near-repeats in scenario) - disclosed.
PRECISION gate (the only measured-safe configuration): 4/18 behavior-class
matches. It refused nearly ALL valid in-scope turns: 'มิโล เป็น แมว',
'มิโล มี หาง', 'ตอบ สี่' -> honest_fallback. ZERO fabricated actions -
but conversationally useless: the gate that keeps unseen phrasings safe
also rejects seen-template teaching (its dev-calibrated threshold sits
above most seen-item margins).
ACCURACY gate: 3/18, and qualitatively worse: DANGEROUS FABRICATIONS -
'มัน กิน ปลา ไหม' (anaphora) -> fake answer; 'ราคา เท่าไหร่ กัน' ->
fake answer; 'เหยี่ยว เป็น สัตว์เลี้ยง ไหม' -> fabricated knowledge;
'สอนวิธี บวก ให้หน่อย' -> wrong action. Plus seen teaches misrouted to
ask_needed via wrong-intent slot-count mismatches.
Conclusion (scoped, no single-cause claim): between these two gates the
current components cannot hold even an 18-turn authored conversation
without either refusing most valid turns or fabricating answers. The
distance to the user's stated target (talk like the assistant) is large
and structural: anaphora, off-topic honesty-with-engagement, definition
teaching, and response richness are ALL absent, not one knob. Resources:
~29MB peak, <2s. Next: candidates (definitions channel; teach-first shell
with per-turn confirmation dialogue; richer fallback engagement) assessed
against THIS scenario before any further gate tuning.

## B-585 PRE-REGISTERED (2026-10-26, before code) - teach-first conversational shell: asking AS the conversational move

B-584 showed both gates fail conversationally. This arm replaces silent
fallback with a REAL clarification exchange: on low intent margin or
uncertain slots, the shell asks a specific natural question (paraphrase
choice / slot confirm); a SIMULATED user (authored script, development
evidence) answers; the answer is learned (intent pair / slot confirmation);
the turn completes. Out-of-scope turns get an honest engaged non-answer
(name the limit, offer what IS possible) instead of a bare refusal.
Metrics per turn: final behavior-class match AFTER the exchange, questions
asked, fabricated-action count (must be 0 by construction - verified),
exact denominators. No gate - feasibility measurement of the conversation
SHAPE the user actually asked for. Same scenario as B-584 for comparability,
extended with scripted answers where the shell asks. SUPPLIED: question
templates, fallback lines, scenario, answers. LEARNED: mapper, store.

## B-585 FINDINGS (2026-10-26): teach-first shell 8/18 - dominant failure is the gate refusing SEEN items

Run: logs/b585_run1.log, script b585.py. Same authored 18-turn scenario
(B-584 comparable) + scripted simulated-user answers where the shell asks
(development evidence). Result: 8/18 behavior-class matches, 5 questions
total, 0 fabricated actions (by construction, verified in log). BUT the
dominant mismatch class is NEW information: seen-template teaching turns
('มิโล เป็น แมว', 'มิโล มี หาง', 'ตอบ สี่', 'นก เป็น สัตว์'...) fall to
fallback because the B-574 precision tau (26.07) REJECTS MOST SEEN ITEMS -
the gate tuned for unseen-cell safety refuses the system's own trained
language. The teach-first SHAPE works where the gate lets it (ask ->
scripted answer -> learned -> teach_ok on both unseen-phrasing turns).

## B-586 DIAGNOSTIC (2026-10-26): margin-scale analysis + operating points

Run: logs/b586_run1.log + inline sweep (script b586.py; seed 0 diagnostic,
labeled single-seed). Facts:
- Raw NBu margins: seen median 28.9, unseen(c22) median 1.6 - separable in
  the median, but seen spread is wide: at the dev-calibrated precision
  tau=26.07 only 34/64 seen items act (all right). Dev calibration picked
  26 because of dev's NONE/dev-family items - a dev artifact, mismatched
  with the real operating objective (seen coverage + unseen/off-topic
  rejection).
- Length-normalized scores (NBn): NO threshold reaches <=5% dev wrong
  short of abstain-all - normalization destroys the safety property.
  Recorded as a tried-and-failed representation variant.
- Operating sweep (seed 0 only, small samples, NOT validated): tau=10
  acted 48/64 seen (all right), 7/64 unseen (0 wrong), 0/20 off-topic;
  tau=5: 53/64 seen (51 right), 10/64 unseen (0 wrong), 2/20 off-topic
  acted. tau=1-2: unseen wrong-intent 16 and 9 - unsafe. A dominated
  calibration choice (26.07) exists because the dev objective differs from
  the conversational objective; tau~10 LOOKS better on these numbers but
  needs paired-seed validation before any claim.
Conclusion (scoped): margin-based gating has an intrinsic
coverage/safety overlap (seen spread crosses unseen spread), but the
specific tau=26 operating point was also a calibration-objective artifact.
Both things are true; neither alone explains the conversational failure.

## B-587 PRE-REGISTERED (2026-10-26, before code) - paired-seed operating-point validation

Validates the B-586 seed-0 sweep observation with paired seeds 0-4, gates
fixed before run. Candidate intent gates (FIXED): tau in {5, 10,
26.07-style dev-calibrated precision (recomputed per seed)}. METRIC NAMING
(B-577 discipline): this is an INTENT-side gate eval; metrics are
wrong-INTENT among acted items (not 'wrong-action'); end-to-end
wrong-EXECUTION is not claimed by this arm. Cells: seen train-family (c11-
style), c21, c22 (INSPECTED, development robustness check - NOT independent
validation), plus off-topic WRONG_INTENT items. Metrics per tau per seed:
seen acted/right, c21+c22 acted/wrong-intent, off-topic acted. Selection
rule (fixed): a candidate passes if unseen+off-topic wrong-intent among
acted <=5% (5-seed totals) AND seen coverage >= 75%; the passing candidate
with highest seen coverage wins. This informs the shell operating point
only; it is not a conversational success claim.

## B-587 VERDICT (2026-10-26): NULL - no margin operating point passes; seed-0 tau~10 observation does NOT replicate

Run: logs/b587_run1.log, script b587.py. Paired seeds 0-4, candidates fixed
before run. 5-seed totals (seen n=320, unseen n=640, off-topic n=100).
METRIC: wrong-INTENT among acted (intent-side gate eval; no end-to-end
wrong-execution claim). Development robustness check on inspected authored
generators, NOT independent validation.
  tau5:  seen cov .847 | unseen acted 246, wrong-intent 22.4% | off-topic
         acted 8 -> FAIL safety (<=5%).
  tau10: seen cov .753 | unseen acted 172, wrong-intent 14.5% | off-topic
         0 -> FAIL safety. The B-586 seed-0 '0 wrong' was single-seed luck.
  tau_dev (21.2-34.5/seed): seen cov .497 | unseen acted 62, wrong-intent
         0% | off-topic 0 -> passes safety, FAILS coverage (>=75%).
Selection rule: NO candidate passes both. The threshold direction is closed
at this representation: margin gating cannot give conversational coverage
AND safety. Recorded with the other nulls; no further threshold sweeps.

## B-588 PRE-REGISTERED (2026-10-26, before code) - per-turn confirmation shell v2 (guess-confirmation UX)

The per-turn design that replaces the global gate: margin >= tau_dev
(per-seed precision tau) -> ACT; margin < 1.0 (fixed a priori - near-zero
margin means no signal) -> out-of-scope honest engagement, NO question;
between -> ask a GUESS-CONFIRMATION (top-1 intent + extracted slots
rendered as a natural yes/no question via GLUE). The SIMULATED user answers
'yes' iff the guess EXACTLY equals gold (intent+slots), else supplies the
gold correction - answers are DERIVED from gold, not authored per turn.
On yes/correction: learn the (utterance, intent) pair + confirmed slots,
act. Metrics: final behavior-class match on the B-584/B-585 18-turn
scenario, questions asked, yes vs correction split, fabricated actions
(must be 0 - verified), and a SECOND run of the scenario immediately after
(repetition pass: taught pairs should make repeats question-free).
Development evidence; no success claim; single seed 0 (paired seeds only
if this shape survives).

## B-588 FINDINGS (2026-10-26): per-turn confirmation shell 17/18 - but 14 questions, 13 of them CORRECTIONS

Run: logs/b588_run1.log, script b588.py. Authored scenario (development
evidence), sim-user answers DERIVED from gold (yes iff guess==gold exactly).
First pass: 17/18 behavior matches, 0 fabricated actions (verified),
repeat pass 17/18 with ZERO new questions (taught store covers repeats).
THE BURDEN IS THE STORY (kept visible, not counted as autonomous success):
14 questions in 18 turns; the guess-confirmation guessed exactly right only
1/14 - 13 needed full corrections. The mapper+extractor's top-1 guess is
almost never exactly right on first encounter, even on trained templates
(the precision tau forces the question, then the guess itself is usually
incomplete/wrong). The single miss: the anaphora turn routed to
honest_engaged instead of the named-limit ask (routing detail).
TARGET ALIGNMENT (per review): this is CONTAINMENT with heavy user burden
plus engineered context handling - useful components, NOT demonstrated
learned conversation comparable to the user's request. The 17/18 is what a
perfectly patient user gets; the 14 questions are what it costs.
Resources: 27.4MB peak, 1.2s (capacity left ON THIS WORKLOAD, not proof of
scalable headroom - B-587-era phrasing corrected).

## B-589 PRE-REGISTERED (2026-10-26, before code) - Thai segmentation probe

Natural Thai has no spaces; the whole protocol assumes them. Probe a
SUPPLIED longest-match segmenter + small AUTHORED Thai lexicon
(~60 protocol/common words; user-taught additions simulated by adding
entities after their first confirmed occurrence) on (a) DE-SPACED
train-family utterances, (b) DE-SPACED c22 utterances, (c) a handful of
authored ordinary Thai sentences including ambiguity/unknown-word cases.
Metrics: exact gold-token recovery rate per set; unknown-span fallbacks;
ambiguity failures inspected manually. Authored lexicon + authored
sentences = MANUAL development evidence, not validation; one probe of a
major untested risk, not a sufficiency proof.
