# Slot-side teaching - design (planning only, NOT built, 2026-10-26)

Status: design for review. No code, no integration. B-577 established that on
unseen templates the slot side dominates end-to-end failure (wrong-execution
74-92% of acted items even at zero wrong-intent). Intent gating alone cannot
deliver correct actions.

## The natural exchange (Thai example)

1. User says a new phrasing: "งา ของ เหยี่ยว สวย" (marker mid-sentence).
2. Intent gate fires (low margin). System asks ONE intent question in
   natural language, offering paraphrases, not internal labels:
   "อันนี้คือกำลังบอกว่าของเหยี่ยวสวย ใช่ไหม หรือถามว่าอะไรสวย?"
   User picks/confirms in their own words. (Intent teaching = B-573/574
   channel; teacher supplies the intent choice.)
3. Slot stage: the system does NOT ask for annotations. It echoes its
   guessed parse as plain-language confirmations, ONE question per uncertain
   slot only:
   "เข้าใจว่า 'งา ของ เหยี่ยว' คือสิ่งที่สวย ใช่ไหม?"
   - yes -> that span-role pair becomes a confirmed example.
   - no  -> system offers its next candidate span(s) as a short choice;
     the user's pick becomes the confirmed example. If no candidate is
     right, the user retypes the value (free text = exact span).
4. Only when every required slot for the confirmed intent is either
   confidently parsed or teacher-confirmed does the system act.

## Exact teacher information supplied

- Intent choice (paraphrase selection or free rephrase -> nearest intent).
- Per-slot: binary confirmations of proposed span-role pairs, a pick among
  offered spans, or a retyped value. No role names, no schema, no
  coordinates are ever exposed to the user.

## What is acquired vs supplied

- SUPPLIED (designed): the role inventory per intent (it is the action API -
  teach_attr needs target/attribute values to run at all), the candidate
  span generator, the confirmation dialogue shape.
- LEARNED: the mapping from utterance spans to roles - a per-role span
  scorer trained on confirmation labels (positive/negative span-role
  pairs), incremental like the intent mapper. Roles are never acquired from
  scratch; the claim is learned span-to-role assignment only.

## Error containment

- Per-slot confidence gate with its own dev-calibrated threshold; uncertain
  slots trigger exactly one targeted question each, not a re-ask of the
  whole utterance.
- No execution on unconfirmed/uncertain slots: the system asks or abstains.
- Confirmed examples accumulate; wrong-execution (intent AND slots), acted
  coverage, abstention, and questions-per-family are reported together with
  exact denominators (B-577 metric discipline).
- Teacher burden is a first-class cost: candidate ranking should put the
  right span in the top offers; if it cannot, burden grows linearly with
  slots and the design fails its utility bar.

## Known risks / honest limits

- Simulated-teacher evaluation can only use gold slots as the oracle; that
  is authored validation, and the requester's real willingness to answer per-slot
  questions is UNTESTED by any of this.
- Span supervision per family may not transfer across families; retention
  and interference of learned span scorers are unverified.
- This adds a second learned component and a confirmation dialogue - a
  materially bigger build. Planning authorized 2026-10-26; implementation
  awaits direction.
