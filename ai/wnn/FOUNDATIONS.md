# Foundations synthesis (Oct 2026): what the classics demanded, what a faithful implementation is, what we already are, cheap first tests
Labels: [fact] = what the source actually says (URL verified); [interp] = my reading; [test] = cheap first experiment, CPU-only.

## Turing 1950, "Computing Machinery and Intelligence", esp. section 7 Learning Machines
https://doi.org/10.1093/mind/lix.236.433 (text: https://www.cs.toronto.edu/~frank/csc2501/Readings/R1_Turing/Turing-1950.pdf)
- [fact] Split the problem into a "child-machine" (little mechanism, mostly blank) and an "education process"; evolution analogy: structure = hereditary material, changes = mutations, experimenter judgment = selection, but mutations need not be random.
- [fact] Punishment/reward alone is a low-bandwidth channel ("the amount of information ... does not exceed the total number of rewards and punishments"); so teach through "unemotional channels": orders in a symbolic language.
- [fact] Propositions in the store carry STATUS: well-established facts, conjectures, proved theorems, statements by authority; imperatives that fire when classed well-established; meta-imperatives regulate which inference rule to apply when ("If one method has been proved quicker, do not use the slower one").
- [fact] Learned rules have "ephemeral validity" vs the time-invariant base rules; "if they could not be unlearnt they could not produce less than 100% certainty."
- [fact] Include a random element in search when systematic search stalls.
- [interp] Faithful implementation: a small kernel (fixed rules) + a writable store where every rule/fact carries provenance and confidence, revised by later evidence, taught mostly by language, occasionally by reward.
- [interp] Are we a partial instance? YES on several axes, NO on status/revision: P14 curriculum = education process; P15-P22 = teaching through the unemotional channel (language), P20 acceptance = reward signal; but NOTHING in our system carries epistemic status, and no learned rule is ever revised or unlearned.
- [test F-1] (S) Contradiction correction: tell the fact/lexicon memory "my name is X", then "actually my name is Y"; also a wrong-then-right number-word. Criterion: latest wins, 100% on probe set; baseline: current store (overwrites blindly or keeps both, measure which).

## McCarthy 1959, "Programs with Common Sense" (Advice Taker)
http://www-formal.stanford.edu/jmc/mcc59/mcc59.html
- [fact] Intelligence = manipulate declarative sentences by deduction; a program improves by being TOLD advice in declarative form, not by re-coding.
- [interp] Faithful: declarative advice that changes behavior without code edits.
- [interp] Are we a partial instance? Weakly: P22 paraphrase definitions teach new wordings declaratively ("X means Y"). Nothing else takes advice.
- [test F-2] (S) Advice as constraints: accept a stated rule ("order does not matter for add and mul") and use it to shrink the hypothesis space for later examples. Criterion: same accuracy with fewer examples vs P15 baseline at n=24/60.

## Minsky 1961, "Steps toward Artificial Intelligence"
https://doi.org/10.1109/JRPROC.1961.287775 (text: https://cbmm.mit.edu/sites/default/files/documents/steps.pdf)
- [fact] Decomposes AI into search, pattern recognition, learning, planning, induction; heuristic search with subproblem selection; "problem-languages".
- [interp] Are we a partial instance? Our induction is heuristic search (P7-P14) and T3 has the beginnings of a problem-language; no planning/subproblem selection.
- [test F-3] (M) Subgoal selection: on composition tasks (P13 style), pick the subgoal whose input/output differ least from known op signatures. Criterion: P13 6/10 baseline, target 8/10, same seeds.

## Newell & Simon 1959, GPS report
http://people.csail.mit.edu/brooks/idocs/GPS1959.pdf
- [fact] Means-ends analysis: compare current state to goal, pick an operator that reduces the largest difference, recurse on subgoals.
- [interp] Are we a partial instance? No: our search enumerates flat, no difference-measurement. Closest is the text2prog explanation search (match answer backwards), which is one step of means-ends.
- [test F-4] (M) Means-ends induction for 2-op compositions: from the target answer, invert each library op to propose intermediate values, induce each half separately. Baseline: P13 flat composition 6/10; success: 8/10 at <= half tried.

## Solomonoff 1964, "A Formal Theory of Inductive Inference"
https://doi.org/10.1016/S0019-9958(64)90223-2 (text: https://raysolomonoff.com/publications/1964pt1.pdf)
- [fact] Universal induction: predict with the shortest program consistent with data; prior 2^-length.
- [interp] Are we a partial instance? Our enumeration is length-biased (comb list ordering) but acceptance is FIRST fit, not shortest; no 2^-len weighting anywhere.
- [test F-5] (S) Shortest-on-tie + weight explanations by 2^-program-length in text2prog. Baselines: B-001 (first-found) and P15; success: equal accuracy, shorter programs, +pts on ambiguous sentences.

## Hutter, AIXI (2000+)
https://arxiv.org/abs/cs/0004001 , book https://hutter1.net/publ/uaibook2.pdf
- [fact] Optimal agent = Bayes-mixture over all computable environments + expectimax; uncomputable; AIXItl is the bounded version.
- [interp] Are we a partial instance? The soft-credit over consistent hypotheses in P15 is a tiny Bayes mixture over ~21 programs; nothing like expectimax planning.
- [interp] Honest: nothing here is implementable faithfully; what transfers is the mixture weighting (covered by F-5).
- [test] none new.

## Schmidhuber: OOPS (2003) and Godel machine (2003+)
https://arxiv.org/abs/cs/0309048 , https://people.idsia.ch/~juergen/gmweb4/gmweb4.html
- [fact] OOPS: ordered problem solver that reuses solutions of earlier tasks as primitives for later ones, with time-share doubling across candidate programs; Godel machine: self-rewrite only after a PROOF the rewrite is useful.
- [interp] Are we a partial instance? P14 library growth (learned ops become primitives for later tasks) is OOPS's reuse idea in embryo; we lack the time-share doubling and any usefulness check beyond "fits examples".
- [test F-6] (S) OOPS-style scheduling: interleave candidate generators with doubling time shares, ordered by past success frequency (ties into P24 macros). Criterion: same tasks found, <= 50% CPU to first correct program vs P14 ordering.

## Chollet 2019, "On the Measure of Intelligence"
https://arxiv.org/abs/1911.01547
- [fact] Skill is not intelligence: priors and training data can "buy" skill; measure generalization power (developer-aware generalization) at fixed priors/experience; ARC as the proposed yardstick.
- [interp] Are we a partial instance? We already report unseen-scale generalization (1-4 digits) and list hand-given priors per result; we do NOT quantify experience (examples seen) per skill or audit priors systematically.
- [test F-7] (S) Priors/experience audit: every README result gets two columns (priors handed to the system, examples consumed) + freeze eval pack v1. Process change, zero compute.

## Lake, Ullman, Tenenbaum, Gershman 2017, "Building Machines That Learn and Think Like People"
https://arxiv.org/abs/1604.00289 (DOI: https://doi.org/10.1017/S0140525X16001837)
- [fact] Human-like learning needs causal models, intuitive physics/psychology priors, compositionality, learning-to-learn, one-shot learning.
- [interp] Are we a partial instance? Compositionality: yes (programs compose); one-shot: yes in HDC facts and fast-mapping (P15); learning-to-learn: P24 macros are the start; causal models/intuitive theories: no.
- [test F-8] (M) One-shot classification benchmark vs MLP (already backlog T7): make the gap table honest and complete.

## Hebb 1949, Hinton (distributed representations)
https://princetonuniversity.github.io/NEU-PSY-502/_static/pdf/Class%203/Hebb1949.pdf
- [fact] Correlation-based strengthening; assemblies as representation units. Hinton: representation in distributed patterns.
- [interp] Are we a partial instance? P3/P4 cross-pathway association (+18%; later shown STD-mediated not Hebbian - LEDGER B-505) and HDC vectors are direct instances. No new proposal; the connectome line stays low-priority after P5's honest negative.

# Top concrete proposals (ranked by evidence x cheapness)
1. F-7 priors/experience audit + frozen eval pack (S, process; makes every future claim Chollet-proof)
2. F-6 OOPS-style doubling scheduler over generators (S-M; directly attacks our CPU bottleneck)
3. F-5 shortest-program preference + 2^-len weighting (S; Solomonoff, two one-line changes)
4. F-1 contradiction correction / unlearning with status (S; Turing's ephemeral rules)
5. F-4 means-ends composition induction (M; GPS, target P13 6/10 -> 8/10)
6. F-3 subgoal selection (M; Minsky)  7. F-2 declarative advice as constraints (S-M; McCarthy)  8. F-8 one-shot gap table (M; Lake et al.)
