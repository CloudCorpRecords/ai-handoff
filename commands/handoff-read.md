---
description: Read the shared AI handoff and say what the other AI did
argument-hint: "[repo-path]"
---

Read the AI handoff for this repo. Use the `handoff_read` MCP tool when it is
available; otherwise read `docs/AI_HANDOFF.md` at the git root (or
`AI_HANDOFF.md` in the working directory if there is no git repo).

If $ARGUMENTS names a repo path, use that repo.

Then tell me, in plain words:

1. What the other AI changed since my last session.
2. What was actually verified — command and observed result only.
3. What is still open, and who each item is blocked on.
4. Every open question addressed to you.

Flag any claim that has no evidence attached. Do not start changing code yet.
