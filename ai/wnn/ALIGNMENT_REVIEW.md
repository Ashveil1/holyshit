# Alignment/outcome feedback review, 2026-10-27

## Correction to B613 interpretation
One update of our weak feature learner is not a replication of SHRDLURN. Equivalent syntax trees can be harmless when the task cares only about denotation. Counts of equivalent trees do not isolate supervision ambiguity as the cause of failure. B613's denotation failure is substantive for its own fixed setup, but its cause remains unresolved among feature representation, update/optimization, candidate biases and feedback. No new build follows from it.

## Distinct mechanisms found

1. **SGOLL local subgraph contrast**. Chen 2012 proposes maintaining online phrase/connected-subgraph co-occurrence counts and ranking by p(graph|phrase) - p(graph|not phrase). Instead of whole-program marginal likelihood alone, it learns a local semantic lexicon from overlapping perceptual/action contexts. This is a materially distinct alignment signal. But the paper uses up-to-4-grams, maximum subgraph size 3, minimum support 10; navigation data contain 3,236 instructions plus 1,011 additional MTurk instructions. Reported lexicon time is 157.30 seconds vs 2,227.63 for the earlier approach, on dual Xeon servers with 32GB installed RAM. That hardware capacity is not measured memory usage, nor a sub-1GB guarantee. Paper explicitly warns that candidate subgraphs can become intractable and memory high. The larger navigation system constructs landmark plans with supplied rules and trains KRISP after pruning; not end-to-end teach-once chat. English/Chinese experiments are not Thai or shared-bilingual knowledge evidence.
Source read: https://aclanthology.org/P12-1045.pdf
Author overview inspected: https://www.cs.utexas.edu/~ai-lab/pub-view.php?PubID=127159

2. **Situated interactive concept instruction (Soar)**. The inspected work claims few examples (1-13), online acquisition and <2s response for grounded concepts. However it uses a static dictionary/grammar to parse utterances, heuristic intent categories, known perceptual feature families and explicit teacher answers about which perceptual property a word describes. Thus its few-example claim is concept grounding on substantial supplied language/architecture, not acquisition of compositional natural language from outcome feedback alone.
Source read: https://arxiv.org/html/2502.20754

3. **Dialogue cost-aware visual concept learning**. DS-TTR plus online visual classifiers studies simulated tutor policies and effort. This supports measuring interaction cost, not treating every oracle selection as a cheap yes/no. It supplies a semantic grammar and focuses on perceptual concepts rather than unrestricted compositional acquisition.
Source read: https://aclanthology.org/W16-3206.pdf

## Recommendation and blocker
No inspected source establishes realistic teach-once compositional alignment within the complete no-pretrained/1GB conversational target. SGOLL is a grounded-alignment candidate, but requires repeated contexts/minimum support and a supplied structured world. Do not silently replace the target with navigation or use its published speed as projected runtime here.

A discriminating study, only after scope is justified, would hold candidate graphs fixed and compare local subgraph contrast vs B613-style global latent feature updates, with matched repeated contexts, unknown alignment gold held evaluator-only, canonical denotation equivalence scoring, and a minimum-support-one arm. Measure learning curves in numbers of genuinely new teacher examples and live concurrent RAM, not just asymptotic speed. An oracle phrase-alignment control would diagnose whether candidate representation supports transfer, without calling that control learned.

Concrete next review point: inspect the SGOLL training/feature/grammar assumptions and available implementation/data license before proposing any reproduction. Require evidence on support-one behavior and actual memory, or record the same blocker. No implementation adopted or new experiment started; no universal impossibility claim; no automatic extension of B613.
