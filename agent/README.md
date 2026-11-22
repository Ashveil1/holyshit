# agent — a small local agent written in pure holyshit

A from-scratch local agent core for the holyshit OS direction. It runs
entirely offline inside the hs runtime: no external model, no
dependencies beyond the language itself. One EXPERIMENTAL exception:
the repl shell can fetch web pages over plain HTTP (`read url`, A18
preview below); the core itself stays network-free.

## What it is today (v0.15)

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

### A22.0: change detection for learned-pattern files (in progress)

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

### A22.1: predicate and argument-type registry (in progress)

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
