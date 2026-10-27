---
name: ai-handoff
description: Hand work between AI coding tools through a shared per-repo handoff file. Use at session start to read what the other AI did, and before ending to append what you changed, verified, and left open.
---

# AI Handoff

Two AI coding tools work on the same repo in turns. The human should not have to
translate between them. This skill is the shared protocol.

## The file

- One handoff file per repo: `docs/AI_HANDOFF.md` at the git repo root.
- If there is no git repo, use `AI_HANDOFF.md` in the working directory.
- The file is append-only history. Never rewrite, reorder, or delete earlier
  sections. Disagreements are new sections, not edits to old ones.
- Never put secrets, tokens, passwords, or private keys in the handoff.

## On session start (reading)

1. Call the `handoff_read` MCP tool when it is available. Otherwise read
   `docs/AI_HANDOFF.md` directly.
2. Summarise for the human in plain words: what the other AI changed, what was
   verified (command and result), what is blocked, and every open question
   addressed to you.
3. Treat unverified claims as unverified. A section that says "tests pass"
   without a command and an observed result does not count as verified.

## Before ending (writing)

1. Call `handoff_append` when available, otherwise append a new dated section
   to `docs/AI_HANDOFF.md` yourself. Use this shape:

   ```markdown
   ## <date> — <your tool name> → next AI

   ### Changed
   - `path/to/file`: what changed and why.

   ### Verified
   - `exact command` → observed result (counts, exit code).

   ### Decisions
   - Decision, and who made it.

   ### Open
   - Item, and who it is blocked on.

   ### Questions for the other AI
   - Question, or "none".
   ```

2. Every verification line must name the command and the observed result.
3. List anything you did not verify as open. Do not mark it done.
4. Never commit, push, merge, release, install, or delete on the other AI's
   behalf. Leave those to the human unless the human asked in this session.

## Asking the other AI

Use `handoff_ask` (or append a Questions section) when you need a decision or
information only the other tool or session has. Tag who it is for. Keep working
on everything that does not depend on the answer. When you've answered one,
call `handoff_answer` with its exact text so it leaves the open list.

## The automatic hook

A PreToolUse hook (`hooks/handoff-hook.py`) runs throttled. It creates the
handoff file from a template when a git repo has none and prints open
questions. The auto-status block (branch and dirty-file count) refreshes on
each append.
It never edits the human/AI history sections and never commits anything.
