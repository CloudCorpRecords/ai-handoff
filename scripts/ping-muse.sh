#!/bin/sh
# Wake Muse Code once, headless, to answer open handoff questions in a repo.
# Usage:
#   scripts/ping-muse.sh [repo] [question...]
# Run from inside a repo with no args to just wake Muse for what's already open.
# With a question, it is appended for Muse Code first (via handoff_core, same
# rules as the MCP tools), then Muse is woken to answer it.
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
CORE_DIR="$SCRIPT_DIR/../mcp"

command -v muse >/dev/null 2>&1 || { echo "ping-muse: 'muse' not on PATH" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "ping-muse: 'python3' not on PATH" >&2; exit 1; }

REPO="$PWD"
if [ $# -gt 0 ] && [ -d "$1" ]; then REPO="$1"; shift; fi
QUESTION="$*"

REPO=$(CORE_DIR="$CORE_DIR" REPO="$REPO" QUESTION="$QUESTION" python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["CORE_DIR"])
import handoff_core as hc
repo = hc.find_repo(os.environ["REPO"])
q = os.environ.get("QUESTION", "").strip()
if q:
    hc.append_question(repo, "ping-muse (on behalf of Claude)", "Muse Code", q)
print(repo)
PY
)

echo "ping-muse: repo=$REPO"
CORE_DIR="$CORE_DIR" REPO="$REPO" python3 - <<'PY'
import os, sys
sys.path.insert(0, os.environ["CORE_DIR"])
import handoff_core as hc
st = hc.status(hc.find_repo(os.environ["REPO"]))
print(f"open questions before: {len(st['open_questions'])}")
for q in st["open_questions"]:
    print(f"  - {q}")
PY

PROMPT="You are Muse Code, woken by ping-muse.sh to use the ai-handoff plugin with the other AI. Repo: $REPO. Use the ai-handoff MCP tools (handoff_status, handoff_read) for that repo when available, otherwise read and append to docs/AI_HANDOFF.md directly (append-only, never edit earlier sections). Answer every open question addressed to Muse Code, to 'the other AI', or untagged: use handoff_answer with the question's exact text and a real answer when available. If a question asks you to test or verify something in the repo, do it: read the code and run the tests/commands it names in the repo, then report the exact command and observed result in your handoff answer/append. Leave questions addressed to Claude alone. If no question is for you, say NO_QUESTIONS_FOR_MUSE and write nothing. Do not edit any file except the handoff file (via the tools). Do not commit, push, or install anything."

muse exec --workspace "$REPO" "$PROMPT"

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
