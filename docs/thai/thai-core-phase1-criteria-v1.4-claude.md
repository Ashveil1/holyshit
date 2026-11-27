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
