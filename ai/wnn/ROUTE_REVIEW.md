# Bounded route review, 2026-10-27

A materially different candidate exists for narrow composition: typed logical-form search with online word-fragment/subtree weights learned from user-selected outcomes. No inspected source supports the complete conversational target within 1GB. This is a research candidate, not a feasible delivery plan.

## Rank and scope
1. SHRDLURN-style latent compositional semantic learning: closest evidence to language learning from scratch through interaction. Supplied action grammar/executor/curriculum, learned language-to-tree associations, denotation feedback. Unlike current flat intent classification or whole-surface templates, the output is a compositional program. Suitable next question is whether phrase meanings learned separately combine in new nested structures with lower teacher burden.
2. SippyCup / Liang-Potts chart-parser demos: readable reference algorithms but didactic, grammar supplied, full derivation enumeration, eval-based interpreter. Not safe or memory-bounded for deployment; no source code should enter the AGPL-only repository without license review.
3. Overnight canonical paraphrases: useful bounded-domain data construction, but grammar plus paraphrase annotation burden does not satisfy teach-once conversational learning. Not preferred under present target.

## Discriminating study if pursued
Independent fresh implementation only, no integration: fixed typed AST primitives (supplied, inventoried), bounded proposal beam; learned fragment/subtree scores. Predeclare train/test split by semantic tree structure, not entities alone. Test nested combinations never shown in training, paired bilingual phrases sharing one semantic store. Compare flat-intent, memorization, no-feedback, deranged-feedback and oracle-candidate coverage arms. Count correct proposals, semantic errors, beam misses, feedback burden and concurrent-tree RAM. Never execute user-generated Python; sandbox pure AST evaluation only. No automatic fact writes. Stop if oracle candidate coverage fails, control arms match learned arm, teacher cost rises without new-structure benefit, or live RAM exceeds 1e9 bytes.

## Evidence and uncertainty
Primary evidence: https://ar5iv.labs.arxiv.org/html/1606.02447 describes no initial seed lexicon or annotated logical forms, but a fixed compositional action grammar and online feedback. Its beam is 100 candidates per size through eight predicates, not an unbounded search. It documents strategic human adaptation and limits of pragmatics. Thus using it would explicitly shift burden to grounding and candidate selection, not eliminate teaching.
Operational references: https://www-nlp.stanford.edu/software/sempre/ ; https://github.com/wcmac/sippycup ; https://github.com/cgpotts/annualreview-complearning/ . Historical bounded-dialogue context: https://hci.stanford.edu/winograd/shrdlu/ . Data-construction alternative: https://aclanthology.org/P15-1129/ .

No measured memory guarantee, Thai result, bilingual knowledge transfer, personal-assistant breadth or open-ended discourse result was found in these sources. I have not exhausted all alternatives. Candidate evaluation would test a narrower compositional capability, not meet the overnight target. No build started.
