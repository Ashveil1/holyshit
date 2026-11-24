# agent — a small local agent written in pure holyshit

A from-scratch local agent core for the holyshit OS direction. It runs
entirely offline inside the hs runtime: no external model, no
dependencies beyond the language itself. One EXPERIMENTAL exception:
the repl shell can fetch web pages over plain HTTP (`read url`, A18
preview below); the core itself stays network-free.

## What it is today (v0.17)

- An evidence-ingestion reader (A16): `read <text>` ingests text as
  DATA - never executed, never believed - and reports typed claims
  with full provenance: normalized subject/predicate/object, polarity,
  matched pattern id, the verbatim sentence, and the source id. This
  is surface-pattern recognition plus evidence aggregation, NOT
  general comprehension: it extracts only whole-segment claims in the
  existing teach shapes (English is-a/is-in/has/verb forms, the
  plural forms are/are not/have/do not have/does not have, and Thai
  เป็น/ไม่เป็น/อยู่/คือ), and skips - with an honest count per
  mutually exclusive class - quoted/attributed segments (quotes,
  'says'/'said'/'according to'), modal/hedged segments
  (might/may/could/...; the supported can/cannot forms still
  extract), multi-clause segments, command-shaped segments (A19:
  a fixed set of known command forms - the agent's own command
  prefixes remember/no,/mode/clear/forget/read/note/say, the
  standalone commands, and the web imperatives 'click here' /
  'subscribe now' / 'download this file' - matched exactly or as
  whole-segment prefixes; there is NO general imperative parser,
  and a declarative merely containing those words away from the
  start is not skipped), and Thai-Latin boundary segments (A19:
  a mixed-script segment splits at a script transition ONLY when
  BOTH resulting segments independently match complete supported
  patterns - strictly atomic, first valid split wins, spans are
  the side texts; otherwise the whole segment is skipped as
  thai-boundary-ambiguous. It never splits on arbitrary Thai
  spaces, and ครับ/ค่ะ/แล้ว/นะ/ไหม are never treated as
  universal terminators). Skip precedence: quoted/attributed >
  directive > modal-hedged > multi-clause. A17 adds one guarded
  conjunction: a segment is split at its FIRST exact ' and ' only
  when BOTH sides independently match a complete registered pattern
  (strictly atomic, never inside quotes, no recursion; spans are the
  side texts), otherwise the whole segment is skipped as
  multi-clause. Pronoun and existential subjects (i/you/he/she/it/
  we/they/there) are unmatched, never guessed. Plural readings have
  matching teach forms (`remember robots are machines`, `remember
  birds have wings`, `remember snakes do not have legs`), so every
  extracted triple has a supported confirmation path. The read reply
  breaks the tail down as `S skipped (q quoted, d directive,
  h modal-hedged, c multi-clause, t thai-boundary-ambiguous),
  U unmatched`. Extraction quality is measured on a
  frozen fixture corpus (tests/reader_eval.txt, 55 English + 20 Thai
  cases with expected triples, polarity, pattern ids, spans and skip
  classes; tests/eval_reader.py): precision 1.000, recall 1.000,
  zero false extractions on that corpus - a gate for the fixed
  corpus, not a guarantee for arbitrary web text. Positive and negative support are tracked
  separately per claim (`positive_sources[]` / `negative_sources[]`,
  never a majority vote); labels are UNVERIFIED, MULTI_SOURCE (with
  `independence UNVERIFIED`), CONFLICT vs SOURCE-INTERNAL CONFLICT,
  USER_CONFIRMED and USER_DISPUTED. Corroboration is metadata only:
  readings never enter inference, guards, recall, did-you-mean or
  hypothesis generation (a byte-identical query battery with and
  without reads proves the isolation), and only explicit user
  teaching enters asserted knowledge. User alignment is tracked PER
  POLARITY, separate from evidence status: the taught side of a
  record is marked USER_CONFIRMED, recorded support on the opposite
  side is marked USER_DISPUTED, and any CONFLICT label stays -
  confirmation never resolves external conflict, provenance is
  retained either way, and repeated teaching changes nothing (labels
  are assignments, never new evidence). The store is
  session-only, hard-capped at 100 claims; new claims at capacity
  are refused AND reported (N new / M updated / K refused / W
  repeat), updates always allowed, no silent eviction. One source id
  per read (auto `read-N` or an exact `name:` prefix); a source
  repeating a claim counts once, a source contradicting itself is a
  SOURCE-INTERNAL CONFLICT with both readings kept. A19 reports
  evidence as SEPARATE measurements on every multi-source claim:
  agreeing sources (claim agreement is structural - every entry on
  a side supports the same triple; cross-polarity disagreement
  stays the CONFLICT label), registrable-domain diversity (url
  sources resolve through the registry; a literal IPv4 host is its
  own domain; otherwise the last two host labels approximate the
  registrable domain - no public-suffix list; typed sources have
  no domain and never count as diversity), and duplicate-text
  clustering over the support spans (normalized 5-word-shingle
  Jaccard, cutoff 0.8 compared as integers; spans under 5 words
  cluster by exact normalized text; EXPERIMENTAL /
  calibration-needed - a duplicate-text signal only, never proof
  of independent or common authorship). A claim whose side meets
  ALL binding thresholds (3+ distinct source ids, 2+ registrable
  domains - together the no-known-common-origin check
  (A20: content clusters are reported NOT_ASSESSED, similarity is
  not proof of copying) -, no polarity conflict, no user
  alignment on that side, every entry pattern-extracted by
  construction) is labelled SOURCE_DIVERSITY_THRESHOLD_MET (renamed at A20 from REVIEW_ELIGIBLE; 3+ sources and 2+ domains, content clusters NOT_ASSESSED) - an evidence status,
  explicitly NOT a fact, and never a promotion: nothing reads it
  outside the evidence-inspection routes. (Historical note: the A19 3-cluster threshold was unreachable and was dropped at A20; the A20
  recalibration.) A later conflicting reading raises an
  ingest-time evidence-review warning - CONFLICT across sources,
  SCOPE_MISMATCH inside one source - that never alters or demotes
  accepted knowledge. Trust labels stay distinct: taught facts
  are USER_ASSERTED, query-time rule conclusions are DERIVED
  (shown with their premises), read candidates are
  READING_UNVERIFIED, and USER_CONFIRMED / USER_DISPUTED are the
  user-acceptance alignments on a candidate (the
  USER_ACCEPTED_SOURCE notion: acceptance of a source's claim
  happens only through explicit teaching). Each candidate also
  carries a bounded (20) approval/revocation history: confirmed
  and disputed are recorded at teach time, and forgetting or
  correcting the taught edge behind an alignment revokes it -
  recorded, never silently kept. Thai input is
  split crudely and reported as `segments in / pattern matches /
  candidates extracted / skipped / unmatched` - never 'sentences
  understood'. `readings`, `readings about <thing>`, `readings
  detail`, `forget reading <thing> is a <kind>` and `clear readings`
  inspect and manage the candidates.
- An ordered pattern-rule matcher: a fixed set of command patterns is
  checked in order and the first match wins.
- Learning from usage, smallest honest version: for every content word
  in every taught fact (key or value) it counts which other content
  words appear alongside it, across all facts. Two uses, both honestly
  framed: a miss with several `did you mean` candidates orders them by
  co-occurrence with the asked words (was: insertion order), and a
  clean miss on a word that shows up in taught values answers
  `i was never taught X, but from how you used it, X seems related to
  A, B` (top 3 by count, ties by first-seen order). It is counting,
  not understanding: it can say two words appeared together, never
  what the relation is. Thai words participate as whole tokens (there
  is no segmenter). The counts are derived state, rebuilt on load like
  the word index - nothing new is persisted and the v4 format is
  unchanged. Corrections and forgets un-count what they remove.
- Relations and small inference: taught facts whose values take a
  recognized shape also record a relation edge - `remember paris is in
  france` records (paris is-in france), `remember cat is an animal`
  records (cat is-a animal, article kept), `remember cat has whiskers`
  records (cat has whiskers), and Thai `remember แมว อยู่ สวน` /
  `remember ลิง คือ สัตว์` record the same is-in / means edges.
  Thai `remember วัด มี พระ` (A25.1) records the same has edge as
  `remember temple has monk`. It is tried last, so a line that already
  matched another shape keeps that behaviour. Limits: no Thai `มี` question
  form yet, the reader does not extract `มี`, and a second different value is
  stored as another fact, not flagged (A22.1).
  Thai correction (A25.2): `no, <thing> อยู่|คือ|เป็น|มี <value>` replaces only
  that thing's existing facts of the SAME shape and keeps the rest. A thing it
  does not know, or one with no fact of that shape, replies `nothing to correct`
  and changes nothing. Several old facts of that shape are all replaced by the
  one new value, and the reply says how many. This is replacement, not conflict
  detection (A22.1 is audit-only). `no, X is Y` in English still replaces
  everything about X. Not covered: หมายความว่า, ไม่เป็น, and corrections
  that name no thing.
  Thai pronouns (A25.3): a fixed list of 20 exact pronoun spellings (มัน, เขา,
  อันนั้น, ตัวนั้น ...) in a question gets a clarification, never a guess: `did
  you mean <topic>? clarify by saying the name` when a topic exists, else `clarify:
  which thing do you mean by <word>?`. It offers the topic as a question only; no
  state, topic or log change, no topic resolution. A taught key or alias with the
  same spelling resolves normally. English pronouns are unchanged. Not covered:
  ใคร, ที่ไหน, and มี-questions (they stay `i do not understand`).
  Also fixed: the about-reply length guard now counts non-ASCII tokens as long
  (matches native; only the interp route changed).
  `is paris in europe` then answers by transitive closure over those
  edges and shows the chain it used (`yes: paris is in france, france
  is in europe`); a miss is open-world honest (`not that i know`,
  never a claimed `no`). `where is paris` walks the is-in chain
  outward, `what does X mean` answers from taught means-edges plus a
  small hard-coded self-knowledge set defining the agent's own
  relation words (mean/is-in/is-a/has - documented as hard-coded, not
  learned), and `<phrase> means <free text>` now defines a phrase
  directly instead of erroring on unknown targets. `means`,
  `หมายความว่า` and `คือ` write the same edge. Thai questions get
  Thai-framed replies (`แมว อยู่ไหน` -> `แมว อยู่ สวน`).
- A teachable memory: several facts per thing (`remember X is Y` sets,
  `remember X is also Y` adds), user-taught paraphrases
  (`<phrase> means <thing>`), kept in a plain JSON-serializable Dict
  (`agent/core.holy`), with hosted file persistence (`agent/store.holy`)
  and a terminal chat loop (`agent/repl.holy`).
- Teaching by correction: `no, X is Z` replaces the facts for X with Z
  (and updates the session topic), so a wrong or stale taught fact can
  be fixed without `forget` plus a fresh `remember`.
- Wider dialogue, honest by construction: open questions
  (`how is X`, `why is X`, `how about X`, `tell me everything about X`,
  Thai `เกี่ยวกับ X`) read back the taught facts framed as
  `all i know about X is ...` - never a pretended answer to the how or
  why; Thai `<thing> คืออะไร` asks what-is; a small pleasantries layer
  (hello/how are you/thanks/bye, สวัสดี/ขอบคุณ) answers with fixed,
  visibly mechanical strings; `and X` recalls X, and `what else` /
  `anything else` continues the session topic.
- A little dialogue context: it tracks the current topic and follows
  `what about it` / `forget it`; when a question misses but a handful of
  taught things overlap its words it asks `did you mean ...?` and
  understands `yes`, `no`, or the name; and it keeps short-term session
  `notes` that are never saved to disk.
- Association recall: `what do you know about X` answers with the taught
  facts plus others whose words overlap them (ASCII word match, glue
  words excluded) - string overlap, not understanding.
- Thai-aware matching: text is normalized without ASCII-izing, and
  non-ASCII tokens (Thai has no spaces or case) also match by
  substring - so `คนไทย` finds `ไทย` and `เมืองหลวง` finds `บางกอก`.
  The guard is deliberately independent of string length semantics:
  the interpreter counts characters while the compiled backends count
  bytes, so matching uses containment plus identity checks only, never
  a length threshold. Single ASCII letters never substring-match, so
  `c` still does not find `cat`.
- A derived word index: taught key words map to their keys, so misses
  and `did you mean` checks look up words instead of scanning every
  taught fact, and membership checks use a key set instead of walking
  the key list (see the benchmark section). Both are rebuilt on load
  and maintained on teach/forget; neither is persisted.
- Relation edges (`rels`) persist in the v5 store format (which adds
  the `forgotten` tombstone list); pre-v5 files re-derive edges from
  their fact shapes on load, once, and the built-in self-knowledge
  edges are never persisted.
- A bare `X is Y` teach whose value matches no known shape still files
  a kind-of edge and says so (`(filed as a kind-of)` in the reply) -
  deliberately shallow: `sky is blue` files blue as a kind of sky.
  `is X Y` asks over the is-a chain without needing an article; Thai
  yes/no questions `<X> เป็น <Y> ไหม` and `<X> คือ <Y> หรือไม่` answer
  over the same chains, and a trailing `?` forces question mode
  (`apple means fruit?` checks instead of teaching).
- Typed verb relations with three-valued answers: `needs`, `can`,
  `uses`, `produces`, `causes` are stored as their own edge types, and
  questions about them INHERIT down the is-a chain
  (`does dog need energy` answers yes from dog -> mammal -> animal ->
  living thing, showing the full chain). Answers are TRUE (direct or
  inherited, chain shown), FALSE (an explicitly taught negative like
  `a fish cannot fly`, chain shown) or UNKNOWN (`not that i know`) -
  unknown is never collapsed into false. The nearest node on the
  chain wins; opposing claims at the same distance are a
  contradiction, flagged at teach time and reported at query time,
  never silently resolved. Query forms normalize through a FIXED
  verb-form table (active `does X need Y`, `can X Y`, passive
  `is Y needed by X`); it is a lookup table, not morphology.
- Compositional inference rules: a fixed, inspectable rule table (in
  `agent/core.holy`, data not hidden logic) composes two relation
  edges into one derived edge. The five rules: `has+uses => uses`,
  `has+can => can`, `uses+can => can`, `has+produces => produces`,
  `uses+produces => produces`. Only listed rules fire - there is no
  invented inference - and rules compose recursively (depth cap 6,
  cycle-safe), so `can a car produce motion` answers yes from
  `a car has an engine` + `an engine uses energy` +
  `energy can produce motion`, showing each rule step with its
  premises. Two hard guarantees: capability stays capability (every
  rule with a `can` premise concludes `can`; nothing ever turns
  `can` into a doing or having-done fact), and `has` stays
  non-transitive (no rule concludes `has`, so
  `does a car have motion` stays honestly unknown). Rules never build
  on a premise with taught negative or contradicted evidence; a
  rule-derived positive that collides with a taught negative is
  reported as a contradiction with its reasoning, never silently
  resolved. Rules are pure query-time derivation - the store format
  is unchanged.
- Domain guards on those rules: every rule declares the kind its
  conclusion's subject must belong to (all five current rules declare
  `machine` - the domain they were validated in), because ownership is
  not participation and a part's capability is not the whole's. The
  guard is an inference CONDITION, not a truth claim: membership says
  the rule may apply here, not that the composition is sound. Each
  rule step checks only its own subject (the middle object is never
  forced into the domain - `a pilot has a license` must not require
  licenses to be machines), and membership goes through the ordinary
  is-a chain, so a subclass satisfies the domain. Two modes: STRICT
  (the default) blocks the rule and explains exactly why - the three
  explanations stay distinct: unknown domain
  (`i do not know whether X is a machine`), taught negative
  (`X is not a machine`), and taught conflict (`i was taught both`),
  and a failed guard never makes the relation itself false - a taught
  negative still answers `no` outright when the opposing rule was
  blocked. EXPLORE (`mode explore`, session-only, `mode` shows the
  current one) lets the rule fire conditionally: the conclusion is
  headed `yes, on N assumption(s):`, every assumption is consolidated
  into one block with a step reference
  (`(a) a car is a machine - assumed at step 2, unverified`),
  duplicates merge, and an assumption NEVER becomes a fact -
  conditional conclusions stay conditional downstream and strict mode
  blocks the same world again. Thai negative domain teaches
  (`remember a pilot ไม่เป็น machine`) participate in guards like
  any other.
- Bounded hypothesis learning: explore-mode assumptions are recorded
  as named, inspectable candidates - the missing knowledge the engine
  leans on, exposed so the user can resolve it. A candidate is NEVER
  a fact: nothing reads the list for inference, guards, recall,
  contradiction detection or suggestions, and strict mode records
  nothing (a candidate used any number of times leaves strict
  queries unknown and compositions blocked). `hypotheses` lists open
  candidates (labelled as unresolved candidates, not beliefs) with
  use counts and first-seen questions; `hypotheses detail` adds the
  creation event and the 10 most recent uses, older ones marked
  omitted. Teaching retires deterministically - a positive verdict
  lets strict guards pass, a negative one leaves strict blocked, a
  taught conflict stays a conflict - and a candidate plus an asserted
  negative is just FALSE (the candidate is not evidence, so no
  contradiction). Hard stop at 20 candidates, no auto-eviction (age
  or count cannot prove an unresolved assumption safe to destroy);
  `forget hypothesis <thing> is a <kind>` and `clear hypotheses`
  free space, and a full list says so when a recording is rejected.
  Session-only, like notes and mode: no store-format change, no
  auto-promotion, ever.
- Bounded self-knowledge: `what do you know` counts taught things and
  names the 5 most recent, `what did you forget` lists the tombstones
  it keeps (last 20), `what did we talk about` replays the session log
  (last 10 events, this session only, never saved). Each answer
  states its own bound.
- Pure and portable: the core never does IO. `respond(state, line)`
  returns a reply, so the same core can later run freestanding in the
  kernel. Memory footprint is a few KB plus exactly what it was taught.

Commands: `remember <thing> is <fact>`, `remember <thing> is also <fact>`,
`remember <thing> has <part>`, `remember <thing> เป็น <kind>`,
`remember <thing> needs/uses/produces/causes <thing>`,
`remember <thing> can <verb>`, `remember <thing> cannot <verb>` (and
`does not need/use/produce/cause` forms),
`remember <thing> is not a <kind>`, `remember <thing> ไม่เป็น <kind>`,
`no, <thing> is <fact>` (correction),
`what is <thing>` (aliases: `do you know`, `tell me about`, `who is`),
`is <thing> in <thing>`, `is <thing> a <kind>`, `is <thing> <kind>` (bare is-a question),
`does <thing> need/use/produce/cause/have <thing>`, `can <thing> <verb>`,
`is <thing> needed/used/produced/caused by <thing>` (passive),
`where is <thing>`
(is-in chain), `what does <thing> mean` (means relation + built-in
self-knowledge), `what do you know about <thing>`, `how is <thing>`,
`why is <thing>`, `when is <thing>`, `how about <thing>`,
`tell me everything about <thing>`,
`เกี่ยวกับ <thing>`, `<thing> คืออะไร`, `<thing> หมายความว่าอะไร`,
`<thing> อยู่ไหน`, `<thing> เป็น <thing> ไหม`,
`<thing> คือ <thing> หรือไม่` (Thai yes/no questions), `and <thing>`,
`what else`,
`anything else`, `what about it`, `<phrase> means <thing>`,
`forget <thing>`, `forget it`, `what do you know`,
`what did you forget`, `what did we talk about`, `note <text>`, `notes`, `clear notes`,
`read <text>`, `readings`, `readings about <thing>`, `readings detail`,
`forget reading <thing> is a <kind>`, `clear readings`,
`list`, `say <text>`, `help`, plus fixed pleasantries (hello/hi/hey,
how are you, thanks/thank you, bye/goodbye, สวัสดี, ขอบคุณ).
One trailing `?` or `.` is ignored.
Anything else gets an honest `i do not understand`.

## EXPERIMENTAL: read url (A18 preview)

The repl shell accepts `read url <http-url>`: it fetches the page over
plain HTTP and ingests the extracted text through exactly the same
evidence pipeline as typed `read` - candidates stay UNVERIFIED
readings, never facts, and questions are never answered from readings.
This is an explicitly labelled EXPERIMENTAL preview, not a release:

- **Hang risk (known, documented):** the hs runtime has no bounded
  receive timeouts yet (see
  `docs/gap-report-bounded-recv-timeouts.md`), so a silent or stalled
  peer can block the repl forever. This is the reason A18 ships as a
  preview; A18.2/A18.3 wait on the runtime fix.
- **Plain HTTP only:** no TLS, no authentication, no integrity. Only
  `http://` URLs, no credentials, no fragments, port 80 only and no
  private/reserved literal IPv4 addresses outside the test harness
  (`HS_AGENT_TEST_FETCH=1`, set only by the repl from the environment,
  unlocks `127.0.0.1` and other ports for the fixture tests).
- **Strict response checks:** HTTP 200 only (redirects are rejected,
  not followed), `text/*` content types only, identity content- and
  transfer-encoding only (chunked is rejected), Content-Length
  consistency enforced, NUL bytes in the first 8 KiB reject the body,
  16 KiB header cap, 1 MiB whole-response cap.
- **Bounded extraction:** page text is capped at 64 KiB before
  ingestion, the trailing partial segment is dropped, and the reply
  says so.
- **Honest html-to-text:** script/style/title blocks are dropped,
  tags removed, six common entities decoded, whitespace collapsed.
  Command-like page text ("clear readings", "quit", "click
  here") matches the A19 directive skip class: skipped whole as
  inert data, never executed and no longer extracted at all
  (pinned by tests). Fake confirmation text
  ("USER_CONFIRMED", "TRUSTED", "VERIFIED") on a page is likewise
  just text: it never changes a candidate's UNVERIFIED label.
- **Source identity, not corroboration:** each normalized URL is one
  `url-N` source (lowercase scheme/host, default port stripped,
  fragment removed, path/query preserved); re-reading the same URL
  counts as a repeat fetch of the same source, never as independent
  support. The registry caps at 100 distinct sources and lives for the
  session only (`clear readings` resets it). `readings detail` lists
  sources with the query string redacted (`?(redacted)`).
- **Failed fetches are transactional:** any failure (network, status,
  policy, parse) adds zero candidates and no registry entry.
- **Thai and UTF-8:** pages are decoded with a pure-hs UTF-8 decoder
  (`agent/utf8.holy`: ASCII, Latin-1, Thai U+0E00-0E7F; everything
  else becomes U+FFFD). A Thai sentence glued to a following
  English one in a single segment hits the A19 boundary
  candidate: it splits only when both sides independently match
  complete patterns, otherwise the whole segment is skipped as
  thai-boundary-ambiguous - the old glued-extraction limitation
  is gone, at the price of skipping such segments unless both
  sides validate.
- The core (`agent/core.holy`) contains no network code at all - the
  IR-subset compiler routes reject tcp builtins at build time - so the
  corpus routes keep a deterministic validation-only `read url`
  reply; the fetch lives in `agent/fetch.holy`, imported only by the
  repl.

## EXPERIMENTAL: pattern candidates (A20, offline, inactive)

`patterns derive FILE` proposes reader-pattern CANDIDATES from an
annotated example set. A candidate is an inactive proposal: it never
extracts, matches inside a read, answers a question, changes a count
or counts as reader coverage. The core and the knowledge store do not
reference the generator (a test asserts it) and the reader transcript
and `agent-memory.json` are byte-identical with the proposals file
absent, present, rejected or corrupt. Activation is a later,
human-approved milestone (A21); nothing here promotes anything.

- Input: JSON `{"examples": [[text, subject, verb, object, predicate,
  polarity], ...], "corpus": [...optional segments...],
  "negatives": [...optional annotated non-matches...]}`. The
  annotation must cover the WHOLE segment as `subject verb object`.
- Scope (A20): explicitly annotated transitive declaratives only,
  English/ASCII only. Predicate must be in the running registry
  (is-a, has, is-in, means); polarity is copied from the annotation.
  No new semantic relations. Compound subjects, adjectives, verb +
  prepositional phrase, attributed, modal, pronoun and Thai shapes
  are deferred; directives stay inert in the reader.
- Matching is complete-structure and fails closed: the relation verb
  is a LITERAL that must occur exactly once; subject and object
  slots are the annotated spans only (1-4 plain alnum tokens, no
  function words, negation, modals, attribution words, pronouns or
  punctuation); no wildcards.
- Induction needs >= 3 agreeing annotated examples (same verb,
  predicate, polarity). Conflicting annotations yield no candidate
  and are reported. The held-out split happens before induction:
  3 examples = training only, reported "no held-out coverage" (not a
  failure); 4-9 hold one out; 10+ hold a fixed 20%. A held-out
  failure stays visible and blocks approval.
- Each candidate carries generated tests, kept in separate counts:
  positive replay, structural negatives (negation, modal,
  attribution, trailing clause, unrelated verb, quoted, punctuated,
  boundary ambiguity, missing argument), supplementary single-token
  mutations (only literal removals are labeled negative), the frozen
  curated adversarial set, and annotated negatives. Any failure
  blocks approval. `expected coverage gain` counts corpus segments
  the candidate would match that the reader does not; it ranks below
  correctness and ambiguity.
- IDs are content-addressed (`pc-` + hash of the full canonical
  descriptor: language, skeleton, slot constraints, predicate,
  polarity, schema version). Provenance and history live outside the
  identity. Re-deriving is idempotent; an id collision with a
  different descriptor is refused.
- Lifecycle commands: `patterns list`, `patterns reject ID` (stays
  rejected through re-derivation until `patterns reopen ID`),
  `patterns retract TEXT` (candidates induced from a retracted
  example go STALE and stay approval-blocked).
- Storage: separate versioned file `agent-patterns.json`, validated
  on write (tmp write read back and checked, then final write read
  back and checked). Gap: the language has no rename builtin, so this
  is validate-then-write, not an atomic rename. An invalid file loads
  as an empty store.
- Counts: the 41-segment Grammar Observatory inventory is frequency
  in the frozen eval data, not natural-language frequency.

## EXPERIMENTAL: shadow, delegated review, learned patterns (A21)

Learned patterns are an opt-in experiment, off by default, positive
polarity only, and revocable. They never become facts. What exists:

- `patterns shadow ID` runs a candidate over every source you read and
  records where it WOULD fire, next to the handwritten reader (new,
  agree, disagree, skip-overlap, competing). Shadow shows where a
  pattern fires, not that its reading is right. Segments are counted by
  content ID, so copies never count twice. Sensitive sources
  (`patterns sensitive SRC`) keep counters only and purge anything
  already retained. Sentence text is stored only after `patterns
  samples on`.
- `patterns review ID` freezes a snapshot hash (descriptor, tests,
  provenance, counters, origins, lineage graph, dispositions). Readiness
  needs 50 distinct matches and 50 distinct non-matching segments from
  verified-independent origins, 3 origins with 10+ matches each, no
  origin above 60%, and every disagreement dispositioned. These floors
  are provisional.
- Origins and lineage are declared, not detected: `patterns origin`,
  `patterns lineage` (an agent may only propose an edge; verifying one
  needs `owner` or `documented:REF`). Domains are reported, never used
  as proof of independence.
- Approval: two owner-attested reviewer attestations from distinct
  lineage families, runs and deployments, neither in the proposer's
  family, each covering the frozen packet exactly, under an
  owner-relayed, versioned delegation. A fixed gate returns stable
  codes (A01-A09). Reviewers cannot change their own scope; owner
  approval cannot override a technical failure.
- `patterns activate ID` re-checks everything. The REPL loader
  re-checks every ACTIVE pattern before each command (L03, L05-L10,
  L12) and disables a failing one, keeping its approval in history.
  `patterns revoke ID` takes effect immediately.
- The core holds a pure matcher. It runs only on a segment the
  handwritten reader neither skipped nor extracted, records every match
  separately, flags ambiguity, and keeps results in a session-only
  learned section (`patterns learned`), outside `readings`, the
  SOURCE_DIVERSITY count and `agent-memory.json`. A lifetime log
  (`agent-learned-log.json`) keeps counters and at most 200 entries.

Limits, stated plainly:

- Identity of a reviewer is NOT authenticated. The `owner` marker on
  `patterns attest` is a convention: nothing in this runtime can prove
  who typed it. There are no signatures, so runner-authenticated
  attestations are not offered.
- All hashes are a 62-bit polynomial hash: fine for detecting change,
  not tamper-proof. Approval needs a real SHA-256 before any general
  release; the language has none yet.
- No clock: timestamps in attestations are whatever the reviewer wrote.
- Sensitive-source markers hold raw source IDs (needed to enforce the
  exclusion); keyed HMAC is blocked on the same missing primitive.
- Learned readings are not persisted across sessions except as log
  counters; the thresholds are not ratified; one reviewer family
  label is not proof of independent training data.

### A22.0: change detection for learned-pattern files

This is CHANGE DETECTION ONLY. `agent-manifest.json` records a hash of
`agent-patterns.json`, `agent-attestations.json`, `agent-delegation.json`
and the learned log. The hash is the 62-bit polynomial hash, so it notices
that a file changed outside the repl; it does not prove who changed it and
an attacker who can edit files can edit the manifest too. Real tamper
resistance waits for SHA-256 / signatures (language lane, C20).

- The repl seals the manifest after `patterns *` commands, after learned
  logging and at exit. It checks it only when an ACTIVE learned pattern
  exists, so reader output is unchanged for everyone else (A20 isolation).
- On a mismatch nothing learned loads, one integrity note is printed, and
  the owner must run `patterns manifest accept` after inspecting the files.
  Upgrading from A20/A21 with pattern files but no manifest needs one
  `patterns manifest accept` before learned patterns load again.
- New loader code L13: an approval made under another hash algorithm is
  void. The manifest and approvals record `hash_algo`, so a future SHA-256
  migration invalidates old approvals.
- L10 now rebuilds the positive examples (all must fire, count must match)
  and re-runs the ADV negatives. It does not rebuild structural/mutation
  cases: those triples are not stored in provenance.
- `tests/test_agent_integrity.py` runs a native build and use session under
  `unshare -rn` + `strace`: no network syscalls, writes only in the working
  directory allowlist (including `.tmp` files, since the language has no
  remove builtin), no symlink escapes; the auditor has negative controls.
- Proposal history no longer repeats consecutive identical origin/lineage
  entries.

### A22.1: predicate and argument-type registry

`agent-registry.json` (repl-only, `registry.holy`) holds predicate
signatures (`patterns predicate P SUBJTYPE OBJTYPE`) and entity type
evidence (`patterns type ENTITY TYPE declared|inferred|verified`);
`patterns registry` lists it and `patterns typecheck` audits the stored
relation edges. Declared, inferred, verified and unknown stay distinct.
Only VERIFIED evidence with exactly one verified type raises
TYPE_MISMATCH. Declared or inferred disagreement is shown as an
unflagged suspicion, several verified types are ambiguous and not flagged.
The `verified` marker is an unauthenticated owner convention. Types are
exact names ("any" accepts all); there is no subtype lattice and no entity
identity linking (aliases are never merged, no count changes). The
registry feeds audits only: reader output and `agent-memory.json` are
byte-identical with it absent, present or corrupt
(`tests/test_agent_registry.py`). The file is covered by the A22.0
manifest. Review-packet integration is not built yet.

### A22.2: operational tripwires and the quarantine state machine

`agent-tripwire.json` (repl-only, `tripwire.holy`, covered by the manifest)
only ever DISABLES learned patterns (loader code L14); it cannot approve,
activate or promote anything, and the frozen eval (0 FP) is a separate gate.
Thresholds are PROVISIONAL and unratified.

- T1: `patterns polarity-error ID owner` (one confirmed polarity error)
  disables at once: DISABLED_POLARITY.
- T2: `patterns fp ID SUBJECT PREDICATE OBJECT owner` (underscores for
  spaces) confirms an ordinary false positive. Two confirmed FPs inside the
  rolling window of 200 DISTINCT eligible matches (keyed by a hash of the
  triple; ambiguous multi-pattern matches are not eligible; sensitive
  sources contribute only the hash) give QUARANTINED_PROVISIONAL. The
  200-match window is not the 200-row log cap.
- `patterns quarantine ID REVIEWER`: two distinct AI reviewers give a
  TEMP_QUARANTINE. Reviewers cannot confirm an FP; `owner` quarantines
  directly. Only the owner lifts (`patterns lift ID owner NOTE`), and a
  lifted pattern stays off: it needs a fresh review, the policy gate and an
  explicit approve + activate. Lifetime counters and history are never reset.
- Every state is enforced at the next command, including the current
  session (the loader runs after each tripwire command). A corrupt tripwire
  file fails closed.
- Forget/teach events (privacy_forget, correction, addition, supersession,
  disagreement, preference_change) are classified by prefix heuristics and
  counted, only while a learned pattern is active. Only an explicit
  correction naming a subject of a session learned reading opens an OPEN
  investigation, which is never an automatic confirmation.
- `patterns review ID` now also prints a read-only A22 status block
  (predicate signature, typecheck summary, tripwire state): display only,
  not a gate. The `owner` and `verified` markers remain unauthenticated.
- With no active learned pattern nothing is written and reader output is
  unchanged.

### A22.3: reviewer budgets, suspension and isolated canaries

`agent-reviewers.json` (repl-only, `reviewers.holy`, covered by the
manifest) only ever LIMITS review; it cannot approve, activate or promote.

- Identity assurance ladder (unchanged): self_asserted is recorded, never
  counts and spends no budget; owner_attested is the current ceiling (the
  `owner` marker is an unauthenticated convention); runner_authenticated is
  deferred until crypto exists (C20), refused rather than faked.
- Budgets are MANDATORY since v0.16 (A22.3 first shipped them opt-in):
  `patterns budget FAMILY MAXCANDS MAXWORK owner`. Every owner_attested
  attestation needs a budgeted family: no budget (the refusal names the
  command to run), an exhausted candidate budget or an exhausted
  weighted-work budget (1 + sample events + 3 x disagreement events per
  attestation) REFUSES the attestation (A10); nothing auto-extends and
  usage is never reset. Upgrading: set a budget per family before
  attesting.
- Canaries: `patterns canary FAMILY CASES ANSWERS owner`. A canary is a
  synthetic case file plus the family's answers; scoring reads only those
  files and the reviewer registry. It imports no proposals, tripwire,
  matcher or graph code (the test asserts the imports), and a pool with a
  production reference or a non-synthetic case is refused. Ambiguous cases
  are never scored; unanswered cases are non-critical. A clear CRITICAL miss
  (approving a must-reject case) suspends the family: its attestations stop
  counting (gate A11) and an ACTIVE pattern approved by it leaves use at the
  next command (loader L15). Only `patterns reinstate FAMILY owner NOTE`
  reinstates. The owner-authored delegation file is never edited.
- An unreadable reviewer registry fails closed. Identical rationale across
  approving attestations prints a flag; it is not a rejection.
- Limits: family names, the owner marker and the answers files are
  unauthenticated conventions; canary pools are owner-supplied, not
  validated against ground truth beyond the synthetic/no-reference rules.

### A22.4: leakage guard

A monotonic sequence number (the language has no clock) orders derivation,
shadow start and the first sight of every source (`seq`, `src_first`,
`holdout` in the proposals file). Per candidate, `cutoffs` records
`derive_seq` and `shadow_seq`; they are set once and never overwritten
(unshadow/re-shadow and re-derive keep them, and a re-derive after the
shadow cutoff changes no evidence input). Rules, all in the review packet's
"leakage guard" line and the snapshot hash:

- A source first seen at or before the candidate's shadow cutoff is a
  pre-shadow fact: its segments are excluded from that candidate's evidence
  (counted as `pre_shadow`) unless `patterns holdout SRC owner` declared it
  held out BEFORE the candidate was derived. A source already seen cannot be
  declared held out later.
- A segment whose text equals one of the candidate's derivation examples is
  never validation (`derived_text`).
- `patterns derive` refuses an example whose text appears in the
  learned-pattern log (circular learning across milestones). This works only
  while `patterns samples on` stored the text; with samples off, or for
  sensitive sources, it cannot be checked.
- Candidates from older files get `legacy` cutoffs and a review blocker: their
  existing evidence was never leak-checked.
- Limits: source names are the owner-visible read labels (unauthenticated);
  "demonstrably held out" means declared before derivation, not proven.

### A23.0: self-evaluation harness (report-only)

`selfeval run FILE...`, `selfeval report`, `selfeval ledger` (repl only; `agent/selfeval.holy`).
It runs frozen JSON suites against the reader and prints counts. It changes nothing.

- **Open loop.** No tuning, no auto-disable, no change to knowledge, patterns or replies. Nothing reads the report back.
- **Report vs ledger.** The report (`agent-selfeval-report.json`) is deterministic: build, suite hashes and config only, with a `report_hash`. It has no counter and no time. Running twice gives identical bytes. The ledger (`agent-selfeval-ledger.json`) is append-only, holds a run counter and each `report_hash`. A corrupt ledger is not overwritten; the report is still printed.
- **Status dimensions** are kept apart: epistemic (supported / unknown / contradicted / ambiguous), verification, action. Classifier `c2` reads them off reply text prefixes (c1 plus one rule: a reply starting `updated ` is `acknowledge`; see the baseline note below). That is a heuristic and can drift if reply wording changes.
- **Numbers.** Per category: matches over scored items, a confusion matrix per dimension, and a label: <30 TOO_FEW_TO_JUDGE, <50 PRELIMINARY, <100 USEFUL_DIAGNOSTIC, else STRONGER_DIVERSITY_DEPENDENT. No blended score. No confidence is output, so no calibration, Brier or ECE claims are made.
- **Isolation.** Each scenario runs on a fresh in-memory state that is discarded. Items starting `read `, `patterns `, `selfeval ` or `quit` are refused. Tests check agent-memory.json and reader transcripts are unchanged.
- **Contamination.** Items whose text equals a pattern-derivation example are retired and listed. Paraphrase and derived-fact lineage is NOT detected yet.
- **Suite.** `tests/selfeval/smoke-en-v1.json` is a plumbing smoke suite. It is not release-relevant and not Thai.
- **Not yet built.** Frozen release baseline, NOT_DIRECTLY_COMPARABLE / REVIEW_REQUIRED comparison, A22 window-rate view and manifest coverage of selfeval files (A23.2); Thai suite (A23.3, needs human Thai annotation by the owner). The A22 manifest is change detection, not authenticated approval.

### A23.1: suite format hardening and lineage

Schema 2 (harness selfeval-1). A suite must now declare `tier` (`supported` or `challenge`), `lang`, and `provenance` (`method`: synthetic, owner-authored or owner-real; `author`). `owner-real` data is refused unless `opt_in` and `privacy_check` are both true. Suites missing these are refused, so `smoke-en-v1.json` stays immutable and `smoke-en-v2.json` replaces it.

- Challenge probes are reported in their own section and never mixed into the supported section.
- Items may carry `lineage` (`seen_in_dev`, `unclear`, `derived_from`). Any of these retires the item from scoring, with the reason printed; unclear lineage is excluded conservatively.
- Contamination also catches a reordered copy of a derivation example (same words, any order). That is a cheap hint. Semantic paraphrases are still NOT detected, and `lineage` is an unauthenticated owner claim.
- The report holds ids, counts and matrices only, never input text.

### A23.2: baselines, comparison, operational snapshot

Still report-only. Nothing here changes a reply, pattern, threshold or tripwire.

- `selfeval freeze NOTE... owner` writes the immutable frozen release baseline from the current report (all suites frozen, no problems, same build). A second freeze is refused; replacing it means the owner moves the file away by hand (there is no remove builtin).
- `selfeval accept NOTE... owner` appends to a hash-chained rolling baseline. It is refused until a frozen baseline exists and the ledger holds at least two distinct reports. Each entry records how it compared with the frozen baseline. It never edits the frozen file or earlier entries. Nothing is ever accepted automatically.
- `selfeval compare` always shows the frozen comparison first, then the latest rolling entry, then an overall verdict. The rolling baseline cannot hide a frozen regression.
- Verdicts: NOT_DIRECTLY_COMPARABLE when schema, harness, classifier, suite version/hash, categories or contamination state differ (a changed score is not read as a regression); REVIEW_REQUIRED for a drop on a dimension with a denominator of 30 or more; REVIEW_THIN_DATA for a drop on thinner data; IMPROVED_NOT_ACCEPTED; UNCHANGED. REVIEW_* is a signal for an owner release decision, not an action.
- `selfeval baseline` shows what is stored. A baseline file or report that no longer matches its own hash is reported as CHANGED and not compared.
- `selfeval ops` prints an aggregate, read-only snapshot of A22 tripwire data with its own id. It is not part of the report or its hash. It shows window false positives over window matches and window exposure share, and labels lifetime counters as totals, not rates. The tripwire does not record per-source concentration, so only per-pattern concentration is shown.
- **Limits.** Baselines are owner-ATTESTED, not authenticated: the `owner` word is a convention and hashes are poly62 change detection (no SHA-256/HMAC until C20). Baseline files are deliberately NOT in the A22 manifest: that manifest gates runtime-affecting files, and these files affect no reply. Their own embedded hashes detect edits instead.

### A23.3: Thai dataset format (labels pending, owner-owned)

`selfeval thai-check FILE` validates a Thai dataset (`kind thai-dataset`, `lang th`). It only checks structure and counts. It creates no labels, translates nothing and scores nothing. A Thai dataset is not a runnable suite yet: `selfeval run` refuses it until a later owner step freezes labeled data.

- **Template:** `tests/selfeval/thai-core-v1.pending.json` has no items and no labels. Its acceptance criteria per category are placeholders for the owner to write.
- **Authored only.** Items must have `origin: authored` (Thai written by the owner). `translated` items are rejected, and so is synthetic provenance. Real conversation examples need `opt_in` and `privacy_check`.
- **Annotation.** Each item holds annotations (annotator, role primary or independent, label with epistemic and action from the fixed sets). `agreed` needs two distinct annotators with identical labels. Critical items, and any item an annotator labels ambiguous, always need an adjudicator who is not one of the annotators.
- **Separation.** The release-relevant core (`tier supported`) and future probes (`tier challenge`) are separate datasets. Thin-data labels (<30 resolved per category) apply as for the English suites. The verdict stays PENDING_OWNER_LABELING until every item is resolved.
- **Open limit:** `json_str` differs for non-ASCII text between the interpreter and compiled backends (language gap). Thai suite hashes must be proven identical across routes before freezing; the tests use ASCII placeholders only.

### A24.0a: claim view contract (spec only)

`agent/CLAIM_VIEW_CONTRACT.md` freezes the contract for a future read-only claim/evidence view. There is NO implementation: no Holy code, no reply route, no Oracle or persistence change. A Python reference model and 24 shared fixtures (`tests/claimview/`) with contract tests (`tests/test_claim_view_contract.py`) pin the status truth table, provenance wording, fail-closed privacy rules, ordering, caps and depth. Memory keeps no original wording or time, so a view can only describe what is stored now. The model passing is not proof of any later implementation. A24.0b is not approved until re-review.

### v0.16 notes (kept; see v0.17 notes below)

A22 Knowledge Integrity is complete: change-detection manifest (A22.0),
predicate/type registry (A22.1), tripwires and quarantine (A22.2), reviewer
budgets (now mandatory), suspension and canaries (A22.3), leakage guard
(A22.4). Everything remains EXPERIMENTAL, opt-in and revocable; no fact is
ever auto-promoted and the reader and core are unchanged since v0.15. The
`owner`, `verified` and reviewer-id markers, family names and hashes (62-bit
polynomial, no SHA-256/HMAC until C20) are unauthenticated conventions.

### v0.17 notes

A23 Self-Evaluation is complete except the Thai labels (A23.0-A23.3 above). It is report-only and open loop: no tuning, auto-disable or reply change, and a regression yields only a signal (REVIEW_REQUIRED / REVIEW_THIN_DATA) for an owner release decision. The reader and core are unchanged since v0.15; the banner, selfeval build id and test pins moved to v0.17. The Thai core suite is PENDING owner labeling: only the format, template and checker exist, no Thai item or label does. No calibration, Brier or ECE claim is made because the agent emits no probabilities. Baselines are owner-attested, not authenticated; hashes are 62-bit polynomial change detection until C20. Language gaps still standing: no SHA-256/HMAC, no clock, no remove builtin (`.tmp` files remain), native `return` inside `try` misses a json_load failure, and `json_str` differs for non-ASCII text across backends.

## Hosted resource benchmark (re-measured at A19, v0.13)

Measured with `tests/bench_agent.py` (repeatable: `--full`; synthesized
facts only). Method, per number: wall = `perf_counter` around the whole
process; cold startup = process wall for an immediate `quit` (loads and
re-saves the seeded store); latency = (session wall - startup) /
commands; peak RSS = the child process's own kernel-reported
`ru_maxrss` (wait4), per-process, not system-wide use. These are
HOSTED numbers (a Linux process running the hs runtime); future in-OS
(kernel-hosted) numbers are a separate milestone and must not be
conflated with these. Host: Linux 6.1 x86_64, glibc 2.35, Python
3.10.12 for the interp route.

Current numbers (A19; the A15/A16 table below is kept for history).
The A19 reader adds skip classes, separate source measurements,
SOURCE_DIVERSITY_THRESHOLD_MET (renamed at A20 from REVIEW_ELIGIBLE; 3+ sources and 2+ domains, content clusters NOT_ASSESSED) and approval history; per-command core costs are
unchanged within noise, the dialogue keeps full marks in every
category on both backends at every scale (reading 8/8 included).

Route note: since A18.1 the repl imports agent.fetch (tcp builtins),
which the ir-x64 subset route rejects at build time, so the native
backend is now built with the full native route (`hs.py build`,
the route the shipped repl uses) and labeled `native`. The ir-x64
subset rows below remain as historical A15 numbers. Chunking note:
interp 10k read-ingest used 60 commands and rule-derive 25 (the
harness's --sessions/--n-cmds chunking; means are per-command).

| backend | facts | miss | recall | inference | rule-derive | read-ingest | startup | peak RSS |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| interp | 0 | 2.1 ms | - | <0.01 ms | 3.8 ms | 15.2 ms | 0.17 s | 28.0 MiB |
| interp | 1,000 | 5.1 ms | 1.3 ms | 2.0 ms | 3.7 ms | 15.2 ms | 2.23 s | 30.1 MiB |
| interp | 10,000 | 50.1 ms | 1.2 ms | 2.3 ms | 8.8 ms | 12.7 ms | 21.3 s | 60.5 MiB |
| native | 0 | 0.02 ms | <0.01 ms | <0.01 ms | 0.05 ms | 0.15 ms | <0.01 s | 10.0 MiB |
| native | 1,000 | 0.05 ms | 0.02 ms | 0.03 ms | 0.08 ms | 0.16 ms | 0.07 s | 11.6 MiB |
| native | 10,000 | <0.01 ms | <0.01 ms | <0.01 ms | <0.01 ms | <0.01 ms | 10.5 s | 72.1 MiB |

The native 10k per-command latencies are real but vanish next to
the 10.5 s startup, which is store load/save on the full native
route; the 4 GiB RLIMIT_AS probe passes on both backends at 10k
(interp 60.3 MiB, native 64.8 MiB peak).

Historical numbers (A15; A14.1 numbers in parentheses where they
differ). A15 adds the hypothesis recorder (explore mode only) plus
one scored dialogue category (hypothesis 5/5; every earlier
category keeps full marks at every scale on both backends).

| backend | facts | miss | recall | inference | rule-derive | read-ingest | startup (A15) | peak RSS (A15) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| interp | 0 | 2.1 ms (2.1) | - | <0.01 ms | 3.9 ms (3.8) | 11.0 ms | 0.12 s (0.12) | 26.4 MiB (25.7) |
| interp | 1,000 | 5.0 ms (4.8) | 1.4 ms (0.9) | 2.0 ms (2.1) | 3.9 ms (3.9) | 11.5 ms | 2.02 s (2.05) | 28.7 MiB (28.2) |
| interp | 10,000 | see note | see note | see note | 0-0.9 ms (9.2-18.6) | 10.2-13.6 ms | 19.5 s (19.4) | 59.3 MiB (58.7) |
| ir-x64 | 0 | 0.02 ms | <0.01 ms | <0.01 ms | 0.04 ms | 0.12 ms | <0.01 s | 37.1 MiB (33.8) |
| ir-x64 | 1,000 | 0.04 ms (0.03) | <0.01 ms | <0.01 ms | 0.04 ms | 0.12 ms | 0.06 s (0.07) | 37.1 MiB (33.8) |
| ir-x64 | 10,000 | 0.4 ms (0.3) | 0.1 ms (0.1) | 0.1 ms (0.1) | 0.2 ms (<0.01) | 0.04 ms | 0.89 s (0.95) | 210.6 MiB (210.2) |

`read-ingest` re-reads the same 5-sentence text per command: 4
claims extracted on the first pass, one more source appended to each
record on every later pass. It is the only A16 hot path: segmentation
plus whole-segment pattern matching, O(sources) dedup per claim.

4 GiB probe (RLIMIT_AS on the child, 10k facts, dialogue session):
both backends complete - interp at 59.3 MiB peak, native at 210.6
MiB peak. Memory stays far inside a 4 GiB budget.

Honest readings:
- A16 adds one hot path (read-ingest, measured above) and exact-match
  command routes checked after the mode/hypothesis routes; readings
  never touch the fact, rule or hypothesis paths. Every non-read
  latency difference vs A15 is box noise: interp inference at 10k
  read 12.7 ms at A15 and 0-3.1 ms at A16 on nearly identical code;
  interp recall read 5.2 ms then 0 ms at A15, 0 ms at A16; native
  peak RSS reads +9.5% at 0/1k facts with no A16 allocation there
  (native startup variance, documented since A14). The dialogue
  transcript gained the reading category (9 new exchanges, all
  passing); every pre-A16 category is unchanged.
- A15 is performance-neutral by construction: hypotheses record
  only in explore mode (the bench's strict sessions never record),
  and the four new commands are exact-match routes checked after
  the mode commands. Every 10k latency difference vs A14.1 is box
  noise: the 10k samples are 5 commands each, and this box's
  readings swing wildly - interp miss read 27.6 ms then 78.4 ms on
  consecutive runs of the SAME build (documented since A11: 74 ms
  then 0 ms). Recall read 5.2 ms then 0 ms; inference 12.7 ms then
  10.9 ms. No A15 code touches those paths.
- interp rule-derive at 10k read 18.6 ms then 9.2 ms, bracketing
  A14.1's 8.5-10.0 ms: unchanged within noise. The hypothesis
  recorder adds work only when an explore derivation actually makes
  assumptions - the strict derive benchmark records nothing.
- interp 10k cold startup 19.3 s vs A14.1's 19.4 s: flat, as
  expected - hypotheses are session state, never persisted, so the
  load path and store format are untouched again. Native session
  RSS flat at ~210 MiB (~5% of the 4 GiB budget).
- A13's interp load increase (+2.1 s at 10k synth facts) comes from
  three extra prefix checks per value in relation derivation
  (lower-casing 4/6/7-character prefixes for the negation shapes).
  Like A12's, it is a ONE-TIME migration cost - v5 stores re-load
  persisted edges. It could be shaved by sharing one lowered prefix;
  we left it as-is because the code reads more honestly as three
  named checks, and the cost is one-time (Ash's priority:
  inspectable over fast).
- Inference latency is real but small: 2.1 ms/cmd on the interp at
  10k facts (a full is-a walk with O(1) edge checks per node),
  sub-0.1 ms on native. The nearest-node-wins scan never touches
  facts outside the chain.
- A12's interp load increase is a ONE-TIME migration cost, not steady
  state. A pre-v5 store re-derives relation edges on first load, and
  A12 adds a bare is-a edge for every value that matches no other
  shape (all 10k synthesized values do), each with a full lowering:
  16.9 s interp cold startup vs A11's 12.4 s. Once re-saved as v5 the
  edges are persisted and the same 10k store loads in 12.2 s - A11
  speed. Native rose less (0.67 -> 0.88 s) because the compiled
  backend derives fast; its peak RSS grew 124 -> 177 MiB because those
  ~10k extra edges now persist in memory (interp +11 MiB). The cost is
  real and is the price of the kind-of edges; the north-star budget
  (4 GiB) is untouched.
- Miss/recall latency numbers swing run to run on this shared box
  (the same interp 10k build measured 10.2 and 23.0 ms miss on two
  runs); treat any single latency as a band, not a point. Query paths
  were not A12's subject and moved only within that noise.
- The A6/A7 derived structures still carry the query paths: misses and
  `did you mean` checks are word-index lookups (~100x over the pre-index
  scan at 10k facts on interp), recalls use keyset membership - no
  O(number of taught facts) work on the ordinary question paths.
  Association recall (`what do you know about`) is an intentional full
  scan.
- Usage counting is real work at LOAD time, and the interpreter route
  shows it. A10 shipped it at 20.9 s interp cold startup for 10k
  facts; A11 profiled that cost and cut it to 12.4 s (A7 was 2.6 s).
  Profiling showed the price was never the counting itself (~3 s) but
  per-character string passes: lowercasing and splitting ran as two
  full string rebuilds per key and per value (~11 s), and relation
  derivation lowercased every whole value to check four ASCII
  prefixes (~4 s, a cost A9 shipped unmeasured). A11 fuses lowercase
  + split into one pass, lowers only the 4-character prefix unless a
  shape actually matches, hoists per-pair dict lookups out of the
  counting loop, and guards the glue-word compares with a length
  check. Two plausible rewrites measured SLOWER on the interp and
  were reverted rather than kept on faith: index-based while loops
  instead of for-in iteration (+5 s), and a non-ASCII guard in front
  of the Thai pattern checks (its per-character calls cost +4 s more
  than the find()s they skipped). The remaining load cost is the
  interpreter's per-character loop overhead; there is no large win
  left on this route without a runtime-level string operation.
- Native load IMPROVED with the same changes: 0.81 s -> 0.67 s cold
  startup at 10k facts, and peak RSS 140 -> 124 MiB (interp RSS is
  flat, ~47 MiB). Still far inside the 4 GiB story.
- Query paths got no slower: misses and recalls hold their A7 latency
  (the interp 10k miss measured faster than A7's, 25.5 vs 43.5 ms -
  both are word-index lookups; the usage merge is skipped when the
  asked word was never seen).
- The held-out Thai/English dialogue (42 lines: 7 recalls incl. alias
  and Thai, 4 clarifications, 2 honest misses, 1 correction, 2
  pleasantries, 2 open questions, 2 topic chains, 6 inference checks,
  2 usage-fallback checks) scores full marks on both backends at every
  stage. Small sample: a smoke check, not an accuracy study.

`tests/test_agent_bench.py` gates the dialogue check and a tiny-scale
smoke run in CI; the full run is manual.

## What it is not

It is not a language model and does not understand language. It cannot
answer anything it was not taught, cannot generalize beyond the one
inference it has (transitive closure over explicitly taught is-in/is-a
edges, shown in its replies so the reasoning is inspectable, with
open-world negatives), matching is
literal ASCII word matching plus non-ASCII substring matching, web
fetching is plain unauthenticated HTTP with a known unbounded-receive
hang risk (EXPERIMENTAL preview above), and the html-to-text
extraction is crude by design (it drops script/style/title and tags;
it does not understand page structure),
"associations" are shared words between taught values, and its
clarifications are word-overlap guesses. The `what does X mean`
self-knowledge for its own relation words is hard-coded text, not
learned understanding, verb understanding is a fixed lookup table
(not morphology - `needs`/`need`/`needed` are listed, `wanting`
is not inferred), inheritance is nearest-node-wins over explicitly
taught edges (not likelihood or default logic), contradictions are
surfaced, never resolved, the usage learning is co-occurrence counting
over taught facts only - it cannot say how two words are related,
cannot tell synonym from antonym from mere co-mention, and small
memories make weak statistics - and an is-a object keeps the article it was
taught with (teach `a animal` and the chain says `a animal` back -
it echoes, it does not know grammar). Thai substring matches can be
loose in ways a speaker would notice (a short taught key can match an
unrelated longer word that merely contains it). Open questions get
taught facts read back, never an answer to the actual how/why/when,
and the pleasantries are fixed strings - not mood, not comprehension.
No reply should ever be
read as more than pattern matching over taught facts.

## Direction (not a claim)

The long-term goal for this line is a conversational agent that chats
freely in natural language on a 4 GB machine at a tiny fraction of LLM
resource cost. That is the north star, not the current state. Stages
grow from this core — richer patterns, dialogue context, learned
associations — and each stage documents honestly what it can and cannot
do. This work is new and separate; it is not based on the paused `wnn`
research line and shares no code with it.

## Layout

- `core.holy` — the pure agent core (normalizer, rules, memory).
- `store.holy` — hosted JSON save/load (missing or corrupt file loads
  fresh).
- `repl.holy` — terminal chat loop; run `hs run agent/repl.holy` from
  the repo root. Memory persists to `agent-memory.json` on exit.
- `fetch.holy` — EXPERIMENTAL bounded HTTP fetch + html-to-text
  (repl-only; see the A18 preview section).
- `patgen.holy`, `proposals.holy` — EXPERIMENTAL offline pattern
  candidates and their separate proposal store (repl-only).
- `integrity.holy` — A22.0 change-detection manifest (repl-only).
- `reviewers.holy` — A22.3 reviewer budgets, suspension, canaries (repl-only).
- `tripwire.holy` — A22.2 tripwires and quarantine states (repl-only).
- `registry.holy` — A22.1 predicate/type registry (repl-only, audits only).
- `shadow.holy`, `review.holy`, `learned.holy` — EXPERIMENTAL A21
  shadow observation, delegated review gate and fail-closed loader
  (repl-only). The core contains only the pure learned matcher.
- `utf8.holy` — pure-hs UTF-8 decoding (ASCII, Latin-1, Thai) used by
  the fetch path.

## Tests

`tests/test_agent_core.py` runs randomized conversation sessions against
an independent Python oracle of the same spec and requires byte-identical
transcripts on every execution route (reference interpreter, reference
IR, both x64 backends, the self-hosted seed and interpreter, and the gcc
native backend), plus hosted save/load roundtrips.
`tests/test_agent_fetch.py` drives the EXPERIMENTAL read-url path
against the deterministic fixture server
(`tests/fix_fetch_server.py`, 127.0.0.1 only) through both the
interpreter and the native repl and pins the full transcript:
extraction, threat fixtures (hostile markup, fake confirmations,
modal text), every failure mode, dedup, redaction, and the no-flag
policy rejections. `tests/eval_reader.py` holds the frozen extraction
quality corpus at precision 1.000 with zero false extractions.
`tests/test_agent_shadow.py`, `test_agent_review.py` and `test_agent_learned.py` cover shadow/readiness, the approval gate and the loader on interp and native, and the core's non-empty learned-list parity is part of `test_agent_core.py`.
`tests/test_agent_patgen.py` checks the pattern generator against an
independent Python oracle on the interpreter and native routes;
`tests/test_agent_proposals.py` covers the proposal store, the repl
`patterns` commands and the reader-isolation gate.

## claimview-0b slices 1 and 1c: relation index, alias index, sort (branch agent-claimview-0b)

Standalone modules, NOT wired into `agent/core.holy`: `agent/relindex.holy` and `agent/cvsort.holy`. No claim view, parser, REPL route or production use. They implement only the contract's index lifecycle (B9, B15, B17, B18) and the B24 ordering. Core `state["rels"]` and `state["aliases"]` would stay authoritative when wired; this state is a derived copy.

What exists:
- Relation index keyed by the exact canonical subject ("robin" and "a robin" are different keys, nothing article-stripped); original tuples kept, duplicates individually. Alias-record index keyed by canonical alias (several records per key). One generation marker covers both.
- One mutation path: ri_load / ri_load_all / ri_add / ri_remove / ri_drop_subject / ri_alias_add / ri_alias_remove / ri_rebuild, plus plan/commit edits ri_plan_replace / ri_plan_forget / ri_commit (one generation step, stale plans refused). Every mutation refuses on a broken index (fail closed, no repair); only load_all/rebuild replace one.
- ri_check (cheap: missing / generation / count) returns a code, never an epistemic result. ri_read / ri_read_alias return a COPY or a code. ri_audit is an explicit O(n) full comparison for tests and load-time verification, never per view.
- cvsort: stable merge sort with byte-wise order (tuple, alias, str keys).

Limits, stated plainly:
- The write boundary is an AUDITED single-writer invariant, not enforcement. Holy has no private fields or closures; a test greps `agent/*.holy` and checks which functions write state, but any holder of the dict can write it.
- ri_check cannot see same-count corruption (wrong tuple, wrong bucket, altered endpoint, wrong alias record); ri_audit catches all five tested kinds. Empty buckets are inert (no dict delete exists).
- Atomicity covers the index only. A core-plus-index transaction does not exist in Holy; the wiring design is a failed or skipped index update leaves ordinary chat unchanged and makes only the view fail closed.
- remove/drop/replace/forget rebuild the tuple list: O(n) each.
- Language findings (not fixed, language lane): (1) string `<` on ir-x64, ast-x64 and seed-native compares signed bytes (non-ASCII before ASCII; a string after its own prefix), interp compares code points; cvsort avoids whole-string `<`. (2) native dict insertion degrades super-linearly with distinct key count: 1k keys/100k inserts 0.21 s, 25k keys 5.8 s, 100k keys/100k inserts 62.7 s, so index load is 1.3 s at 50k tuples. byte_at/byte_len are not in the IR subset.
- Tests: test_claim_view_0b_relindex.py (lifecycle vs the Oracle store model plus an alias model, 8 random sequences x 60 ops, fail closed, corruption matrix, plan/commit, copy reads, write-boundary gate), test_claim_view_0b_relindex_routes.py (one 4454-line script on all 7 routes), test_claim_view_0b_cvsort.py. No Oracle parity on the 102 fixtures (that needs the view). No production, quality or 4 GB hardware claim; RSS was 40 MB at 50k tuples on the dev box only.

## claimview-0b slice 2a: standalone Holy view (branch agent-claimview-0b)

`agent/claimview.holy` (`cv_view(ri, keyset, builtins, readings, excl, q)`) is a read-only Holy port of the draft Oracle `view()` over `relindex.holy` through its checked-read copy API, with `cvsort.holy` for byte-wise ordering (new "row" kind). It is NOT wired into `core.holy`, has no parser, REPL route or production use, and the W5 core field is not built.

- Parity: `test_claim_view_0b_holy_parity.py` compares the FULL result (layer, status, basis, level, provenances, every evidence path, W charged, candidates, readings rows, readings-stage flag) against the Oracle on all 102 fixtures, their shuffled variants and 260+ generated cases (depth 8/9 and negation chain boundaries, aliases, builtins, Thai names, fail-closed index states, poisoned readings/exclusion inputs): 465 cases identical native, and interp output equals native.
- Routes: `test_claim_view_0b_holy_routes.py` runs a 56-case subset as one embedded script on all 7 routes, byte-identical (the reference interp takes about 100 s for the full set, so the route run is a subset).
- Read-only: `test_claim_view_0b_holy_readonly.py` dumps the whole index state before and after views of every case, identical; no lazy init on an unloaded index.
- Bench (dev box, not 4 GB hardware): 1k tuples 0.14 ms/view, 10k 0.26 ms, 50k 1.21 ms (load at 50k 4.2 s, the native dict super-linear finding), peak RSS 46 MB at 50k.
- Not claimed: ClaimView correctness (parity with an Oracle written from the same contract is not proof), production behavior, resource fit on 4 GB hardware, wiring.

## claimview-0b slice 2: core epoch + repl-only wire (branch agent-claimview-0b-wire, NOT activated)

- core.holy: session-only `cvinst`/`cvgen` and `_cv_inval`, called before every real mutation of the claim-view read-set (rels, aliases, `order` key universe). `cvgen` is an invalidation epoch (never rolls back, may stay advanced after a failure, no-ops never bump), not a change count. Never saved. No other core change; the core corpus is byte-identical on 7 routes.
- agent/cvwire.holy (repl-only): `cv_assign` (fresh process-unique cvinst after new/load), `cv_status` (read-only), `cv_rebuild` (explicit; unavailable first; one candidate; validate; publish only if the live token is unchanged; no fallback to an old snapshot), `cv_query` (token checked before and after the view; ABORT carries no evidence). No REPL command, no respond() integration, no reply metadata, no automatic rebuild. Activation stays behind the C20 gate.
- Tests: test_claim_view_0b_epoch.py, test_claim_view_0b_wire.py (1500 queries through respond()-built states vs the Oracle, fail-closed stages, identity, load, duplicates), test_claim_view_0b_wire_routes.py (7 routes), bench_claim_view_0b_wire.py.
- Not claimed: ClaimView correctness (the Oracle shares the author's reading of the contract), production behavior, resource fit on 4 GB hardware. The writer audit is source-level reading plus grep, not a data-flow proof. Writer interruption is simulated (invalidate-only, partial drop), there is no fault injection inside core writers. Under an address-space cap the runtime dies on out-of-memory (SIGSEGV at 16 MB cap with 3k relations) instead of returning a clean error, so memory exhaustion is not a recoverable ABORT. Mixed random query sets are mostly UNKNOWN (depth and contradiction coverage comes from the 102-fixture parity of slice 2a).

### Classifier c2 baseline note

c2 differs from c1 in exactly one rule: a reply starting with `updated ` (the A25.2 Thai correction and English-correction acknowledgement) is `acknowledge` instead of `other`. The classifier id in reports is now `c2`, so `selfeval compare` treats any report or baseline made under `c1` as NOT_DIRECTLY_COMPARABLE and a frozen baseline needs a fresh freeze by the owner. Real-run effect, same build, same suites: smoke-en-v1/v2 unchanged (no `updated ` replies); thai-dev-ai-v1 (dev only, not tuned) correction/action 3/11 to 7/11 and overall 51/85 to 55/85. Thai answers are still classified `other` (no broader Thai class, per owner choice A).
