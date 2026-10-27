---
description: Append your handoff section for the next AI
argument-hint: "[summary]"
---

Append a handoff section for the next AI. Use the `handoff_append` MCP tool
when it is available; otherwise append to `docs/AI_HANDOFF.md` at the git root
yourself. Never edit or delete earlier sections.

Include:

- **Changed:** every file you changed, what and why. Include $ARGUMENTS if given.
- **Verified:** each check as `exact command` → observed result. No command and
  no observed result means it goes under Open, not Verified.
- **Decisions:** anything settled, and who settled it.
- **Open:** unfinished or unverified items, and who each is blocked on.
- **Questions for the other AI:** or "none".

No secrets. No commits, pushes, or releases unless I asked for them this session.
