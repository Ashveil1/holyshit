# Phase 4 - Stage 2 corpus session log (protocol corpus-v1)

Runner: Instinct task agent, 2026-11-27 (UTC). Account: Ash's free Gemini
account (gemini.google.com), free tier ("Upgrade" button shown in UI
throughout; never upgraded, never switched model or account). Displayed
model label recorded verbatim per session as shown in the UI: "Auto"
(self-reported by the service, unverified). One fresh chat per batch
(new conversation via "New chat" / gemini.google.com/app, nothing
carried over), one session at a time. Prompts pasted verbatim from the
bundle (SHA256SUMS verified before the run); nothing added or changed,
no follow-up messages in any chat. Raw responses copied unedited via
each response's Copy button into the files below. No edits, fixes, or
interpretation applied.

| stage | category | session file | model label (displayed) | date (UTC) | chat URL | fresh chat |
|---|---|---|---|---|---|---|
| corpus | recall | tc-recall-s1.txt | Auto | 2026-11-27 | https://gemini.google.com/app/8ca8cfc2715ecefb?pli=1 | yes |
| corpus | unknown | tc-unknown-s1.txt | Auto | 2026-11-27 | https://gemini.google.com/app/1bcdcb7ae4b5acd4 | yes |
| corpus | contradiction | tc-contradiction-s1.txt | Auto | 2026-11-27 | https://gemini.google.com/app/16da322c3fb1285a | yes |
| corpus | ambiguity | tc-ambiguity-s1.txt | Auto | 2026-11-27 | https://gemini.google.com/app/12d06dc6bdadeece | yes |
| corpus | teach | tc-teach-s1.txt | Auto | 2026-11-27 | https://gemini.google.com/app/d5d89babb674cc6b | yes |
| corpus | forget | tc-forget-s1.txt | Auto | 2026-11-27 | https://gemini.google.com/app/016efdeb6d274d4c | yes |
| corpus | correction | tc-correction-s1.txt | Auto | 2026-11-27 | https://gemini.google.com/app/ea1f3e5e55caad92 | yes |

## Notes

- No quota wall was hit; no batch spanned chats (all sessions are -s1).
- No response was cut off; each response covers its batch's full marked
  pair set (recall/unknown/contradiction/ambiguity: 10 pairs; teach: 15;
  forget: 26; correction: 20). Completion was confirmed per session by
  the generation stop control being gone and the response text stable
  across two reads ~15s apart before copying.
- All 7 raw files have distinct sha256 hashes (see below); sizes 748 to
  2124 bytes, plausible for their pair counts and JSON verbosity.
- Batch run order: recall, unknown, contradiction, ambiguity, teach,
  forget, correction (the category order in the runner brief).
- Pair-validity rule (pin record section 2, change 3): runner confirms
  each response was captured raw as displayed; whether each satisfies
  the exactly-marked-pairs rule is left to the reviewers - no
  interpretation applied here.

## SHA256 of raw files

961886154c1594c6751f5e1b7d1254b90219c65df25ff64bf142c46be533003f  tc-ambiguity-s1.txt
44cb9f62193a571c2095566f20e10294e7d334fb2eeee42ee18e966a3e43a912  tc-contradiction-s1.txt
b201d770eb32c3f9d9f8fc27d7ffab8314e9d4b5124610e902eac503d69f22dd  tc-correction-s1.txt
2116b7f12487f19e9b3c8617e6aa027d9542f2dc4e6b6b323640d6d149d0e211  tc-forget-s1.txt
ff2e1075114420b1beb9a433bca1452020e868bbf1fc526935e577ca09c6e449  tc-recall-s1.txt
aebccbd2c93b9850f4b93990acfcc9f2f2277ebe5b6c1df51ab33c957fb86e22  tc-teach-s1.txt
aa0abbbf221a456f3d8d0c262f9bdf5088b13722d340adcd04a35ffca8c9896e  tc-unknown-s1.txt
