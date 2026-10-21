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
