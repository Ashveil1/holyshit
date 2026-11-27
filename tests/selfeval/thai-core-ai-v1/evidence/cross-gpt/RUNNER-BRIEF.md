# Phase 4 cross-annotation runner brief - GPT annotates (family A items)

Spec v2.5 variant A: GPT annotates the 35 Claude-authored items. Blind:
prompts contain only scenario turns, the frozen rubric semantics, and
the output schema. No author notes, no expected labels, no family info.
Do not disclose to the annotating chat that these are Claude-authored,
and do not paste Gemini's annotations anywhere.

CHATS NEEDED: 7, one per batch file in prompts/ (xg-recall, xg-unknown,
xg-contradiction, xg-ambiguity, xg-teach, xg-forget, xg-correction).
5 items per batch, 50 marked pairs total. Run in that order.

Per chat:
1. FRESH chat on Ash's ChatGPT account, one session at a time.
2. Record BEFORE sending: displayed model label exactly as shown, date,
   chat URL. Never invent a version identifier.
3. Paste the ENTIRE prompt file verbatim. Nothing added, no follow-ups.
4. Copy the ENTIRE raw response verbatim via Copy into
   raw/<batch>-s1.txt. No edits. If the model asks a question or
   refuses, that raw reply IS the response - record it, do not coax.
5. Quota: pause on an actual quota notice, record displayed reset info
   verbatim, resume when capacity returns. Never switch model or
   account. A batch spanning chats gets -s2, -s3 files with resume_of.

Return: the 7 raw files + a session log (batch, session file, model
label, date, chat URL, fresh chat yes) + sha256 of each raw file.
