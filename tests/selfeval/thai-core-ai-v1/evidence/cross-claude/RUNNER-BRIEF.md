# Phase 4 cross-annotation runner brief - Claude annotates (family B items)

Spec v2.5 variant A: Claude annotates the 35 GPT-authored items. Blind:
prompts contain only scenario turns, the frozen rubric semantics, and
the output schema. No author notes, no expected labels, no family info.
Do not disclose to the annotating chat that these are GPT-authored, and
do not paste Gemini's annotations anywhere.

CHATS NEEDED: 7, one per batch file in prompts/ (xc-recall, xc-unknown,
xc-contradiction, xc-ambiguity, xc-teach, xc-forget, xc-correction).
5 items per batch, 51 marked pairs total. Run in that order.

CLAUDE FREE-TIER QUOTA: the account walls in 5-hour windows. The
batches are small (5 items each) so several should fit in one window,
but on an ACTUAL quota notice: stop immediately, record the displayed
reset information verbatim, and resume only when the window reopens.
Never switch model or account to work around a wall. A batch spanning
chats gets -s2, -s3 files with resume_of; a session never spans batches.

Per chat:
1. FRESH chat on Ash's Claude account, one session at a time.
2. Record BEFORE sending: displayed model label exactly as shown, date,
   chat URL. Never invent a version identifier.
3. Paste the ENTIRE prompt file verbatim. Nothing added, no follow-ups.
4. Copy the ENTIRE raw response verbatim via Copy into
   raw/<batch>-s1.txt. No edits. If the model asks a question or
   refuses, that raw reply IS the response - record it, do not coax.

Return: the 7 raw files + a session log (batch, session file, model
label, date, chat URL, fresh chat yes) + sha256 of each raw file.
