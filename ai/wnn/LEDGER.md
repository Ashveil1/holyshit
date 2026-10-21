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
