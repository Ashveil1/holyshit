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
