# SGOLL assumption and availability review (2026-10-27)

## Verdict

Source-review closeout, not a reproduction proposal. SGOLL provides a
specific local-alignment mechanism, but the inspected evidence does not
justify it as a teach-once, sub-1GB conversational implementation. No new
build, package execution, pretrained model use or dataset adoption occurred.
This is uncertainty about fit, not proof of impossibility.

## Algorithm and supervision

The primary paper ranks phrase/subgraph co-occurrences by
p(g|w)-p(g|not w), extracting small connected subgraphs from navigation
plans. Defaults are up-to-4-grams, maximum graph size 3, threshold .4,
and minimum support 10. The paper says that minimum support deliberately
suppresses noisy rare-phrase entries, with higher precision/lower recall.
No inspected support-one result was found. Changing support to one would
be our modification, not a source-supported teach-once result.

The larger system supplies rules which turn observed action traces and
world descriptions into landmark plans, prunes them using the learned
lexicon, then trains KRISP. It is not online conversation from a single
outcome selection. The published corpus has thousands of instructions;
Chinese uses translated data and a Stanford Chinese segmenter. No Thai or
shared-bilingual knowledge result follows.

157.30 seconds is lexicon construction time on dual Xeon X5440 servers
with 32GB installed RAM, not total training time or measured RAM. The
paper warns that graph counts and candidate meanings can require high
memory. No measured sub-1GB or support-one guarantee was found.

Primary source: https://aclanthology.org/P12-1045.pdf

## What is actually downloadable

Author homepage links to the navigation project. HTTP failed, but HTTPS
resolved and was read as the intended project:
https://www.cs.utexas.edu/~ml/clamp/navigation/

Its actual linked archive was downloaded for read-only inspection outside
the project, no package code run or imported:
https://www.cs.utexas.edu/~ml/clamp/navigation/downloads/LearningNavigationInstructions.tgz
SHA256: 75c03d75a54d75a7f5f4e4344a059780511c9b5b867319a4436f2469de71cc67
Archive has 524 members, 25,451,877 compressed bytes. Initial 25MB download
cap rejected it; inspected again under explicit 30MB transfer cap.

Archive README dates it August 2011 and describes modified MARCO code
and instructor/follower data for the earlier AAAI paper. Code outside
MARCO is a wrapper; inspection of 221 small text/source files found no
SGOLL/subgraph-generation implementation indicators. This bounds what
was checked; it is not proof no implementation exists elsewhere.

MARCO README explicitly says its POS/sense/PCFG components use trained
models supplied by the original author (trainable from Penn Treebank).
Thus running the archive unchanged would violate the no-pretrained
constraint even though the SGOLL research itself targets language
learning. Old Python2, PyEnchant, SciPy/NumPy dependencies also differ
from a fresh minimal implementation.

Data README says canonical follower paths need not reach the intended
destination; sentence/action alignment discards unalignable examples.
Human semantic annotations exist for evaluation, so they must not leak
into training in any reproduction claiming weak supervision.

## License status

No root archive license or explicit dataset redistribution/adaptation
license was found in inspected READMEs/members. Release-as-is with an
original author's permission is not a clear project-wide reuse grant.
Bundled component sources carry copyright and reference licenses such as
LICENSE.TXT; mixed dependencies need separate review. No AGPL-only
compatibility claim, source copy, integration or data adoption is made.

## Concrete stopping point

The reviewed downloadable artifact is not a verified SGOLL reproduction,
uses pretrained MARCO components, and lacks an established project-wide
reuse/data license. Together with minimum-support-ten evidence and absent
actual memory measurements, that is insufficient for a concrete feasibility
build under this target. Source review stops here rather than continuing
paper-to-paper without a capability hypothesis.

The distinct hypothesis remains local phrase/subgraph contrast could learn
semantic lexical alignments better than whole-program features, but only
with recurring discriminating contexts. Any future proposal must explicitly
accept a different teacher-cost scope, or provide new support-one evidence;
it must separately obtain/replace execution and parser dependencies and
resolve licenses. A source-backed support-one learning curve or a verified
minimal implementation with runtime/teacher costs is the next evidence
checkpoint, not an automatic experiment or a request for user action.

Existing conversational entry failures and B613 denotation NULL remain
unresolved. No result here establishes general target feasibility.
