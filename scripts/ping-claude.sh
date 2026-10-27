#!/bin/sh
# Wake Claude Code once, headless, to answer open handoff questions in a repo.
# Usage:
#   scripts/ping-claude.sh [repo] [question...]
# Run from inside a repo with no args to just wake Claude for what's already open.
# With a question, it is appended for Claude first (via handoff_core, same
# rules as the MCP tools), then Claude is woken to answer it.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CORE_DIR="$SCRIPT_DIR/../mcp"

command -v claude >/dev/null 2>&1 || { echo "ping-claude: 'claude' not on PATH" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ping-claude: 'python3' not on PATH" >&2; exit 1; }

REPO="$PWD"
if [ $# -gt 0 ] && [ -d "$1" ]; then REPO="$1"; shift; fi
QUESTION="$*"

# Resolve to the git root and, if given, append the question for Claude.
REPO=$(CORE_DIR="$CORE_DIR" REPO="$REPO" QUESTION="$QUESTION" python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["CORE_DIR"])
import handoff_core as hc
repo = hc.find_repo(os.environ["REPO"])
q = os.environ.get("QUESTION", "").strip()
if q:
    hc.append_question(repo, "ping-claude (on behalf of Muse Code)", "Claude", q)
print(repo)
PY
)

echo "ping-claude: repo=$REPO"
CORE_DIR="$CORE_DIR" REPO="$REPO" python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["CORE_DIR"])
import handoff_core as hc
st = hc.status(hc.find_repo(os.environ["REPO"]))
print(f"open questions before: {len(st['open_questions'])}")
for q in st["open_questions"]:
    print(f"  - {q}")
PY

PROMPT="You are Claude Code, woken by ping-claude.sh to use the ai-handoff plugin with the other AI. Repo: $REPO. Use the ai-handoff MCP tools (handoff_status, handoff_read) for that repo. Answer every open question addressed to Claude, to 'the other AI', or untagged: call handoff_answer with the question's exact text and a real answer (use handoff_append only if handoff_answer fails). If a question asks you to test or verify something in the repo, do it: read the code and run the tests/commands it names (read-only Bash plus Read/Grep/Glob in $REPO), then report the exact command and observed result in your handoff answer/append. Bash is allowlisted to test/status commands only (tests/*, check_release.py, git status/diff/log/check-ignore, node --check, sh -n). Leave questions addressed to Muse Code alone. If no question is for you, say NO_QUESTIONS_FOR_CLAUDE and write nothing. Do not edit any file except through the handoff tools. Do not commit, push, or install anything."

cd "$REPO"
claude -p "$PROMPT" --allowedTools "mcp__ai-handoff__handoff_read,mcp__ai-handoff__handoff_status,mcp__ai-handoff__handoff_answer,mcp__ai-handoff__handoff_append,Read,Grep,Glob,Bash(.venv/bin/python tests/*),Bash(.venv/bin/python scripts/check_release.py*),Bash(git status*),Bash(git diff*),Bash(git log*),Bash(git check-ignore*),Bash(node --check *),Bash(sh -n *)"

echo "--- after ---"
CORE_DIR="$CORE_DIR" REPO="$REPO" python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["CORE_DIR"])
import handoff_core as hc
st = hc.status(hc.find_repo(os.environ["REPO"]))
print(f"last section: {st['last_section']}")
print(f"open questions after: {len(st['open_questions'])}")
for q in st["open_questions"]:
    print(f"  - {q}")
PY
