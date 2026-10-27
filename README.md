# AI Handoff

A Muse plugin that lets two AI coding tools hand work to each other through
one shared file per repo, so the human does not have to translate between them.

## How it works

- The shared file is `docs/AI_HANDOFF.md` at the git repo root. Append-only.
- Any MCP-capable agent can use the bundled MCP server's tools:
  `handoff_read`, `handoff_append`, `handoff_ask`, `handoff_status`.
- In Muse, the `ai-handoff` skill teaches the protocol, and three commands
  wrap it: `handoff-read`, `handoff-write`, `handoff-ask`.
- A throttled PreToolUse hook creates the file when a git repo has none,
  refreshes an auto-status block (branch, uncommitted count), and prints the
  last section plus open questions. It never edits history and never commits.

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
