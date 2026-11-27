# AUTHOR BRIEF - thai-core v1 (AI path), Phase 3 authoring, family CLAUDE

You are claude-author-01, the claude-family author for a Thai conversational-memory
evaluation set. You are authoring in a FRESH session: the ONLY system knowledge you
may use is in this brief. Never assume capabilities, wording requirements, internals,
dev-set items or failure modes beyond Annex A of the plan.

## Your assignment

Author EXACTLY the 35 items listed below - 5 per category, your slots only, one
scenario per slot. A scenario is a sequence of Thai user turns (the examinee's
replies are produced live at evaluation time; you write ONLY the user turns).
Every constraint in your slot's table row is binding: length, register, entity,
subtype, shape, abstract value domain, pronoun, decoy, and the full note text.
The governing rules are in the plan (sections 1-10 + Annex A), especially:
- G-AX4 pronoun rules incl. the pronoun+decoy discourse rule and the antecedent
  self-check (section 6 rule 8: record ALL defensible antecedents per occurrence).
- G-AX3b value domains (color/age/size/count/taste/occupation only; person-kind
  values from role/relationship/nationality, never occupation).
- G-AX7 decoy rules (decoy fact never the answer to any scored probe).
- Section 6 Thai language rules (natural, script-correct Thai).
- Section 7 relation exclusivity; section 8 naming and anti-overlap.

Your slots (per category; the full pinned row is in the plan's section 4.8 tables):
- recall:
  - S01 | short | khrup | person | kind | kind | abstract: no | pronoun: no | decoy: no | adjacent probe; person-kind value from role/relationship/nationality (not occupation)
  - S02 | short | plain | animal | attribute | attribute | abstract: color | pronoun: no | decoy: no | adjacent probe; abstract value (color)
  - S07 | medium | khrup | animal | location | location | abstract: no | pronoun: yes | decoy: no | intervening 2-3 turns; pronoun probe
  - S08 | medium | kha | place | possession | possession | abstract: no | pronoun: no | decoy: yes | intervening 2-3 turns
  - S09 | long | kha | object | kind | kind | abstract: no | pronoun: yes | decoy: no | intervening 2-3 turns; pronoun probe
- unknown:
  - S01 | short | khrup | person | untaught-relation | kind | abstract: no | pronoun: no | decoy: no | asked relation is NOT occupation (disjoint from the pinned occupation total)
  - S03 | short | plain | place | missing-referent | location | abstract: no | pronoun: yes | decoy: no | EXEMPT: zero-antecedent pronoun probe on a short slot; no trap; 0 setup facts, so the probe's มัน has NO candidate referent; the Entity column names the implied class of the non-existent referent
  - S05 | medium | plain | food | untaught-relation | attribute | abstract: taste | pronoun: yes | decoy: yes | trap BEFORE the target facts, closed before the target's introduction; pronoun in a SETUP turn whose only subject is the target (the probe names the subject); decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before); abstract value (taste)
  - S06 | medium | kha | person | untaught-subject | kind | abstract: no | pronoun: no | decoy: no | asked relation is NOT occupation (disjoint from the pinned occupation total)
  - S09 | long | plain | object | untaught-relation | possession | abstract: no | pronoun: yes | decoy: yes | pronoun in a SETUP turn BEFORE the trap fact appears, its only subject the target (the probe names the subject); trap AFTER the target facts; decoy: person, discourse-unavailable at the pronoun (not yet introduced at the pronoun; pronoun at most one turn from the antecedent)
- contradiction:
  - S01 | short | khrup | person | kind | kind | abstract: no | pronoun: no | decoy: no | declarative, positive-conflict; person-kind value from role/relationship/nationality (not occupation)
  - S02 | short | kha | animal | attribute | attribute | abstract: color | pronoun: no | decoy: no | declarative, positive-conflict; abstract value (color)
  - S07 | medium | khrup | animal | location | location | abstract: no | pronoun: yes | decoy: no | question (ไม่ได้อยู่...หรือ); pronoun in assertion
  - S08 | medium | plain | place | possession | possession | abstract: no | pronoun: no | decoy: yes | question (ไม่มี...ใช่ไหม)
  - S09 | long | plain | object | kind | kind | abstract: no | pronoun: yes | decoy: no | declarative, negated (ไม่ใช่); pronoun in assertion
- ambiguity:
  - S03 | short | kha | place | polysemy-homograph | attribute | abstract: age | pronoun: no | decoy: no | both readings identifiable; abstract value (age)
  - S04 | short | kha | object | polysemy-homograph | location | abstract: no | pronoun: no | decoy: no | both readings identifiable
  - S05 | medium | plain | food | same-name | kind | abstract: no | pronoun: no | decoy: yes | two referents inherent (counts as decoy item)
  - S07 | medium | plain | animal | pronoun-2-antecedent | action | abstract: no | pronoun: yes | decoy: yes | FORCED anaphora; two animal antecedents (มัน), same animacy+number; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)
  - S09 | long | khrup | object | same-name | attribute | abstract: size | pronoun: yes | decoy: yes | pronoun probe over the two named referents (the same-name pair are the intended two มัน candidates); any additional decoy: person, discourse-unavailable at the pronoun (taught and closed before the referents' introduction, never re-mentioned; pronoun at most one turn from the antecedent pair; decoy absent from the pronoun's turn and the turn before); abstract value (size)
- teach:
  - S01 | short | plain | person | copula-เป็น | kind | abstract: no | pronoun: no | decoy: no | short: 0 setup facts; scored = instruction; person-kind value from role/relationship/nationality (not occupation)
  - S02 | short | kha | animal | possession-มี | possession | abstract: no | pronoun: no | decoy: no | short: 0 setup facts; count with classifier
  - S05 | medium | plain | food | copula-เป็น | kind | abstract: no | pronoun: yes | decoy: yes | follow-up recall probe (scored); pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)
  - S06 | medium | khrup | person | copula-คือ | identify | abstract: occupation | pronoun: no | decoy: yes | identifying Y; occupation (abstract value); decoy fact in setup, never probed (G-AX7 note)
  - S10 | long | khrup | food | location-อยู่ที่ | location | abstract: no | pronoun: yes | decoy: no | follow-up recall probe (scored); pronoun probe
- forget:
  - S02 | short | kha | animal | single-fact | attribute | abstract: color | pronoun: no | decoy: no | bin อย่าจำ; abstract value (color); universal re-ask
  - S03 | short | khrup | place | single-fact | location | abstract: no | pronoun: no | decoy: no | bin ไม่ต้องจำ...แล้ว; universal re-ask
  - S05 | medium | plain | food | one-of-several | kind | abstract: no | pronoun: yes | decoy: yes | bin ลบ...ออก; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE; pronoun re-ask; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)
  - S08 | medium | plain | place | one-of-several | possession | abstract: no | pronoun: no | decoy: yes | bin ช่วยลบ...ออกหน่อย; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE
  - S10 | long | khrup | food | one-of-several | attribute | abstract: taste | pronoun: yes | decoy: yes | bin ลบ...ออก; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE; abstract value (taste); pronoun re-ask; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)
- correction:
  - S01 | short | plain | person | marker-ขอแก้ไขข้อมูลเดิม: | kind | abstract: no | pronoun: no | decoy: no | post-correction probe (scored); person-kind value from role/relationship/nationality (not occupation)
  - S04 | short | plain | object | marker-ไม่ใช่ X แต่เป็น Y | kind | abstract: no | pronoun: no | decoy: no | negation form ไม่ใช่; post-correction probe
  - S05 | medium | khrup | food | marker-ขอแก้ไขข้อมูลเดิม: | location | abstract: no | pronoun: yes | decoy: yes | pronoun in post-correction probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)
  - S08 | medium | kha | place | marker-เปลี่ยน X เป็น Y | attribute | abstract: count | pronoun: no | decoy: yes | abstract value (count); post-correction probe
  - S09 | long | kha | object | marker-แก้ไข:(bare) | possession | abstract: no | pronoun: yes | decoy: yes | pronoun in post-correction probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before)

## Output

Return ONE JSON document matching this schema exactly (no prose around it):

```json
{
  "provenance": {
    "method": "ai-authored",
    "label": "AI เขียน / not human-validated",
    "authors": [{"author_id": "claude-author-01", "family": "claude",
                 "model": "<state what you are>", "version": "<or \"unavailable\">",
                 "session_date": "<today, YYYY-MM-DD>"}]
  },
  "items": [
    {"id": "<category>-S<nn>",
     "category": "<category>", "slot": "S<nn>",
     "turns": ["<user turn 1, Thai>", "<user turn 2, Thai>", "..."],
     "scored_turns": [{"turn": <1-based index>, "expected": ["<label>", "<label>"]}],
     "antecedent_self_check": [
       {"turn": <index>, "pronoun": "<form>",
        "defensible_antecedents": ["<ALL antecedents a reader could entertain>"],
        "count": <0, 1 or 2>}],
     "author_notes": "<decoy discourse management, trap placement, anything the slot note pins>"}
  ]
}
```

Rules for the JSON:
- turns contains ONLY user turns, in order, all in Thai (register per your slot row).
- scored_turns lists every scored turn with its expected label pair from the
  category's scored-turn rule (plan sections 4.1-4.7 and 5).
- antecedent_self_check is required on every pronoun slot, one entry per pronoun
  occurrence; count must match the pinned expectation (G-AX4): 0 on unknown
  S03/S04, 2 on ambiguity S07-S10, 1 elsewhere. Omit the field on non-pronoun items.
- Every item carries the provenance label AI เขียน / not human-validated via the
  provenance block above. Make no quality claim anywhere.
- Your items will be structurally validated against the pinned plan by a checker;
  items failing an acceptance gate are rejected and must be rewritten.

## Document 1 of 2: FROZEN criteria v1 (verbatim; do not modify, do not relax)

# thai-core Phase 1 (Claude family): criteria v1.4 - freeze-ready + PINNED template v2 (protocol preflight-v2)

Status: FREEZE-READY + PINNED TEMPLATE v2. Supersedes v1.3 (GPT template
review: NEEDS-CHANGE, targeted; all folds applied here, GPT accepts
after these). AI-authored (Claude family) / NOT human-validated; never a
quality claim. Changes vs v1.3: forget/correction semantics completed in
the template; rationale constraints pinned IN the template; the third
scoring dimension renamed RUBRIC-APPLICATION CONSISTENCY with its honest
meaning documented; opaque item IDs (category names no longer leak);
the re-run is a NEW PROTOCOL (preflight-v2), not comparable to run 1,
which is archived as legacy. No criterion, example or expected
annotation changes. The unknown-category G5 resolution stays recorded in
Part 0b (both families' agreement on GPT's wording). AI-authored
(Claude family) / NOT human-validated; never a quality claim. GPT round 2
accepted six categories outright (recall, contradiction, ambiguity,
teach, forget, correction) and all 35 preflight annotations. The one
remaining disagreement (G5 vs unknown criterion 2) is RESOLVED in this
version by Claude-family ACCEPTANCE of GPT's wording - see Part 0b. With
both families' agreement recorded, all seven categories are freeze-ready.
The naturalness caveat (R-Thai) stands: every Thai string is AI-authored,
NOT native-validated; a native check is still needed and no family here
can provide it.

## Part 0b: round-2 resolution and recorded agreements

G5 / unknown criterion 2 - Claude-family decision: ACCEPT GPT's wording.
GPT's formulation: "UNKNOWN applies when an identifiable subject and
relation have an untaught value, or when the requested referent is
entirely missing and no competing referents can be identified. A missing
referent is not automatically ambiguity. Multiple defensible referents
are classified as ambiguous." Why accept: it keeps the original unknown
definition intact (identifiable subject + relation, untaught value) and
makes the missing-referent case an explicit second clause instead of a
contradictory extension; the ambiguity boundary (multiple defensible
referents) is preserved exactly; and no accepted example annotation
changes under it (GPT accepted all 35, including the unknown five).

Recorded agreement (both families, this round): recall ACCEPT/ACCEPT,
contradiction ACCEPT/ACCEPT, ambiguity ACCEPT/ACCEPT, teach
ACCEPT/ACCEPT, forget ACCEPT/ACCEPT, correction ACCEPT/ACCEPT -
frozen. unknown: GPT's wording accepted by Claude (this section) -
freeze-ready once GPT records the same text.

Optional Thai refinements GPT marked advisory (ช่วยลืมว่า...ด้วย,
มีที่นา): NOT applied. The set froze on the accepted wording; advisory
phrasing changes after acceptance would reopen review for no gate
benefit. They are recorded here for a future native-validation pass,
which is the right moment to apply them.

## Part 0: dispute resolutions (what I accepted/rejected, and why)

| Point | GPT position | Claude-family decision | Why |
|---|---|---|---|
| forget label | {unknown, acknowledge} | ACCEPT | The annotation names the resulting epistemic state + the action. After a successful forget the fact is no longer supported; {unknown, acknowledge} is more precise and keeps teach/forget symmetric. My original {supported, acknowledge} described the request's well-formedness, which is not what the enum encodes. |
| R4 equivalence table | English enum tokens only | ACCEPT | The preflight's job is strict structural testing; Thai alias tokens add a normalization layer that can make structurally invalid output look valid. The frozen equivalence table becomes NORMALIZATION-ONLY (NFC, whitespace folding, case folding; no aliases). Thai glosses survive as documentation only, never as serialized tokens. |
| Natural vs minimal Thai | naturalize all 35 | ACCEPT WITH CAVEAT (R-Thai) | The preflight measures Gemini's annotation behavior on the kind of Thai the corpus will contain; telegraphic space-separated Thai would make a pass mean less. I adopt GPT's natural rewrites. CAVEAT: no family here is a validated native speaker. The naturalness of every Thai string is AI-authored and UNVERIFIED; this is stated wherever the set is described. The structural and instruction dimensions do not depend on naturalness, so the gate's meaning survives. |
| Correction marker | explicit ขอแก้ไขข้อมูลเดิม: | ACCEPT | ไม่ใช่ is ordinary negation/disagreement; an explicit marker is what separates correction from contradiction. The boundary was the point of the category. |
| unknown vs ambiguous vs missing referent | three-way distinction | ACCEPT | unknown = subject and relation identifiable, value never taught; ambiguous = multiple defensible referents or readings; missing referent is NOT ambiguity (annotated {unknown, abstain} when nothing is identifiable). ambiguity-5 is replaced, not relabeled. |
| Contradiction canonical label | {contradicted, answer} | ACCEPT | Matches my R1/R3 lean. clarify is reserved for genuinely unclear incoming assertions. |
| Ambiguity: clarify only | drop the explicit-assumption alternative for v1 | ACCEPT | One canonical tuple keeps the preflight deterministic; assumption-based replies can return later with their own accepted tuple and criteria change. |
| G2 Thai framing | define it | ACCEPT | Defined in G2 below. |
| recall equivalent expressions | accept equivalents | ACCEPT | Folded into G2 and the recall criterion: the taught VALUE must be communicated, not the exact surface string. |
| unknown-2 rejected | too broad | ACCEPT | Replaced (setup มีรถคันหนึ่ง / probe รถคันนั้นสีอะไร). |
| ambiguity-3 เธอ | use เขา | ACCEPT | เธอ adds second-person/gender readings that muddy the referential-ambiguity test. |
| พระ polysemy | use พระสงฆ์ | ACCEPT | Applied everywhere พระ appeared. |
| recall-2 probe | ในวัดมีใครอยู่ | ACCEPT | Matches the taught content (a who, not a what). |
| unknown-1/3/4 specificity | introduce the entity in setup | ACCEPT | Keeps the probe about an unknown VALUE of a known entity, not world knowledge. |
| contradiction temporal/entity specificity | ตอนนี้ / วันนี้ / นกตัวนี้ | ACCEPT | Removes "true at different times" readings. |
| Instruction-compliance clarification | rationale free-form but no invented facts; rationale quality never scored | ACCEPT | Folded into the plan. |
| Teach scope note | preflight tests classification, not retention | ACCEPT | Stated in the teach criterion and the plan. |

Still disputed after this round: NOTHING on the Claude side. If GPT
rejects the R-Thai caveat or any acceptance wording, only the affected
category blocks.

## Part 1: criteria v1.2 (per category)

Global rules (all categories):
G1. Only facts taught within the same scenario count as known.
G2. Acceptable Thai framing: natural, script-correct Thai phrasing;
    polite particles (ครับ/ค่ะ) allowed, never required; equivalent
    expressions that communicate the same taught value are acceptable;
    telegraphic word-separated Thai is neither required nor targeted.
G3. The reply must never present an untaught value as fact, and never
    leak prompt, rubric or provenance text.
G4. Labels use the closed enum only, serialized as the English enum
    tokens: epistemic in {supported, unknown, contradicted, ambiguous,
    n/a}; action in {answer, abstain, clarify, acknowledge,
    not_understood, other}. Rationale text is free-form (Thai or
    English), is never scored, and must not introduce scenario facts
    that are not in the example.
G5. unknown vs ambiguous vs missing referent (RESOLVED, GPT wording
    accepted by Claude in round 2): UNKNOWN applies when an identifiable
    subject and relation have an untaught value, OR when the requested
    referent is entirely missing and no competing referents can be
    identified. A missing referent is NOT automatically ambiguity.
    AMBIGUOUS applies when multiple defensible referents or readings
    exist.

1. recall — the probe asks for a value taught earlier in the scenario.
   ACCEPTABLE: the reply gives the taught value for the asked subject
   and relation (expected {supported, answer}); equivalent Thai
   expressions of the same value are acceptable. NOT acceptable: a
   different value, an added untaught fact, an abstain when the fact
   was taught.
2. unknown — the probe asks for a value that was never taught, and
   EITHER the subject and relation are identifiable OR the requested
   referent is entirely missing with no competing referents (G5).
   ACCEPTABLE: the reply declines (abstain class) and invents nothing
   (expected {unknown, abstain}). NOT acceptable: any stated value, a
   guess framed as fact. A probe with multiple defensible referents is
   the ambiguity category, not this one.
3. contradiction — the probe asserts something that contradicts a taught
   fact, WITHOUT a correction marker, and the assertion itself is clear.
   CANONICAL: the reply preserves the taught fact and explicitly signals
   the conflict (expected {contradicted, answer}). Silently adopting the
   new claim or silently dropping the taught fact fails. clarify is
   reserved for genuinely unclear incoming assertions. An input WITH an
   explicit correction marker (e.g. ขอแก้ไขข้อมูลเดิม:) is the
   correction category, not this one.
4. ambiguity — the probe has multiple defensible referents or readings
   in the scenario. CANONICAL: the reply asks a clarification that
   names the ambiguity (expected {ambiguous, clarify}). A confident
   pick of one referent with no signal fails; stating an explicit
   assumption is NOT an accepted alternative in v1.
5. teach — the input states a new fact in an accepted teaching shape.
   ACCEPTABLE: the reply acknowledges, and a later recall probe in the
   same scenario is served the taught value (expected {supported,
   acknowledge}); "supported" means the new fact is accepted into the
   scenario's knowledge state. The preflight tests classification of a
   teaching instruction only; actual retention is the full scenario's
   job, not the preflight's.
6. forget — the input asks the agent to forget a taught fact.
   ACCEPTABLE: the reply acknowledges the request, later probes for
   that fact get the unknown/abstain behavior, and unrelated taught
   facts stay recallable (expected {unknown, acknowledge}: the action
   is acknowledgment; the epistemic state after forgetting is unknown).
   Forgetting more or less than asked fails.
7. correction — the input corrects a taught fact with an explicit
   correction marker (e.g. ขอแก้ไขข้อมูลเดิม:). ACCEPTABLE: the reply
   acknowledges, later probes are served the corrected value, and the
   old value is not served again (expected {supported, acknowledge}).
   Serving the old value, or treating the input as a contradiction to
   argue with, fails.

## Part 2: Gemini preflight plan v1.2 (pinned before any run)

- Namespace: gemini-preflight-; these examples NEVER enter thai-core.
- Exactly 5 USABLE examples per category after replacement (35 total).
  Examples whose expected annotation the two families cannot agree on
  are REMOVED and REPLACED before the run; a category that cannot reach
  exactly 5 WAITS (no 3-4 denominator).
- Scoring (per category): structural compliance 5/5 (one miss fails the
  category); instruction compliance 5/5 (one invented fact fails the
  category; rationale is free-form, never scored, but must not introduce
  unsupported scenario facts); RUBRIC-APPLICATION CONSISTENCY >= 4/5
  (the renamed third dimension: did the annotator apply the pinned
  rubric's expected tuple). A PASS proves RUBRIC-FOLLOWING ONLY - never
  independent category recognition, and never Thai semantic
  reliability.
- The decision field must emit the EXACT ENGLISH ENUM TOKEN after
  normalization (Unicode NFC, whitespace folding, case folding). There
  are NO alias tokens; the equivalence table is normalization-only.
- The two reviewers are the Claude and GPT families, each scoring
  independently from the recorded RAW Gemini responses (scoring is
  reproducible from the raw output, never from a paraphrase). Reviewer
  disagreement on any scoring call = the category FAILS the preflight
  pending a new, agreed assessment (fail-pending-reassessment; the same
  output is never negotiated into a pass; a new assessment needs an
  agreed plan and fresh or explicitly re-approved examples).
- A PASSED preflight is structural process evidence only - never
  evidence of Thai semantic reliability.

## Part 2b: PINNED serialized annotation schema (closed, v1)

Pinned before the Gemini run, per the round-2 requirement:
- One annotation = ONE JSON object, UTF-8, compared in canonical form
  (Unicode NFC, keys sorted, no insignificant whitespace - the same
  canonicalization the evidence checker pins for hashes).
- EXACTLY two REQUIRED fields:
  {"epistemic": <enum>, "action": <enum>}
  epistemic in {supported, unknown, contradicted, ambiguous, n/a};
  action in {answer, abstain, clarify, acknowledge, not_understood,
  other}. Values are the exact English enum tokens after the
  normalization-only equivalence table (Part 2).
- "rationale": OPTIONAL third field, a string. Free-form (Thai or
  English), NEVER scored, must not introduce scenario facts not in the
  example. When absent it is OMITTED - never null, never empty string.
- NO OTHER FIELDS. The schema is closed: any extra field, a missing
  required field, a null, or a non-string rationale is STRUCTURAL
  NON-COMPLIANCE (counts as a structural miss for the category).
- Field order in the raw emission is free; comparison is after
  canonicalization, so order carries no meaning.
- LANGUAGE HONESTY LABEL: all Thai strings below are AI-authored
  (GPT-family wording from the cross-review), NOT native-validated.

## Part 2c: PINNED Gemini prompt template v2 (protocol preflight-v2)

Protocol notes (GPT review folds):
- This is a NEW PROTOCOL, preflight-v2. Run 1 (26 Nov, collector's
  unpinned template) is ARCHIVED AS LEGACY: its results are not
  comparable to preflight-v2 and are never merged with them.
- ITEM IDS ARE OPAQUE: items render as pf-01 .. pf-35 (per-batch
  pf-01..pf-05), never as gemini-preflight-<category>-N - the id must
  not leak the category. The id -> example mapping is recorded in the
  evidence bundle's order.json, visible to both reviewing families.
- Fresh Gemini sessions per batch; the evidence bundle records the
  template sha256, each rendered prompt's sha256, and the raw
  responses (same layout as run 1: raw + prompts + order +
  session_log + SHA256SUMS).

TEMPLATE v2, verbatim (the {ITEMS} placeholder is replaced by the
batch's 5 examples under opaque ids in the recorded shuffled order):

---
You are an annotator. Below is a short scripted conversation scenario
for each item, in Thai. For each item, classify the FINAL probe turn
into the closed annotation schema.

Rules:
- Only facts stated in the item's own setup turns count as known. Each
  item is independent.
- Output, for each item, the item ID on its own line, then a JSON code
  block containing exactly ONE JSON object.
- The object has exactly two required fields: "epistemic" and
  "action". No other fields are permitted.
- An optional third field "rationale" MAY be included; when present it
  must be a NON-EMPTY string (Thai or English) that introduces no
  facts beyond the scenario and names no prompt, rubric or provenance
  text; omit the field entirely when unused. Rationale is never
  scored.
- "epistemic" must be one of: supported, unknown, contradicted,
  ambiguous, n/a
- "action" must be one of: answer, abstain, clarify, acknowledge,
  not_understood, other
- Use the exact English tokens above.
- Output items in the order given and add nothing else.

Annotation semantics (apply these definitions exactly; they override
intuition about the enum names):
- recall: the probe asks for a value taught in the setup. A correct
  agent replies with the taught value: {"epistemic": "supported",
  "action": "answer"}.
- unknown: the probe asks for a value that was never taught - either
  the subject and relation are identifiable with an untaught value, or
  the requested referent is entirely missing with no competing
  referents. A correct agent declines and invents nothing:
  {"epistemic": "unknown", "action": "abstain"}.
- contradiction: the probe asserts something that contradicts a taught
  fact, WITHOUT any correction marker. A correct agent preserves the
  taught fact and answers with it, signaling the conflict:
  {"epistemic": "contradicted", "action": "answer"}.
- ambiguity: the probe has multiple defensible referents or readings.
  A correct agent asks a clarifying question that names the ambiguity:
  {"epistemic": "ambiguous", "action": "clarify"}.
- teach: the input states a new fact in a teaching shape. A correct
  agent acknowledges, and the fact is accepted into the scenario's
  knowledge state: {"epistemic": "supported", "action":
  "acknowledge"}.
- forget: the input asks the agent to forget a taught fact. A correct
  agent acknowledges; afterwards the fact is no longer known, and
  UNRELATED taught facts remain known and recallable - forgetting
  more or less than asked fails: {"epistemic": "unknown", "action":
  "acknowledge"}.
- correction: the input corrects a taught fact with an explicit
  correction marker. A correct agent acknowledges, serves the
  corrected value afterwards, and the OLD value is no longer served:
  {"epistemic": "supported", "action": "acknowledge"}.

Items:

{ITEMS}
---

Scoring note: with the semantics pinned in the template, a batch that
still returns the old priors (teach -> n/a, forget -> n/a,
contradiction -> other, correction -> contradicted) is a genuine
rubric-application failure and scores as such - never negotiated into
a pass.


## Part 3: the 35 revised preflight examples (non-corpus)

### recall (gemini-preflight-recall-1..5) — expected {supported, answer} throughout
1. setup: จำไว้ว่าแมวอยู่ในสวน — probe: แมวอยู่ที่ไหน
2. setup: จำไว้ว่าในวัดมีพระสงฆ์ — probe: ในวัดมีใครอยู่
3. setup: จำไว้ว่าปู่มีสวน — probe: ปู่มีอะไร
4. setup: จำไว้ว่านกกินข้าว — probe: นกกินอะไร
5. setup: จำไว้ว่าแม่อยู่ที่บ้าน — probe: แม่อยู่ที่ไหน

### unknown (gemini-preflight-unknown-1..5) — expected {unknown, abstain} throughout
1. setup: มีช้างตัวหนึ่ง — probe: ช้างตัวนั้นอยู่ที่ไหน
2. setup: มีรถคันหนึ่ง — probe: รถคันนั้นสีอะไร
3. setup: มีปลาตัวหนึ่ง — probe: ปลาตัวนั้นกินอะไร
4. setup: มีครูคนหนึ่ง — probe: ครูคนนั้นอยู่ที่ไหน
5. setup: จำไว้ว่าแมวอยู่ในสวน — probe: หมาอยู่ที่ไหน

### contradiction (gemini-preflight-contradiction-1..5) — expected {contradicted, answer} throughout
1. setup: จำไว้ว่าแมวอยู่ในสวนตอนนี้ — probe: แมวอยู่ในบ้านตอนนี้
2. setup: จำไว้ว่าในวัดมีพระสงฆ์ — probe: ในวัดไม่มีพระสงฆ์
3. setup: จำไว้ว่านกตัวนี้กินข้าว — probe: นกตัวนี้ไม่กินข้าว
4. setup: จำไว้ว่าวันนี้แม่อยู่บ้าน — probe: วันนี้แม่อยู่ที่ตลาด
5. setup: จำไว้ว่าปู่มีสวน — probe: ปู่ไม่มีสวน

### ambiguity (gemini-preflight-ambiguity-1..5) — expected {ambiguous, clarify} throughout
1. setup: จำไว้ว่าแมวอยู่ในสวน / จำไว้ว่าหมาอยู่ในบ้าน — probe: มันอยู่ที่ไหน
2. setup: จำไว้ว่าพ่อมีรถ / จำไว้ว่าพี่มีเรือ — probe: เขามีอะไร
3. setup: จำไว้ว่าน้องอยู่ที่โรงเรียน / จำไว้ว่าน้าอยู่ที่ตลาด — probe: เขาอยู่ที่ไหน
4. setup: จำไว้ว่าแมวกินปลา / จำไว้ว่าหมากินข้าว — probe: มันกินอะไร
5. setup: จำไว้ว่าพ่ออยู่ที่บ้าน / จำไว้ว่าแม่อยู่ที่ตลาด — probe: เขาอยู่ที่ไหน

### teach (gemini-preflight-teach-1..5) — expected {supported, acknowledge} throughout
1. probe: จำไว้ว่าแมวอยู่ในสวน
2. probe: จำไว้ว่าในวัดมีพระสงฆ์
3. probe: จำไว้ว่านกกินข้าว
4. probe: จำไว้ว่าแม่อยู่ที่บ้าน
5. probe: จำไว้ว่าปู่มีสวน

### forget (gemini-preflight-forget-1..5) — expected {unknown, acknowledge} throughout
1. setup: จำไว้ว่าแมวอยู่ในสวน — probe: ช่วยลืมข้อมูลที่ว่าแมวอยู่ในสวนด้วย
2. setup: จำไว้ว่าในวัดมีพระสงฆ์ — probe: ช่วยลืมข้อมูลที่ว่าในวัดมีพระสงฆ์ด้วย
3. setup: จำไว้ว่านกกินข้าว — probe: ช่วยลืมข้อมูลที่ว่านกกินข้าวด้วย
4. setup: จำไว้ว่าแม่อยู่ที่บ้าน — probe: ช่วยลืมข้อมูลที่ว่าแม่อยู่ที่บ้านด้วย
5. setup: จำไว้ว่าปู่มีสวน — probe: ช่วยลืมข้อมูลที่ว่าปู่มีสวนด้วย

### correction (gemini-preflight-correction-1..5) — expected {supported, acknowledge} throughout
1. setup: จำไว้ว่าแมวอยู่ในสวน — probe: ขอแก้ไขข้อมูลเดิม: แมวไม่ได้อยู่ในสวน แต่อยู่ในบ้าน
2. setup: จำไว้ว่าในวัดมีพระสงฆ์ — probe: ขอแก้ไขข้อมูลเดิม: ที่วัดไม่มีพระสงฆ์ แต่มีแม่ชี
3. setup: จำไว้ว่านกตัวนี้กินข้าว — probe: ขอแก้ไขข้อมูลเดิม: นกตัวนี้ไม่ได้กินข้าว แต่กินหนอน
4. setup: จำไว้ว่าวันนี้แม่อยู่บ้าน — probe: ขอแก้ไขข้อมูลเดิม: วันนี้แม่ไม่ได้อยู่ที่บ้าน แต่อยู่ที่ตลาด
5. setup: จำไว้ว่าปู่มีสวน — probe: ขอแก้ไขข้อมูลเดิม: ปู่ไม่ได้มีสวน แต่มีทุ่งนา

## Document 2 of 2: PINNED variation plan v12.1 (verbatim; sections 1-10 + Annex A govern)

# thai-core v1 (AI path) - Phase 2: VARIATION PLAN v12.1 (PINNED)

Labels (binding): **AI เขียน / not human-validated**. No quality claim
about the resulting set, no capability claim about any agent. This is a
generation-control document: it fixes WHAT varies before items are
written, so authoring cannot drift toward whatever is easiest to write.

Authority basis (evidence lives OUTSIDE this document, in the user's
own channel): Ash's 22 Nov delegation to Instinct+GPT with Claude
review, and 26 Nov "continue all". Criteria v1 are FROZEN
(= v1.4 doc, sha256 241612cab5f3efbec8eee2562e2850680a8a262186132cbe4af8ee6af7a2dd18).

## 1. Scope and arithmetic

- 7 frozen categories: recall, unknown, contradiction, ambiguity,
  teach, forget, correction (criteria v1 Part 1; G1-G5 apply globally).
- 10 scenarios per category x 7 = **N = 70 items**. A scenario
  (setup + instruction/probe turns) counts as 1 item (spec Phase 2).
- Authoring allocation (Phase 3, spec section 4): Claude and GPT
  author approximately equal halves; this plan REQUIRES the split to
  be 5 items per category per family when N=70, allocated by the
  per-category ALLOCATION MATRIX pinned in the slot tables (Author
  column) and validated by the checker: within each category each
  family authors 2 short, 2 medium and 1 long item, sees all three
  registers, and splits every multi-item subtype bin - plus
  contradiction's declarative/question forms, teach's
  copula/possession constructions, forget's request constructions
  and correction's multi-item markers - as evenly as the bin's count
  permits (singleton bins exempt). The matrix additionally balances
  authors SET-WIDE (checker-enforced): each entity type exactly 7/7;
  register totals differ by at most 1 per register (plain 14/14,
  ครับ 11/10, ค่ะ/คะ 10/11); every multi-item abstract domain splits
  as evenly as its total permits (color 3/3, taste 2/3, age 1/2,
  size 1/2, occupation 1/1; singleton count exempt). Author style
  therefore never aligns with a category, length, register, subtype,
  entity type, abstract domain or construction/marker variant. Which
  family is A/B is recorded at Phase 3. If a category unfreezes, N
  derives down per spec and the set says so.
- Authors see ONLY: the frozen criteria, this plan, and Annex A
  (capability-level description). Never code, outputs, dev-set items,
  or failure modes (spec Phase 3).

## 2. Definitions (binding on every table and count)

- TURN: one user message plus the agent's reply to it. Turn counting
  is by user messages; the agent's reply belongs to the same turn.
- SETUP TURN: a turn that teaches scenario facts before the
  instruction or probe under test.
- TAUGHT FACT: a single (subject, relation, value) statement accepted
  in a setup turn. Relations are SINGLE-VALUED per subject (section 7).
- INSTRUCTION-UNDER-TEST: the user turn carrying the category's
  primary event (the teaching statement, forget request, correction,
  conflicting assertion, or ambiguous/unknown probe).
- FOLLOW-UP PROBE: a later user turn asking about scenario facts.
- SCORED TURN: a turn whose reply is annotated against the criteria.
  Setup turns are context-only and NEVER scored. Section 5 lists every
  scored turn per category with its expected label.
- INTERVENING TURN: a complete turn (user message + agent reply)
  between the turn that taught the probed fact and the probe turn.
  Intervening turns are other teaching turns or neutral exchanges;
  "intervening 2-3" exists only in medium/long slots.
- SCENARIO ISOLATION: each scenario is evaluated in a fresh
  conversation with no retained facts from any other scenario or item.
- LENGTH: determined ONLY by the number of taught setup facts:
  short = 0-1, medium = 2-3, long = 4-5. Probe counts do not define
  length.

## 3. Global variation axes

Precedence: the per-category slot tables in section 4 are the pinned
assignment; the global rules below define what the tables must
satisfy. Where a category table documents an exemption it is listed
in section 3.9; there are no other exceptions.

G-AX1 REGISTER (per scenario, constant across its user turns):
  - plain (none of ครับ/ค่ะ/คะ): exactly 4 of 10
  - ครับ: exactly 3 of 10
  - ค่ะ/คะ: exactly 3 of 10
  Register bins carry NO speaker gender/identity. Other particles
  (นะ/สิ/อะ) are unconstrained. Registers are pre-assigned PER SLOT
  PER CATEGORY in the tables (4/3/3 within each category), chosen by
  exhaustive search so that every multi-item audit bin spans >=2
  registers within its category and every slot position sees all 3
  registers across the set. Phase 6 runs the register-vs-label audit
  with the acceptance rule in section 5.

G-AX2 LENGTH: short x4, medium x4, long x2 per category, by the
  section 2 definition.

G-AX3a ENTITY TYPES: five bins - person, animal, place, object,
  food (INCLUDING beverages, matching Annex A's "food or drink") -
  each appearing EXACTLY twice per category (the S01-S10
  skeleton assigns them in pairs). Entity x shape compatibility is
  pinned in the checker.
G-AX3b VALUE DOMAINS (independent of G-AX3a): a taught/probed value
  is ABSTRACT or CONCRETE (entities, substances, places, classes).
  The authoritative ABSTRACT domain list (defined only here) is:
  color, age, size, count, taste, occupation. Spiciness is a value
  WITHIN the taste domain, not a separate domain. Every category
  carries 1-4 abstract-valued items; each abstract slot's exact
  domain is pinned in the table's "Abstract value" column and in the
  checker, with set-wide totals color 6, taste 5, age 3, size 3,
  occupation 2, count 1 (20 abstract-valued items). Abstract values
  appear only with attribute, kind or identify shapes; an occupation
  value only on a person host; a taste value only on a food host.
  A kind-class value on a PERSON host comes from {role, relationship,
  nationality}, disjoint from the occupation domain, and unknown's
  person-kind probes never ask occupation (checker-enforced via the
  pinned notes).
  Annex A names the same domains (capability level), so authors
  never assume a capability beyond it.

G-AX4 PRONOUN / ANAPHORA: exactly 4 of 10 scenarios per category
  contain at least one pronoun reference in a setup, instruction or
  probe turn. Pronoun slots are medium/long EXCEPT documented
  exemptions (section 3.9). Inventory (authoritative, defined only here): เขา (people),
  มัน/พวกมัน (ALL non-person entities: animals, objects, places,
  food), พวกเขา (people plural). เธอ is FORBIDDEN in
  user turns. Every pronoun use must still be natural Thai in context
  (section 6) - the inventory makes slots authorable, never mandatory. Every pronoun's expected defensible-antecedent
  count is pinned (checker-enforced): exactly 0 on the two
  missing-referent exemptions (unknown S03+S04, section 3.9), exactly
  the intended 2 on ambiguity's four pronoun slots (S07, S08, S10
  pronoun-2-antecedent; S09 same-name, whose two candidates are the
  same-name pair), and exactly 1 on every other pronoun slot.
  Pronoun-ambiguity items require
  antecedents of the same animacy and number. Zero anaphora (omitted
  subject) is OUT of scope in v1 of this plan.
  PRONOUN+DECOY RULE (checker-enforced via the pinned notes): where a
  pronoun and a decoy co-occur in one item, the decoy MUST be
  DISCOURSE-UNAVAILABLE at every pronoun occurrence, under EITHER
  safe ordering: (A) the decoy is not yet introduced at the pronoun
  occurrence (unknown S09), or (B) the decoy was introduced earlier,
  its discourse segment explicitly closed, and it is never
  reintroduced between the antecedent's introduction and the
  pronoun. In BOTH orderings: the pronoun sits at most one turn from
  its antecedent (same or adjacent turn); the antecedent is the most
  recently introduced subject and the only subject of its turn; and
  the decoy appears in neither the pronoun's turn nor the turn
  before it. On pronoun-ambiguity items (ambiguity S07-S10) the two
  singular conditions - "most recently introduced subject" and "only
  subject of its turn" - do NOT apply to the two intended candidates:
  both remain independently defensible by design. Those conditions
  govern the discourse anchor on single-antecedent items; on
  ambiguity items the orderings and turn-absence conditions constrain
  only any ADDITIONAL decoy. Where feasible, authors pick a pronoun predicate
  semantically incompatible with the decoy host (inanimate or
  agentless predicates) as an extra margin; entity-class distance
  (person decoys) is likewise only a margin, never the guarantee -
  มัน can refer to humans in informal Thai, and discourse
  accessibility is not a binary of recency. No rule gives certainty
  in natural language: authors perform and record an antecedent
  self-check on every pronoun slot (section 6 rule 8), Phase 6
  spot-audits antecedent uniqueness on every pronoun+decoy slot
  (section 5), and the residual risk is declared in section 9. If
  Phase 3 authoring finds a slot where this boundary is not
  authorable, the decoy is dropped from that slot and moved to
  another medium/long slot (keeping exactly 4 per category), handled
  as a plan change under section 10.
  On unknown S05 and S09 the pronoun sits in a SETUP turn
  whose only subject is the antecedent (on S09, before the trap fact
  appears) and the probe names the subject. In ambiguity items the
  antecedents the subtype inherently requires are the intended
  candidates; the orderings above constrain any ADDITIONAL decoy.
  NATURALNESS EXCEPTION: ambiguity S08's มัน-for-places is a
  declared, narrow exception to the natural-Thai requirement
  (section 9); everywhere else naturalness governs.

G-AX5 SENTENCE SHAPES: at least 3 distinct per category, no shape
  more than 5 items, assignments pinned per slot. Shapes: kind
  (X เป็น Y, class membership), identify (X คือ Y, identifying Y only),
  attribute (all six abstract domains - color, age, size, count,
  taste, occupation - with classifiers where required),
  location (X อยู่ที่/อยู่ใน Y), possession (X มี Y), action/ability.

G-AX6 NEGATION FORMS: applies to contradiction and correction ONLY.
  Closed form list: ไม่ใช่ (identity), ไม่มี (possession),
  ไม่ได้ + verb (action/location). Contradiction: at least 2 distinct
  forms across its 10 items (pinned: ไม่ใช่ x2, ไม่มี x1,
  ไม่ได้อยู่ x1). Correction: all 3 forms via its negative-frame
  markers (pinned: one slot each). Forget is EXCLUDED: อย่า is a
  prohibitive, not a form in the list, and Annex A defines no taught
  negative facts. ใช่ไหม / ไม่ใช่...หรือ are confirmation-seeking
  question frames, never negation forms.

G-AX7 DECOY: exactly 4 of 10 scenarios per category carry the DECOY
  FLAG: an entity beyond the target subject with its own taught setup
  fact whose value is never the correct answer to any scored probe.
  A decoy's fact is a taught setup fact, so a decoy
  item needs at least 2 setup facts: decoys sit on medium/long slots
  ONLY (checker-enforced). A decoy need not carry a scored probe; in
  teach items the decoy fact is never the instruction-under-test
  target. In forget one-of-several items the decoy entity is present
  alongside the target subject, but EVERY scored probe asks about the
  target subject's facts: the decoy's own fact is never the correct
  answer to any scored probe (see 4.6). Where a subtype inherently
  requires two referents - an unknown trap entity, an ambiguity
  same-name pair - the second referent carries the flag. The two
  antecedents of a pronoun-2-antecedent item do NOT (the subtype
  requires them; only an additional decoy, as on ambiguity S07,
  counts), and entities mentioned around an unknown untaught-subject
  probe carry no taught fact of their own and are never flagged. The
  FLAG is balanced 4/10 per category, so the flag never predicts the
  label; the mere PRESENCE of any second entity is not balanced
  (unknown 7/10, ambiguity 6/10) and no such claim is made.

### 3.9 Documented exemptions (complete list)

1. unknown S03 and S04 (missing-referent, criteria category 2 + G5):
   pronoun probes with ZERO antecedents on short slots; these items
   never carry traps (a trap would create a competing referent and
   break G5).
2. No other exemptions exist. With length defined by setup-fact count,
   teach short items (0 setup facts, the instruction creates the fact)
   satisfy G-AX2 without an override.

## 4. Per-category rules and pinned slot tables

Subtype-to-criteria traceability is stated per category. The tables
below are GENERATED and CHECKED by scripts/thai-phase2-slot-check.py;
hand edits are forbidden (change the script, re-check, re-emit).

### 4.1 recall (criteria clause 1; expected {supported, answer})

Subtypes are the asked value type: kind / attribute / location /
possession. Probe distance: adjacent x5 (all 4 short slots + S06),
intervening 2-3 turns x5 (medium/long slots only). The 4 pronoun
slots use pronoun PROBES (single antecedent).

### 4.2 unknown (criteria clause 2 + G5; expected {unknown, abstain})

Subtypes: untaught relation on a taught subject x5, entirely untaught
subject x3, missing referent with no competing referents x2. Trap
design (decoy entity with a taught value for a DIFFERENT subject;
same-type on S07/S08, on the pronoun slots S05/S09 a person kept
discourse-unavailable per G-AX4's pronoun+decoy rule): exactly the 4 trap slots S05, S07, S08, S09 (all
medium/long, per G-AX7). Trap position is pinned: S05 and S08 place
the trap fact BEFORE the target subject's facts, S07 and S09 AFTER
(at least one of each, checker-verified); trap wording MUST vary, and
the 6 non-trap items MUST NOT be uniformly simpler. Missing-referent
items (S03, S04) are exempt per section 3.9; they carry 0 setup
facts, so the probe's มัน has NO candidate referent, and their Entity
column names the implied class of the non-existent referent. On the
pronoun trap slots S05 and S09 the pronoun sits in a SETUP turn
whose only subject is the target (on S09, before the trap fact
appears) and the probe names the subject; the trap entity is
discourse-unavailable at the pronoun per G-AX4's pronoun+decoy rule.
S07 and S08 carry no pronoun; their trap entity is same-type.

### 4.3 contradiction (criteria clause 3; expected {contradicted, answer})

Subtypes are the contradicted value type. Assertion shapes:
declarative x7, confirmation-seeking question x3 (ใช่ไหม /
ไม่ใช่...หรือ with an unambiguous implied proposition). Negated
assertions: ไม่ใช่ on S05+S09, ไม่มี on S08, ไม่ได้อยู่ on S07; the
other 6 are positive-conflict assertions. No correction marker may
appear (clause 3 boundary); ไม่ใช่ X แต่เป็น Y is FORBIDDEN here
because it is a correction marker (clause 7). The SCORED target is
the agent's reply WITHIN the same turn as the conflicting assertion
(the instruction-under-test), expected {contradicted, answer}; this
category has no separate follow-up turn.
WORKED EXAMPLE (S07, negative tag question): setup teaches
วัดแพร่แดงอยู่เชียงใหม่ (the temple is in Chiang Mai). The assertion
turn is วัดแพร่แดงไม่ได้อยู่เชียงใหม่หรือ. In this frame หรือ is a
confirmation-seeking tag on the NEGATIVE proposition, so the implied
proposition is unambiguous: the speaker asserts the temple is NOT in
Chiang Mai. The agent must treat it as conflicting with the taught
location, expected {contradicted, answer} - not as a genuine
open question about where the temple is.

### 4.4 ambiguity (criteria clause 4 + G5; expected {ambiguous, clarify})

Subtypes: polysemy/homograph x4 (exactly the 4 short slots - a single
taught fact suffices), same-name referents x3 (S05, S06, S09),
pronoun with two defensible antecedents x3 (S07, S08, S10; antecedents
share animacy and number). The mechanism for written Thai is
homographs/polysemes (ตา, ลูก); word-SEGMENTATION ambiguity
(ตากลม) is OUT of scope. Every item MUST make both referents/readings
independently identifiable from the supplied setup + probe context
(criteria clause 4 with G5: multiple defensible referents or readings
exist) - naming a homograph is not sufficient by itself; the context
must support BOTH readings. The expected clarify reply names the
ambiguity; a confident pick fails (clause 4).

### 4.5 teach (criteria clause 5; expected {supported, acknowledge} +
follow-up)

Subtypes are the teaching shape: เป็น x4, คือ x2 (identifying Y),
มี x2, อยู่ที่ x1, action/ability x1. Short slots have 0 setup facts
(the instruction creates the fact). Exactly 5 items (S05, S07, S08,
S09, S10 - the medium/long slots minus S06) carry ONE follow-up
recall probe scored {supported, answer}.

### 4.6 forget (criteria clause 6; expected {unknown, acknowledge} +
probes)

Subtypes: single-fact x4 (the 4 short slots: exactly one taught fact,
which is the forget target), one-of-several x6 (medium/long: the
target is one of several taught facts; unrelated facts MUST stay
recallable). Request-construction bins: ลบ...ออก x4, อย่าจำ x2,
ไม่ต้องจำ...แล้ว x2, ช่วยลบ...ออกหน่อย x2. These are
construction bins (verb + framing pinned together), not a verb
axis crossed with politeness; register stays per G-AX1. EVERY item ends with a universal re-ask probe
of the forgotten fact scored {unknown, abstain}; one-of-several items
add an unrelated-fact recall probe scored {supported, answer}. In
every one-of-several item the unrelated-fact probe asks about a
different RETAINED FACT OF THE ORIGINAL TARGET SUBJECT; on decoy
slots (S05, S08, S09, S10) the decoy entity's own fact is never
probed and never the correct answer to any scored probe.

### 4.7 correction (criteria clause 7; expected {supported, acknowledge}
+ probe)

Marker bins: ขอแก้ไขข้อมูลเดิม: x3, bare แก้ไข: x2 (excludes the long
form), เปลี่ยน X เป็น Y x2 (accepted as a marker per clause 7's
open "e.g."; authors must pair it with an explicit correction intent),
negative-frame markers x3: ไม่ใช่ X แต่เป็น Y (kind), ไม่มี X แต่มี Y
(possession), ไม่ได้อยู่ X แต่อยู่ Y (location). Corrected value types
are pinned in the table. EVERY item carries a universal
post-correction probe scored {supported, answer}; the old value is
never served again.

### 4.8 Slot tables (generated, checked)

The tables below are generated and verified by
scripts/thai-phase2-slot-check.py. The checker's execution result is
VALIDATION EVIDENCE, not part of this normative document: it is
recorded beside the plan's hash and the checker's self-hash in the
freeze attestation (section 10). This plan remains AI-authored / not
human-validated; the checker proves only its implemented structural
checks (section 9 limitations).

#### recall slot table

| Slot | Author | Length | Register | Entity | Subtype | Shape | Abstract value | Pronoun | Decoy | Scored turns / notes |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | A | short | khrup | person | kind | kind | no | no | no | adjacent probe; person-kind value from role/relationship/nationality (not occupation) |
| S02 | A | short | plain | animal | attribute | attribute | color | no | no | adjacent probe; abstract value (color) |
| S03 | B | short | plain | place | location | location | no | no | no | adjacent probe |
| S04 | B | short | plain | object | possession | possession | no | no | no | adjacent probe |
| S05 | B | medium | kha | food | kind | kind | no | yes | yes | intervening 2-3 turns; pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S06 | B | medium | khrup | person | attribute | attribute | size | no | yes | adjacent probe; abstract value (size); decoy entity present |
| S07 | A | medium | khrup | animal | location | location | no | yes | no | intervening 2-3 turns; pronoun probe |
| S08 | A | medium | kha | place | possession | possession | no | no | yes | intervening 2-3 turns |
| S09 | A | long | kha | object | kind | kind | no | yes | no | intervening 2-3 turns; pronoun probe |
| S10 | B | long | plain | food | attribute | attribute | taste | yes | yes | intervening 2-3 turns; pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before); abstract value (taste) |

Scored-turn rule: every probe turn: {supported, answer}

#### unknown slot table

| Slot | Author | Length | Register | Entity | Subtype | Shape | Abstract value | Pronoun | Decoy | Scored turns / notes |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | A | short | khrup | person | untaught-relation | kind | no | no | no | asked relation is NOT occupation (disjoint from the pinned occupation total) |
| S02 | B | short | kha | animal | untaught-subject | attribute | color | no | no | abstract value (color) |
| S03 | A | short | plain | place | missing-referent | location | no | yes | no | EXEMPT: zero-antecedent pronoun probe on a short slot; no trap; 0 setup facts, so the probe's มัน has NO candidate referent; the Entity column names the implied class of the non-existent referent |
| S04 | B | short | khrup | object | missing-referent | possession | no | yes | no | EXEMPT: zero-antecedent pronoun probe on a short slot; no trap; 0 setup facts, so the probe's มัน has NO candidate referent; the Entity column names the implied class of the non-existent referent |
| S05 | A | medium | plain | food | untaught-relation | attribute | taste | yes | yes | trap BEFORE the target facts, closed before the target's introduction; pronoun in a SETUP turn whose only subject is the target (the probe names the subject); decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before); abstract value (taste) |
| S06 | A | medium | kha | person | untaught-subject | kind | no | no | no | asked relation is NOT occupation (disjoint from the pinned occupation total) |
| S07 | B | medium | khrup | animal | untaught-relation | action | no | no | yes | trap AFTER the target facts |
| S08 | B | medium | kha | place | untaught-relation | location | no | no | yes | trap BEFORE the target facts |
| S09 | A | long | plain | object | untaught-relation | possession | no | yes | yes | pronoun in a SETUP turn BEFORE the trap fact appears, its only subject the target (the probe names the subject); trap AFTER the target facts; decoy: person, discourse-unavailable at the pronoun (not yet introduced at the pronoun; pronoun at most one turn from the antecedent) |
| S10 | B | long | plain | food | untaught-subject | attribute | taste (spiciness) | no | no | abstract value (taste: spiciness) |

Scored-turn rule: the probe turn (instruction-under-test): {unknown, abstain}

#### contradiction slot table

| Slot | Author | Length | Register | Entity | Subtype | Shape | Abstract value | Pronoun | Decoy | Scored turns / notes |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | A | short | khrup | person | kind | kind | no | no | no | declarative, positive-conflict; person-kind value from role/relationship/nationality (not occupation) |
| S02 | A | short | kha | animal | attribute | attribute | color | no | no | declarative, positive-conflict; abstract value (color) |
| S03 | B | short | plain | place | location | location | no | no | no | declarative, positive-conflict |
| S04 | B | short | khrup | object | possession | possession | no | no | no | declarative, positive-conflict |
| S05 | B | medium | kha | food | kind | kind | no | yes | yes | declarative, negated (ไม่ใช่); pronoun in assertion; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S06 | B | medium | plain | person | attribute | attribute | age | no | yes | declarative, positive-conflict; abstract value (age) |
| S07 | A | medium | khrup | animal | location | location | no | yes | no | question (ไม่ได้อยู่...หรือ); pronoun in assertion |
| S08 | A | medium | plain | place | possession | possession | no | no | yes | question (ไม่มี...ใช่ไหม) |
| S09 | A | long | plain | object | kind | kind | no | yes | no | declarative, negated (ไม่ใช่); pronoun in assertion |
| S10 | B | long | kha | food | attribute | attribute | taste | yes | yes | question (...ใช่ไหม), positive; pronoun in assertion; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before); abstract value (taste) |

Scored-turn rule: the agent's reply WITHIN the same turn as the conflicting assertion (the instruction-under-test): {contradicted, answer}. No separate follow-up turn exists in this category.

#### ambiguity slot table

| Slot | Author | Length | Register | Entity | Subtype | Shape | Abstract value | Pronoun | Decoy | Scored turns / notes |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | B | short | kha | person | polysemy-homograph | attribute | color | no | no | short-feasible; both readings identifiable from setup+probe (clause 4); abstract value (color) |
| S02 | B | short | khrup | animal | polysemy-homograph | kind | no | no | no | both readings identifiable from setup+probe |
| S03 | A | short | kha | place | polysemy-homograph | attribute | age | no | no | both readings identifiable; abstract value (age) |
| S04 | A | short | kha | object | polysemy-homograph | location | no | no | no | both readings identifiable |
| S05 | A | medium | plain | food | same-name | kind | no | no | yes | two referents inherent (counts as decoy item) |
| S06 | B | medium | plain | person | same-name | attribute | occupation | no | yes | two referents inherent; abstract value (occupation) |
| S07 | A | medium | plain | animal | pronoun-2-antecedent | action | no | yes | yes | FORCED anaphora; two animal antecedents (มัน), same animacy+number; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S08 | B | medium | khrup | place | pronoun-2-antecedent | location | no | yes | no | FORCED anaphora; two place antecedents (มัน, extended inventory) |
| S09 | A | long | khrup | object | same-name | attribute | size | yes | yes | pronoun probe over the two named referents (the same-name pair are the intended two มัน candidates); any additional decoy: person, discourse-unavailable at the pronoun (taught and closed before the referents' introduction, never re-mentioned; pronoun at most one turn from the antecedent pair; decoy absent from the pronoun's turn and the turn before); abstract value (size) |
| S10 | B | long | plain | food | pronoun-2-antecedent | kind | no | yes | no | FORCED anaphora; two food antecedents (มัน) |

Scored-turn rule: the ambiguous probe turn: {ambiguous, clarify}

#### teach slot table

| Slot | Author | Length | Register | Entity | Subtype | Shape | Abstract value | Pronoun | Decoy | Scored turns / notes |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | A | short | plain | person | copula-เป็น | kind | no | no | no | short: 0 setup facts; scored = instruction; person-kind value from role/relationship/nationality (not occupation) |
| S02 | A | short | kha | animal | possession-มี | possession | no | no | no | short: 0 setup facts; count with classifier |
| S03 | B | short | plain | place | possession-มี | possession | no | no | no | short: 0 setup facts |
| S04 | B | short | kha | object | copula-เป็น | kind | no | no | no | short: 0 setup facts |
| S05 | A | medium | plain | food | copula-เป็น | kind | no | yes | yes | follow-up recall probe (scored); pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S06 | A | medium | khrup | person | copula-คือ | identify | occupation | no | yes | identifying Y; occupation (abstract value); decoy fact in setup, never probed (G-AX7 note) |
| S07 | B | medium | kha | animal | action-ability | action | no | yes | no | follow-up recall probe (scored); pronoun probe |
| S08 | B | medium | khrup | place | copula-เป็น | kind | no | no | yes | follow-up recall probe (scored) |
| S09 | B | long | plain | object | copula-คือ | identify | no | yes | yes | follow-up recall probe (scored); pronoun probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S10 | A | long | khrup | food | location-อยู่ที่ | location | no | yes | no | follow-up recall probe (scored); pronoun probe |

Scored-turn rule: instruction turn: {supported, acknowledge}; exactly 5 items (S05, S07-S10) add one follow-up recall probe: {supported, answer}

#### forget slot table

| Slot | Author | Length | Register | Entity | Subtype | Shape | Abstract value | Pronoun | Decoy | Scored turns / notes |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | B | short | kha | person | single-fact | kind | no | no | no | request-construction bin ลบ...ออก; universal re-ask probe; person-kind value from role/relationship/nationality (not occupation) |
| S02 | A | short | kha | animal | single-fact | attribute | color | no | no | bin อย่าจำ; abstract value (color); universal re-ask |
| S03 | A | short | khrup | place | single-fact | location | no | no | no | bin ไม่ต้องจำ...แล้ว; universal re-ask |
| S04 | B | short | khrup | object | single-fact | possession | no | no | no | bin ช่วยลบ...ออกหน่อย; universal re-ask |
| S05 | A | medium | plain | food | one-of-several | kind | no | yes | yes | bin ลบ...ออก; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE; pronoun re-ask; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S06 | B | medium | plain | person | one-of-several | attribute | age | no | no | bin อย่าจำ; other facts on the target subject; unrelated-fact probe asks one of them; abstract value (age) |
| S07 | B | medium | kha | animal | one-of-several | location | no | yes | no | bin ไม่ต้องจำ...แล้ว; other facts on the target subject; unrelated-fact probe asks one of them; pronoun re-ask |
| S08 | A | medium | plain | place | one-of-several | possession | no | no | yes | bin ช่วยลบ...ออกหน่อย; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE |
| S09 | B | long | plain | object | one-of-several | kind | no | yes | yes | bin ลบ...ออก; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE; pronoun re-ask; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S10 | A | long | khrup | food | one-of-several | attribute | taste | yes | yes | bin ลบ...ออก; decoy entity present, its fact NEVER probed; other facts on the target subject; unrelated-fact probe asks one of THOSE; abstract value (taste); pronoun re-ask; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |

Scored-turn rule: instruction turn: {unknown, acknowledge}; universal final re-ask probe: {unknown, abstain}; one-of-several items add an unrelated-fact recall probe: {supported, answer}

#### correction slot table

| Slot | Author | Length | Register | Entity | Subtype | Shape | Abstract value | Pronoun | Decoy | Scored turns / notes |
|---|---|---|---|---|---|---|---|---|---|---|
| S01 | A | short | plain | person | marker-ขอแก้ไขข้อมูลเดิม: | kind | no | no | no | post-correction probe (scored); person-kind value from role/relationship/nationality (not occupation) |
| S02 | B | short | khrup | animal | marker-แก้ไข:(bare) | attribute | color | no | no | abstract value (color); post-correction probe |
| S03 | B | short | plain | place | marker-เปลี่ยน X เป็น Y | attribute | size | no | no | abstract value (size); post-correction probe |
| S04 | A | short | plain | object | marker-ไม่ใช่ X แต่เป็น Y | kind | no | no | no | negation form ไม่ใช่; post-correction probe |
| S05 | A | medium | khrup | food | marker-ขอแก้ไขข้อมูลเดิม: | location | no | yes | yes | pronoun in post-correction probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S06 | B | medium | khrup | person | marker-ไม่มี X แต่มี Y | possession | no | no | yes | negation form ไม่มี; post-correction probe |
| S07 | B | medium | plain | animal | marker-ไม่ได้อยู่ X แต่อยู่ Y | location | no | yes | no | negation form ไม่ได้+verb; pronoun probe |
| S08 | A | medium | kha | place | marker-เปลี่ยน X เป็น Y | attribute | count | no | yes | abstract value (count); post-correction probe |
| S09 | A | long | kha | object | marker-แก้ไข:(bare) | possession | no | yes | yes | pronoun in post-correction probe; decoy: person, discourse-unavailable at the pronoun (taught and closed before the antecedent's introduction, never re-mentioned; pronoun at most one turn from the antecedent; decoy absent from the pronoun's turn and the turn before) |
| S10 | B | long | kha | food | marker-ขอแก้ไขข้อมูลเดิม: | kind | no | yes | no | pronoun in post-correction probe |

Scored-turn rule: instruction turn: {supported, acknowledge}; universal post-correction probe: {supported, answer}

## 5. Scored-turn protocol (multi-turn evaluation)

Register audit acceptance rule (Phase 6). Audit UNITS are: (a) the
subtype bins of each category table, (b) sentence-shape bins,
(c) request-construction / correction-marker bins, (d) scored-turn
target labels. For each unit the audit tabulates register x unit
across the annotated set. A bin with exactly ONE occurrence set-wide
is reported descriptively and cannot fail. A bin with two or more
occurrences FAILS the audit if all its occurrences sit in one
register. The pinned tables satisfy this by construction (checker-
verified, including the set-wide slot diversity that keeps
cross-category bins like the action shape register-diverse); the
Phase 6 audit re-verifies it against the annotated set. The audit
makes NO statistical-independence claim (N=70 cannot support one).
Phase 6 VALIDATES the pinned antecedent count on ALL 28 pronoun
slots (4 per category x 7, checker-pinned) against each author's
self-check record (section 6 rule 8): exactly 0 on
unknown S03+S04, exactly the intended 2 on ambiguity S07-S10
(including the same-name S09), exactly 1 on every other pronoun slot.
The count check covers EVERY recorded pronoun occurrence in the item,
not one aggregate per slot.
Phase 6 ADDITIONALLY performs the deeper discourse-unavailability
audit on the 15 pronoun+decoy slots - exactly 15, pinned in the
checker: recall
S05+S10, unknown S05+S09, contradiction S05+S10, ambiguity S07+S09,
teach S05+S09, forget S05+S09+S10, correction S05+S09 - verifying
the G-AX4 orderings and turn-absence conditions as authored. BOTH
audits are ACCEPTANCE GATES:
an item that fails either is rejected and fixed before the set is
accepted.

Every probe and instruction turn listed in a slot table is a SCORED
turn with the expected label named in the category's scored-turn rule
(under each table). Setup turns and agent acknowledgements during
setup are context-only. A scenario still counts as 1 item toward
N=70 regardless of how many scored turns it carries; annotations are
per scored turn, and the item's disposition follows the criteria's
item-level rule. Authors MUST write the expected label of every
scored turn into the item's annotation target.

## 6. Thai language rules (binding on authors)

1. Natural, script-correct Thai (criteria G2); telegraphic
   word-separated Thai is neither required nor targeted.
2. คือ takes an identifying Y (ผู้จัดการคือคุณสมชาย); class membership
   uses เป็น; the skill sense of เป็น (เล่นกีตาร์เป็น) is FORBIDDEN.
3. Locations use อยู่ที่ or อยู่ใน. Counts use correct classifiers
   (ตัว/คน/ใบ/อัน).
4. ลืม is non-volitional: forget requests use the pinned verb bins
   (ลบ/อย่าจำ/ไม่ต้องจำ...แล้ว/ช่วยลบ...ออกหน่อย), never ช่วยลืม.
5. Attribute shapes bind to the host entity's own attributes;
   abstract-domain values appear only in attribute/kind/identify
   shapes (entity x shape matrix is checker-enforced).
6. Confirmation-seeking frames (ใช่ไหม, ไม่ใช่...หรือ) must carry one
   unambiguous implied proposition.
7. Polite bins: question-final คะ counts as ค่ะ; "…ค่ะ?" is FORBIDDEN.
8. ANTECEDENT SELF-CHECK (binding on authors): for every pronoun
   slot, the author records at each pronoun occurrence ALL
   defensible antecedents a reader could entertain - not only the
   intended ones; the count must follow the pinned expectation
   (G-AX4): exactly 0 on the missing-referent exemptions (unknown
   S03+S04), exactly the intended 2 on ambiguity's four pronoun
   slots (S07-S10, including the same-name S09), and exactly 1 on
   every other pronoun slot. The record ships with
   the item for the Phase 6 audits (section 5), which are
   acceptance gates: a failing item is rejected and fixed before the
   set is accepted.

## 7. Relation exclusivity and value compatibility

- Every (subject, relation) pair is SINGLE-VALUED within a scenario.
- Possession facts use a count with classifier, an exclusivity cue,
  or an explicit ไม่มี, so a second possession is never "replace or
  add" ambiguous.
- Contradiction and correction replacement values MUST be plainly
  incompatible (white vs black; 2 vs 5). Replace-vs-add ambiguous
  pairs (occupation vs occupation for a person who could hold both)
  are FORBIDDEN.

## 8. Anti-overlap, fictional scope, and naming (honest version)

1. Authors MUST invent fresh scenario facts and MUST NOT reuse the
   criteria examples they can see. Authors CANNOT check overlap with
   the dev set or preflight examples, which they never see: the
   Phase 6 overlap gate (spec section 5) is the sole enforcement for
   hidden overlap, and it is an acceptance condition of the set.
2. All named entities are fictional: no real personal data, no real
   public figures or famous animals (e.g. หมูเด้ง), no invented place
   names that coincide with real provinces/districts/villages, no
   names appearing in criteria examples.
3. Entity names are UNIQUE across the whole set, except the intended
   same-name pairs in ambiguity items.
4. Within one item, the same fictional name never refers to two
   different entities except by design in ambiguity items.

## 9. Limitations (stated, binding on reports)

- The axes are COVERAGE CONTROLS, not strata: cell sizes of 1-4
  cannot support per-axis pass-rate reporting. Reports describe
  coverage, never per-axis competence.
- AI-authored Thai is not human-validated: items may be awkward or
  unintended-ambiguous even when script-correct; the "AI เขียน /
  not human-validated" label is never upgraded.
- Zero anaphora and word-segmentation ambiguity are out of scope;
  coverage of Thai anaphora is partial by design.
- The checker proves only its implemented structural checks on the
  slot tables. It does not establish that authored Thai will be
  natural, that scored turns will be authored correctly, or that the
  Phase 6 audit will pass on the annotated set.
- Register variation tests memory behavior across surface registers,
  nothing social or demographic.
- Pronoun coverage is skewed by the pinned hosts: food 12/14, object
  8/14, animal 6/14, place 2/14, person 0/14 pronoun uses; เขา and
  พวกเขา are never exercised, and the three pronoun-ambiguity items
  pair animals, places and food - never two people, the canonical
  Thai case. Fixing this needs a fresh allocation search and is
  deferred to a later plan version; reports must not claim
  person-pronoun coverage.
- มัน for places (ambiguity S08) is marginal Thai; demonstratives
  (ที่นั่น, ตัวนั้น, อันนั้น) stay OUTSIDE the closed inventory and
  the awkwardness is accepted for v1, under the AI-authored /
  not human-validated label.
- No forget bin uses plain ลืม... (the most common Thai imperative
  for forgetting): the omission is INTENDED - the four pinned
  constructions exist for request-phrasing diversity, and ช่วยลืม
  remains banned (section 6). v1 does not cover plain ลืม.
- Antecedent uniqueness on pronoun slots is enforced by discourse
  conditions, an author self-check and a Phase 6 spot audit - NOT by
  any grammatical certainty: Thai allows มัน for humans in informal
  registers, and discourse accessibility is graded, not binary. The
  residual risk on pronoun+decoy slots is declared here, not
  guaranteed away.

## 10. Pinning mechanics (pre-hash checklist)

1. Remove the "DRAFT / NOT PINNED / review" status text before
   hashing; the pinned artifact must not call itself a draft.
2. Canonical bytes: UTF-8, no BOM, LF line endings, final newline,
   Thai in NFC. Hash the COMMITTED file, never a pasted copy.
3. Record the diff between the reviewed draft and the pinned text
   alongside the attestation.
4. scripts/thai-phase2-slot-check.py passes; its sha256 and the
   plan's sha256 both enter the freeze attestation (spec 6.1), with
   the plan's version recorded next to the script docstring's
   version. The canonical-bytes rule (step 2) applies to the script
   too. Run scripts/thai-phase2-slot-check.py --verify-plan <plan
   file>: it must print ok (section 4.8 tables identical to --emit,
   canonical bytes of both files).
5. Any post-pinning change: new plan version, fresh GPT+Claude
   review, re-issued attestation entry, BEFORE any affected item is
   generated.

## Annex A: capability-level description (the ONLY system knowledge authors get)

The examinee is a Thai-capable conversational memory agent. At the
CAPABILITY level (no code, no outputs, no failure modes):

- It accepts Thai teaching statements asserting one fact about an
  entity: kind/class (X เป็น Y, X คือ Y with an identifying Y),
  possession (X มี Y, optionally counted with classifiers), location
  (X อยู่ที่/อยู่ใน Y), attribute values (color, age, size, count; a
  person's occupation; the taste of food or drink, including
  spiciness), and simple action/ability.
- It answers Thai questions asking for a previously taught value.
- It handles requests to forget a taught fact (request phrasing
  varies).
- It handles explicit corrections of taught facts (the user marks the
  correction explicitly; marker phrasing varies).
- Scenarios are usually multi-turn: setup turns teach, later turns
  ask or assert; the shortest teach items may be a single turn (the
  instruction itself creates the fact). Polite particles are optional
  on every turn.
- Each scenario starts in a fresh conversation with no retained facts.
- Authors MUST NOT assume anything beyond this list: no specific
  wording requirements, no knowledge of internals, no expectations
  about reply style beyond the frozen criteria's acceptability rules.

