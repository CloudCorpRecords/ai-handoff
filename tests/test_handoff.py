"""ai-handoff tests (stdlib only), each in a throwaway git repo:  python3 tests/test_handoff.py"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))
import handoff_core as hc  # noqa: E402


def git_repo():
    d = Path(tempfile.mkdtemp(prefix="handoff-test-"))
    subprocess.run(["git", "init", "-q", str(d)], check=True)
    return d


def serve(msgs, env=None, cwd=None):
    p = subprocess.run([sys.executable, str(ROOT / "mcp" / "server.py")], input="\n".join(json.dumps(m) for m in msgs) + "\n",
                       capture_output=True, text=True, timeout=30, env={**os.environ, **(env or {})}, cwd=cwd)
    return [json.loads(line) for line in p.stdout.splitlines() if line.strip()]


def call(i, name, args):
    return {"jsonrpc": "2.0", "id": i, "method": "tools/call", "params": {"name": name, "arguments": args}}


class Handoff(unittest.TestCase):
    def setUp(self):
        self.repo = git_repo()
        os.environ.pop("AI_HANDOFF_REPO", None)

    def test_server_tools(self):
        out = serve([{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                     {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                     call(3, "handoff_append", {"repo": str(self.repo), "author": "A", "verified": ["cmd -> ok"]}),
                     call(4, "nope", {"repo": str(self.repo)})])
        names = {t["name"] for t in out[1]["result"]["tools"]}
        self.assertEqual(names, {"handoff_read", "handoff_append", "handoff_ask", "handoff_answer", "handoff_status"})
        self.assertFalse(out[2]["result"].get("isError"))
        self.assertTrue(out[3]["result"].get("isError"))

    def test_asked_questions_are_open_until_answered(self):
        hc.append_section(self.repo, "A", questions=["Q1 in a section?"])
        hc.append_question(self.repo, "A", "B", "Q2 via ask?")
        self.assertEqual(hc.status(self.repo)["open_questions"], ["Q1 in a section?", "Q2 via ask?"])
        hc.answer_question(self.repo, "B", "Q2 via ask?", "yes")
        self.assertEqual(hc.status(self.repo)["open_questions"], ["Q1 in a section?"])

    def test_repo_argument_beats_env(self):
        other = git_repo()
        os.environ["AI_HANDOFF_REPO"] = str(other)
        try:
            self.assertEqual(hc.find_repo(str(self.repo)).resolve(), self.repo.resolve())
            self.assertEqual(hc.find_repo(None).resolve(), other.resolve())
        finally:
            os.environ.pop("AI_HANDOFF_REPO")

    def test_held_lock_refuses_and_is_kept(self):
        path = hc.ensure(self.repo)
        before = path.read_text()
        lock = path.with_suffix(".lock")
        lock.write_text("someone else")
        t = time.time()
        with self.assertRaises(hc.HandoffError):
            hc.append_question(self.repo, "A", "B", "while locked")
        self.assertGreaterEqual(time.time() - t, 9)
        self.assertTrue(lock.exists(), "the other writer's lock was removed")
        self.assertEqual(path.read_text(), before, "it wrote without the lock")

    def test_secrets_refused(self):
        with self.assertRaises(hc.HandoffError):
            hc.append_section(self.repo, "A", changed=["api_key = abcdef123456"])

    def test_paths_are_repo_relative(self):
        self.assertEqual(hc.append_section(self.repo, "A")["path"], "docs/AI_HANDOFF.md")
        st = hc.status(self.repo)
        self.assertEqual(st["path"], "docs/AI_HANDOFF.md")
        self.assertNotIn(str(Path.home()), json.dumps(st))

    def test_hook_reads_without_rewriting(self):
        hc.append_section(self.repo, "A", questions=["Q?"])
        path = hc.handoff_path(self.repo)
        before = path.read_text()
        env = {**os.environ, "TMPDIR": tempfile.mkdtemp()}
        for f in Path("/tmp").glob("ai-handoff-*"):
            try:
                f.unlink()
            except OSError:
                pass
        p = subprocess.run([sys.executable, str(ROOT / "hooks" / "handoff-hook.py")], input="{}", capture_output=True,
                           text=True, cwd=self.repo, env=env, timeout=20)
        self.assertEqual(p.returncode, 0)
        self.assertIn("open question: Q?", p.stdout)
        self.assertEqual(path.read_text(), before, "the hook rewrote the file")

    def test_append_refreshes_auto_status(self):
        hc.append_section(self.repo, "A")
        self.assertIn("_Auto-status: branch", hc.handoff_path(self.repo).read_text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
