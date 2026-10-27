"""Shared handoff logic for the ai-handoff plugin. Stdlib only.

One append-only file per repo: docs/AI_HANDOFF.md at the git root.
History sections are never edited. Only the auto-status block between the
ai-handoff:auto markers is refreshed.
"""
import os
import re
import subprocess
import time
from datetime import date
from pathlib import Path

AUTO_START = "<!-- ai-handoff:auto:start -->"
AUTO_END = "<!-- ai-handoff:auto:end -->"

_SECRET_RES = [
    re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(password|passwd|api[_-]?key|secret|token)\s*[:=]\s*\S{6,}"),
]

TEMPLATE = """# AI Handoff

Shared, append-only handoff between AI coding tools working in this repo.
Newest sections go at the bottom. Never rewrite earlier sections.
No secrets in this file.

{auto_start}
_Auto-status has not run yet._
{auto_end}

## How to use

- Reader: summarise Changed / Verified / Open / Questions from the last section.
- Writer: append a dated section with Changed, Verified (command -> observed
  result), Decisions, Open, and Questions for the other AI.
- Claims without a command and an observed result are unverified.

"""


class HandoffError(Exception):
    pass


def check_no_secrets(text):
    for rx in _SECRET_RES:
        if rx.search(text or ""):
            raise HandoffError("Refusing to write: the text looks like it contains a secret.")


def find_repo(start=None):
    """The repo: the explicit argument, else $AI_HANDOFF_REPO, else cwd (each resolved to its git root).

    Refuses outside a git repo instead of quietly creating a stray handoff
    file in whatever folder the session happened to start in.
    """
    env = os.environ.get("AI_HANDOFF_REPO")
    base = Path(start or env or os.getcwd()).expanduser()
    try:
        r = subprocess.run(["git", "-C", str(base), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return Path(r.stdout.strip())
    except Exception:
        pass
    raise HandoffError(
        f"Not in a git repo: {base} - start inside a repo, or pass repo=<path> "
        f"(or set AI_HANDOFF_REPO) so the handoff lands in that repo's docs/AI_HANDOFF.md.")


def handoff_path(repo):
    return Path(repo) / "docs" / "AI_HANDOFF.md"


def _git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args],
                           capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def auto_block(repo):
    branch = _git(repo, "branch", "--show-current") or "(no branch)"
    dirty = [l for l in _git(repo, "status", "--porcelain").splitlines() if l.strip()]
    return (f"{AUTO_START}\n"
            f"_Auto-status: branch `{branch}` - {len(dirty)} uncommitted change(s) - "
            f"updated {time.strftime('%Y-%m-%d %H:%M')}._\n{AUTO_END}")


def ensure(repo):
    path = handoff_path(repo)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(TEMPLATE.format(auto_start=AUTO_START, auto_end=AUTO_END),
                        encoding="utf-8")
    return path


def refresh_auto(repo):
    path = ensure(repo)
    text = path.read_text(encoding="utf-8")
    block = auto_block(repo)
    if AUTO_START in text and AUTO_END in text:
        text = re.sub(re.escape(AUTO_START) + r".*?" + re.escape(AUTO_END),
                      block, text, count=1, flags=re.S)
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def _locked_append(path, text):
    """Append under an exclusive lock file. If another writer holds it past the deadline, refuse rather than
    write over it, and never remove a lock this call doesn't own."""
    lock = path.with_suffix(".lock")
    deadline = time.time() + 10
    fd = None
    while fd is None:
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.time() >= deadline:
                raise HandoffError(f"Another writer holds {lock.name}; nothing was written. Try again.")
            time.sleep(0.1)
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
    finally:
        os.close(fd)
        try:
            lock.unlink()
        except OSError:
            pass


def _rel(repo, path):
    try:
        return str(Path(path).relative_to(repo))
    except ValueError:
        return str(path)


def _bullets(items, empty="- none"):
    items = [str(i).strip() for i in (items or []) if str(i).strip()]
    return "\n".join(f"- {i}" for i in items) if items else empty


def append_section(repo, author, changed=None, verified=None, decisions=None,
                   open_items=None, questions=None):
    body = "\n".join([*(changed or []), *(verified or []), *(decisions or []),
                      *(open_items or []), *(questions or [])])
    check_no_secrets(body)
    path = ensure(repo)
    section = (f"\n## {date.today().isoformat()} - {author} -> next AI\n\n"
               f"### Changed\n{_bullets(changed)}\n\n"
               f"### Verified\n{_bullets(verified)}\n\n"
               f"### Decisions\n{_bullets(decisions)}\n\n"
               f"### Open\n{_bullets(open_items)}\n\n"
               f"### Questions for the other AI\n{_bullets(questions)}\n")
    _locked_append(path, section)
    refresh_auto(repo)
    return {"path": _rel(repo, path), "section": section.strip().splitlines()[0]}


def append_question(repo, author, target, question):
    check_no_secrets(question)
    path = ensure(repo)
    section = (f"\n## {date.today().isoformat()} - {author} asks {target}\n\n"
               f"- {str(question).strip()}\n")
    _locked_append(path, section)
    refresh_auto(repo)
    return {"path": _rel(repo, path), "question": str(question).strip()}


def answer_question(repo, author, question, answer=""):
    """Mark an open question answered (it drops out of open_questions); history is appended, never edited."""
    question = str(question).strip()
    check_no_secrets(question + "\n" + str(answer or ""))
    if not question:
        raise HandoffError("Say which question this answers.")
    path = ensure(repo)
    section = (f"\n## {date.today().isoformat()} - {author} answers\n\n"
               f"- Answered: {question}\n" + (f"- {str(answer).strip()}\n" if str(answer or "").strip() else ""))
    _locked_append(path, section)
    refresh_auto(repo)
    return {"path": _rel(repo, path), "answered": question}


def read_handoff(repo, tail_chars=12000):
    path = ensure(repo)
    text = path.read_text(encoding="utf-8")
    tail = text[-tail_chars:] if len(text) > tail_chars else text
    return {"path": _rel(repo, path), "chars": len(text), "truncated": len(text) > tail_chars,
            "content": tail}


def open_questions(text):
    """Questions still waiting: '### Questions' bullets and handoff_ask sections, minus any marked 'Answered:'."""
    asked, answered = [], set()
    in_q = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_q = " asks " in line
        elif line.startswith("### "):
            in_q = line.startswith("### Questions")
        elif line.startswith("- Answered:"):
            answered.add(line[len("- Answered:"):].strip())
        elif in_q and line.startswith("- ") and line.strip() != "- none":
            asked.append(line[2:].strip())
    return [q for q in asked if q not in answered]


def status(repo):
    path = ensure(repo)
    text = path.read_text(encoding="utf-8")
    headings = re.findall(r"^## .+$", text, flags=re.M)
    dirty = [l for l in _git(repo, "status", "--porcelain").splitlines() if l.strip()]
    return {"path": _rel(repo, path), "repo": Path(repo).name,
            "branch": _git(repo, "branch", "--show-current"),
            "uncommitted": len(dirty), "sections": len(headings),
            "last_section": headings[-1] if headings else None,
            "open_questions": open_questions(text)[-10:]}
