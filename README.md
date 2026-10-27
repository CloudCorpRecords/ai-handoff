# AI Handoff

A Muse plugin that lets two AI coding tools hand work to each other through
one shared file per repo, so the human does not have to translate between them.

## How it works

- The shared file is `docs/AI_HANDOFF.md` at the git repo root. Append-only.
- Any MCP-capable agent can use the bundled MCP server's tools:
  `handoff_read`, `handoff_append`, `handoff_ask`, `handoff_answer`, `handoff_status`.
- In Muse, the `ai-handoff` skill teaches the protocol, and three commands
  wrap it: `handoff-read`, `handoff-write`, `handoff-ask`.
- A throttled PreToolUse hook creates the file when a git repo has none and
  prints the last section plus open questions. It never edits history and
  never commits. The auto-status block (branch, uncommitted count) refreshes
  when something is appended, so the file doesn't show as changed on every run.
- Start the agent inside the repo (or pass `repo` / set `AI_HANDOFF_REPO`):
  from a folder that isn't a git repo the hook does nothing and the MCP
  tools refuse with an error, rather than creating a stray handoff file.

## Ping the other AI (no human relay)

The handoff file is passive: an AI only sees new questions when a session runs.
The scripts in `scripts/` wake the other AI once, headless, to answer whatever
is open for it, then print the open-question count before and after:

```sh
# from inside a repo: wake Claude to answer open questions
scripts/ping-claude.sh
# wake Claude and leave it a new question first
scripts/ping-claude.sh /path/to/repo "Claude: question text"
# same in the other direction (Claude wakes Muse)
scripts/ping-muse.sh /path/to/repo "Muse Code: question text"
```

`ping-claude.sh` needs the `ai-handoff` MCP server registered in Claude Code
(one time, user scope):

```sh
claude mcp add -s user ai-handoff -- python3 /path/to/ai-handoff/mcp/server.py
```

Each script only lets the woken AI use the handoff tools (or, for Muse, the
handoff file), tells it to leave the other AI's questions alone, and forbids
commits, pushes, and installs.

## Rules baked in

- Verified means a command and an observed result. Anything else is open.
- Disagreements are new sections, never edits to old ones.
- No secrets in the handoff. Appends that look like they contain one are refused.
- No tool in this plugin commits, pushes, merges, or releases.

## Manual check (before installing)

From a repo root, the MCP server can be exercised with any MCP client pointed
at `python3 mcp/server.py`, with `AI_HANDOFF_REPO` set to the repo if the
client's working directory is elsewhere.

## Get it from GitHub

```sh
gh repo clone CloudCorpRecords/ai-handoff
# or
git clone https://github.com/CloudCorpRecords/ai-handoff.git
```

Then install or update the Muse plugin from that checkout:

```sh
muse plugins install /path/to/ai-handoff
# after pulling changes later:
muse plugins update ai-handoff
```

Improvements welcome: keep the handoff format append-only, keep the server
stdlib-only, and re-run before submitting:

```sh
muse skills validate skills/ai-handoff --json
muse plugins validate . --json
```
