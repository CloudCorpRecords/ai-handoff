#!/usr/bin/env python3
"""ai-handoff MCP server (stdio, newline-delimited JSON-RPC). Stdlib only.

Tools: handoff_read, handoff_append, handoff_ask, handoff_answer, handoff_status.
Repo: the `repo` argument, else $AI_HANDOFF_REPO, else the git root of cwd.
File: docs/AI_HANDOFF.md in that repo (created from a template if missing).
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handoff_core as hc

TOOLS = [
    {"name": "handoff_read", "description": "Read the shared AI handoff file for a repo (newest content last).",
     "inputSchema": {"type": "object", "properties": {
         "repo": {"type": "string"}, "tail_chars": {"type": "integer"}}}},
    {"name": "handoff_append", "description": "Append a dated handoff section (Changed/Verified/Decisions/Open/Questions). Never edits history.",
     "inputSchema": {"type": "object", "required": ["author"], "properties": {
         "repo": {"type": "string"}, "author": {"type": "string"},
         "changed": {"type": "array", "items": {"type": "string"}},
         "verified": {"type": "array", "items": {"type": "string"}},
         "decisions": {"type": "array", "items": {"type": "string"}},
         "open": {"type": "array", "items": {"type": "string"}},
         "questions": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "handoff_ask", "description": "Append a question for the other AI to the handoff file.",
     "inputSchema": {"type": "object", "required": ["question"], "properties": {
         "repo": {"type": "string"}, "author": {"type": "string"},
         "target": {"type": "string"}, "question": {"type": "string"}}}},
    {"name": "handoff_answer", "description": "Mark an open question answered (by its exact text), with an optional answer. It drops out of open questions.",
     "inputSchema": {"type": "object", "required": ["question"], "properties": {
         "repo": {"type": "string"}, "author": {"type": "string"},
         "question": {"type": "string"}, "answer": {"type": "string"}}}},
    {"name": "handoff_status", "description": "Branch, uncommitted count, section count, last section, open questions.",
     "inputSchema": {"type": "object", "properties": {"repo": {"type": "string"}}}},
]


def call_tool(name, args):
    repo = hc.find_repo(args.get("repo"))
    if name == "handoff_read":
        return hc.read_handoff(repo, int(args.get("tail_chars") or 12000))
    if name == "handoff_append":
        return hc.append_section(repo, args.get("author") or "unknown AI",
                                 args.get("changed"), args.get("verified"),
                                 args.get("decisions"), args.get("open"),
                                 args.get("questions"))
    if name == "handoff_ask":
        return hc.append_question(repo, args.get("author") or "unknown AI",
                                  args.get("target") or "the other AI",
                                  args.get("question") or "")
    if name == "handoff_answer":
        return hc.answer_question(repo, args.get("author") or "unknown AI",
                                  args.get("question") or "", args.get("answer") or "")
    if name == "handoff_status":
        return hc.status(repo)
    raise hc.HandoffError(f"Unknown tool: {name}")


def reply(mid, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid, "result": result}) + "\n")
    sys.stdout.flush()


def reply_error(mid, message):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": mid,
                                 "error": {"code": -32603, "message": message}}) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        method, mid = msg.get("method"), msg.get("id")
        if method == "initialize":
            reply(mid, {"protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "ai-handoff", "version": "0.1.0"}})
        elif method == "ping":
            reply(mid, {})
        elif method == "tools/list":
            reply(mid, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params") or {}
            try:
                out = call_tool(params.get("name"), params.get("arguments") or {})
                reply(mid, {"content": [{"type": "text",
                                         "text": json.dumps(out, indent=2)}]})
            except Exception as e:
                reply(mid, {"isError": True,
                            "content": [{"type": "text", "text": str(e)}]})
        elif mid is not None:
            reply_error(mid, f"Unknown method: {method}")


if __name__ == "__main__":
    main()
