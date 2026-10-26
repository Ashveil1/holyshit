# hsml conversational capability plan (2026-10-26, planning doc - NOT a build commitment)

Target (user-stated): talk with hsml like with the assistant; <=1GB whole
runtime; runs locally; no pretrained weights; no paid resources.
Honest frame: full assistant-level conversation is not reachable without
pretrained language models. What IS reachable is a personal system that
converses honestly inside a growing taught domain: remembers what you teach
it, reasons over it, asks when unsure, says what it cannot do, and absorbs
new phrasings from a single correction. The plan below decomposes the gap
measured in B-584/B-585 into components.

## Gap -> component map (from measured scenario failures)

1. GATE (measured null B-587): no global margin threshold gives coverage
   AND safety. Replacement design: PER-TURN confirmation as the safety
   mechanism - act only at very high confidence, otherwise ask a specific
   question; correctness comes from the answer, not the threshold.
   Supplied: question dialogue shapes. Learned: mapper, span scorer,
   confirmed-configuration store. Feasibility: proven in B-583/B-585 at
   ~29MB.
2. THAI SEGMENTATION (unmeasured but structural): the whole protocol
   assumes space-separated tokens; natural Thai has no spaces. A
   dictionary longest-match segmenter with a USER-EXTENDABLE lexicon
   (new words taught as they're confirmed) fits the constraints: supplied
   algorithm, learned lexicon, a few MB. Without this, nothing else
   transfers to real Thai chat. Flagged as the largest transfer risk.
3. REFERENCE (anaphora): 'มัน', 'ของมัน', omitted subjects. Supplied
   recency structure (last-mentioned entities per conversation) + ask on
   ambiguity. Learned: nothing initially. Feasibility: trivial RAM.
4. DEFINITIONS CHANNEL (candidate, unassessed): user states a reusable
   pattern once ("'วิธี X' คือถามเรื่อง X") compiled to a rule/feature.
   Supplied: definition syntax shape. Learned: which definitions exist and
   their confirmed uses. Must NOT be presented as induced grammar;
   one-definition-per-pattern burden and semantic-validity checking are
   open. Assess against the B-584 scenario before building.
5. RESPONSE GENERATION: template + knowledge traversal (supplied);
   richness from taught phrasings later. The assistant-like FEEL mostly
   lives here and in honest engagement; it is design work, not learning.
6. OFF-TOPIC HONESTY: detect out-of-scope (mapper abstention works: 0/100
   off-topic acted at tau_dev) and answer with named limits + offers.
   Supplied lines; no scripted off-topic padding (per main).
7. MEMORY/PERSISTENCE: counting-state serialize/rebuild measured working
   (B-582, reconstruction only). Integrate with hsml's knowledge store
   (supplied glue). Durability across real restarts untested.

## Resource feasibility

All components are counting tables, small lexicons and pickle state.
Measured: ~29MB peak RSS, <10s full experiment runs. A Thai lexicon
(thousands of entries) adds MBs, not hundreds. The 1GB budget has ~30x
headroom at current scale; growth risk is the taught-store over months -
pruning/compaction policy needed eventually (not now).

## Sequencing (each its own bounded eval, preregistered)

A. Per-turn confirmation shell replacing the global gate (builds on B-585).
B. Thai segmentation probe on real Thai sentences (supplied segmenter +
   taught lexicon); measures the transfer risk directly.
C. Reference recency + ask-on-ambiguity in scenario.
D. Definitions-channel feasibility assessment (scenario-based, honest
   supplied-vs-learned).
E. Integration proposal to main WITH evidence; production integration is
   NOT authorized by this plan.
