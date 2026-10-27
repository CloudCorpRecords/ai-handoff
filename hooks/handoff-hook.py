#!/usr/bin/env python3
"""handoff-sync PreToolUse hook. Stdlib only. Never blocks: always exits 0.

Throttled to one run per repo per 60s. Creates docs/AI_HANDOFF.md from the
template when a git repo has none, refreshes the auto-status block, and prints
the last section heading plus open questions so the reading AI sees them.
It never edits history sections and never commits anything.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp"))
THROTTLE_SECS = 60


def main():
    cwd = os.getcwd()
    try:
        raw = sys.stdin.read()
        if raw.strip():
            data = json.loads(raw)
            cwd = data.get("cwd") or (data.get("tool_input") or {}).get("cwd") or cwd
    except Exception:
        pass
    try:
        import handoff_core as hc
        repo = hc.find_repo(cwd)
        marker = Path("/tmp") / ("ai-handoff-" +
                                 hashlib.sha256(str(repo).encode()).hexdigest()[:12])
        now = time.time()
        if marker.exists() and now - marker.stat().st_mtime < THROTTLE_SECS:
            return
        marker.write_text(str(now))
        if not (repo / ".git").exists():
            return
        hc.refresh_auto(repo)
        st = hc.status(repo)
        print(f"[ai-handoff] {st['last_section'] or 'no sections yet'} "
              f"({st['uncommitted']} uncommitted, {st['path']})")
        for q in st["open_questions"][-5:]:
            print(f"[ai-handoff] open question: {q}")
    except Exception as e:
        print(f"[ai-handoff] unavailable: {e}")


if __name__ == "__main__":
    main()
    sys.exit(0)
