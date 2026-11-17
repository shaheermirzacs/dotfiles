"""Read-only, PID-bound plan sources. No cwd or newest-session fallback."""

import datetime
import json
import os
from pathlib import Path
import re
import shlex
import sqlite3
import subprocess
from tempfile import TemporaryDirectory


_UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", re.I)
_JOURNALS = {}


def _process(pid):
    try:
        result = subprocess.check_output(
            ["/bin/ps", "-p", str(int(pid)), "-o", "lstart=,tty=,command="],
            text=True, env={**os.environ, "TZ": "UTC"},
        ).strip().split(None, 6)
    except (ValueError, subprocess.CalledProcessError) as error:
        raise ValueError("The selected agent process is no longer running.") from error
    if len(result) != 7:
        raise ValueError("Cannot identify the selected agent process.")
    start = " ".join(result[:5])
    command = result[6]
    try:
        words = shlex.split(command)
    except ValueError:
        words = command.split()
    agent = next((Path(word).name for word in words[:3]
                  if Path(word).name in ("omp", "claude", "codex")), None)
    if not agent:
        raise ValueError("The selected process is not Codex, OMP, or Claude Code.")
    return {"pid": int(pid), "start": start, "tty": result[5],
            "agent": agent, "command": command}


def _open_paths(pid):
    try:
        result = subprocess.run(
            ["/usr/sbin/lsof", "-n", "-P", "-a", "-p", str(pid), "-Fn"],
            capture_output=True, text=True, check=False, timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ValueError("Cannot inspect the agent's open session files with lsof.") from error
    return {Path(line[1:]) for line in result.stdout.splitlines() if line.startswith("n/")}


def _check_process(source):
    current = _process(source["pid"])
    if any(current[key] != source[key] for key in ("start", "agent", "tty")):
        raise ValueError("The agent process changed; reopen the plan pane.")
    return current


def _records(path, agent):
    """Cache only plan-relevant records; never consume a partial appended line."""
    path = Path(path)
    stat = path.stat()
    identity = (stat.st_dev, stat.st_ino)
    key = (str(path), agent)
    old = _JOURNALS.get(key)
    if old and old.get("stat") == (identity, stat.st_size, stat.st_mtime_ns):
        return old["records"]
    if (not old or old["identity"] != identity or stat.st_size < old["offset"]
            or (stat.st_size == old.get("size") and stat.st_mtime_ns != old.get("mtime"))):
        old = {"identity": identity, "offset": 0, "records": []}
        _JOURNALS[key] = old
    terms = {
        "codex": (b'"session_meta"', b"proposed_plan", b"update_plan", b"plan_update"),
        "omp": (b'"mode_change"',),
        "claude": (b"planContent", b"plan_file_reference", b"ExitPlanMode", b'"Write"', b'"Edit"'),
    }[agent]
    with path.open("rb") as stream:
        stream.seek(old["offset"])
        for line in stream:
            if not line.endswith(b"\n"):
                break
            old["offset"] += len(line)
            if not any(term in line for term in terms):
                continue
            try:
                record = json.loads(line)
            except (ValueError, UnicodeDecodeError):
                continue
            if isinstance(record, dict):
                old["records"].append(record)
    old.update(stat=(identity, stat.st_size, stat.st_mtime_ns),
               size=stat.st_size, mtime=stat.st_mtime_ns)
    return old["records"]


def _meta(path):
    with Path(path).open() as stream:
        try:
            first = json.loads(stream.readline())
        except ValueError as error:
            raise ValueError("Codex has not saved its session header yet.") from error
    if first.get("type") != "session_meta":
        raise ValueError("Codex rollout is missing its session identity.")
    return first["payload"]


def _codex_journal(source, command):
    paths = _open_paths(source["pid"])
    rollouts = {p for p in paths if p.name.startswith("rollout-") and p.suffix == ".jsonl"}
    roots = []
    for path in rollouts:
        try:
            meta = _meta(path)
        except (OSError, ValueError):
            continue
        if meta.get("source") == "cli" and not meta.get("parent_thread_id"):
            roots.append((path, meta))
    if len(roots) == 1:
        return roots[0]
    words = shlex.split(command)
    explicit = {words[index + 1] for index, word in enumerate(words[:-1])
                if word == "resume" and _UUID.fullmatch(words[index + 1])}
    matches = [(p, m) for p, m in roots if m.get("id") in explicit]
    if len(matches) == 1:
        return matches[0]
    if roots:
        raise ValueError("Multiple Codex root sessions belong to this PID; refusing to guess.")
    # A lock is a PID-owned reference, unlike the global session index or cwd.
    ids = {p.stem for p in paths if p.parent.name == "thread-writer-locks" and _UUID.fullmatch(p.stem)}
    ids.update(explicit)
    homes = {p.parent.parent for p in paths if p.parent.name == "thread-writer-locks"}
    homes.add(Path(source["home"]))
    candidates = []
    for home in homes:
        database = home / "state_5.sqlite"
        if not database.is_file():
            continue
        try:
            with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
                for session in ids:
                    row = db.execute("SELECT rollout_path FROM threads WHERE id = ?", (session,)).fetchone()
                    if not row:
                        continue
                    path = Path(row[0])
                    meta = _meta(path)
                    if meta.get("id") == session and meta.get("source") == "cli" and not meta.get("parent_thread_id"):
                        candidates.append((path, meta))
        except (sqlite3.Error, OSError, ValueError):
            continue
    unique = {str(p): (p, m) for p, m in candidates}
    if len(unique) == 1:
        return next(iter(unique.values()))
    raise ValueError("Cannot map this Codex PID to one saved root thread. No cwd/latest-session fallback is used.")


def _claude_journal(source):
    pointer = json.loads(Path(source["pointer"]).read_text())
    if pointer.get("pid") != source["pid"]:
        raise ValueError("Claude session pointer belongs to a different PID.")
    if " ".join(str(pointer.get("procStart", "")).split()) != source["start"]:
        raise ValueError("Claude session pointer has a stale process identity.")
    session = pointer.get("sessionId", "")
    if not isinstance(session, str) or not _UUID.fullmatch(session):
        raise ValueError("Claude has not published a valid session ID yet.")
    if source.get("session") != session or not Path(source.get("journal", "/nonexistent")).is_file():
        matches = list((Path(source["home"]) / "projects").glob(f"*/{session}.jsonl"))
        if len(matches) != 1:
            raise ValueError("Claude's exact session journal is unavailable or ambiguous; waiting for it to be saved.")
        source.update(session=session, journal=str(matches[0]))
    return Path(source["journal"]), pointer.get("cwd", "")


def discover(pid: int) -> dict:
    source = _process(pid)
    agent = source["agent"]
    source["home"] = str(Path.home() / {"omp": ".omp/agent", "claude": ".claude", "codex": ".codex"}[agent])
    if agent == "omp":
        tty = source["tty"]
        if tty == "??" or "/" in tty:
            raise ValueError("OMP is not attached to a terminal with a session pointer.")
        source["pointer"] = str(Path(source["home"]) / "terminal-sessions" / tty)
        _omp_session(source)
    elif agent == "claude":
        source["pointer"] = str(Path(source["home"]) / "sessions" / f"{pid}.json")
        _claude_journal(source)
    else:
        path, meta = _codex_journal(source, source["command"])
        source.update(journal=str(path), session=meta["id"])
    return source


def _omp_session(source):
    pointer = Path(source["pointer"])
    lines = pointer.read_text().splitlines()
    if len(lines) < 2 or not Path(lines[1]).is_absolute():
        raise ValueError("OMP has not published a valid terminal session pointer yet.")
    # Resuming a session can leave its pointer older than the current process.
    if source.get("owned_journal") != lines[1]:
        if Path(lines[1]) not in _open_paths(source["pid"]):
            raise ValueError("The OMP terminal pointer does not belong to this live agent.")
        source["owned_journal"] = lines[1]
    return Path(lines[1]), Path(lines[0])


def _omp_plan(journal, cwd):
    local = journal.with_suffix("") / "local"
    candidates = {p for p in local.glob("*") if p.name.lower().endswith("plan.md")}
    for record in _records(journal, "omp"):
        if record.get("type") != "mode_change":
            continue
        value = record.get("data", {}).get("planFilePath")
        if isinstance(value, str) and value:
            candidates.add(local / value.removeprefix("local://") if value.startswith("local://") else cwd / value)
    saved = [(p.stat().st_mtime_ns, str(p), p) for p in candidates if p.is_file()]
    if not saved:
        raise ValueError("No saved plan in this OMP session yet. Waiting for a plan…")
    path = max(saved)[2]
    return f"OMP · {path.name}", path.read_text()


def _timestamp(record):
    try:
        return datetime.datetime.fromisoformat(record.get("timestamp", "").replace("Z", "+00:00")).timestamp()
    except (ValueError, TypeError):
        return 0


def _codex_plan(journal, session, home):
    full = []
    checklist = None
    for index, record in enumerate(_records(journal, "codex")):
        payload = record.get("payload", {})
        if record.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "assistant":
            for content in payload.get("content", []):
                if content.get("type") != "output_text":
                    continue
                for text in re.findall(r"\A\s*<proposed_plan>(.*?)</proposed_plan>\s*\Z", content.get("text", ""), re.S):
                    if text.strip():
                        full.append((_timestamp(record), index, "Codex · proposed plan", text.strip()))
        call = record.get("type") == "response_item" and payload.get("type") == "function_call" and payload.get("name") in ("update_plan", "functions.update_plan")
        event = record.get("type") == "event_msg" and payload.get("type") == "plan_update"
        if call or event:
            try:
                args = payload if event else payload.get("arguments", {})
                args = json.loads(args) if isinstance(args, str) else args
                steps = args.get("plan", [])
                if not steps or not all(isinstance(s.get("step"), str) and s.get("status") in ("pending", "in_progress", "completed") for s in steps):
                    continue
                lines = ["# Progress checklist (update_plan)", ""]
                if args.get("explanation"):
                    lines.extend([str(args["explanation"]), ""])
                lines.extend(f"- [{'x' if s['status'] == 'completed' else ' '}] {s['step']}" + (" **(in progress)**" if s["status"] == "in_progress" else "") for s in steps)
                checklist = "\n".join(lines)
            except (ValueError, TypeError, AttributeError):
                continue
    for path in (Path(home) / "plans" / session).glob("*/PLAN.md"):
        if path.is_file():
            full.append((path.stat().st_mtime, -1, "Codex · saved plan", path.read_text()))
    if full:
        _, _, title, markdown = max(full)
        return title, markdown
    if checklist:
        return "Codex · progress checklist (not Plan Mode)", checklist
    raise ValueError("No proposed_plan, saved plan, or update_plan checklist in this Codex thread yet.")


def _claude_plan(journal, session, home, cwd):
    path = None
    markdown = None
    plans = (Path(home) / "plans").resolve()
    for record in _records(journal, "claude"):
        if record.get("sessionId") not in (None, session):
            continue
        if isinstance(record.get("planContent"), str) and record["planContent"].strip():
            markdown = record["planContent"]
        attachment = record.get("attachment", {})
        if attachment.get("type") == "plan_file_reference":
            if isinstance(attachment.get("planContent"), str):
                markdown = attachment["planContent"]
            if attachment.get("planFilePath"):
                path = Path(cwd) / attachment["planFilePath"]
        content = record.get("message", {}).get("content", [])
        for block in content if isinstance(content, list) else []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            args = block.get("input", {})
            if not isinstance(args, dict):
                continue
            if block.get("name") == "ExitPlanMode" and isinstance(args.get("plan"), str):
                markdown = args["plan"]
            if block.get("name") not in ("Write", "Edit") or not isinstance(args.get("file_path"), str):
                continue
            candidate = (Path(cwd) / args["file_path"]).resolve()
            if not candidate.is_relative_to(plans):
                continue
            if path != candidate:
                markdown = None
            path = candidate
            if block["name"] == "Write" and isinstance(args.get("content"), str):
                markdown = args["content"]
            elif block["name"] == "Edit" and markdown is not None:
                old, new = args.get("old_string"), args.get("new_string")
                if isinstance(old, str) and old and isinstance(new, str) and (args.get("replace_all") or markdown.count(old) == 1):
                    markdown = markdown.replace(old, new, -1 if args.get("replace_all") else 1)
    if path is not None and path.is_file():
        return f"Claude Code · {path.name}", path.read_text()
    if markdown and markdown.strip():
        return "Claude Code · session plan", markdown
    raise ValueError("No saved plan reference, planContent, or ExitPlanMode plan in this Claude Code session yet.")


def load(source: dict) -> tuple[str, str]:
    """Follow only this live process's session; errors are useful waiting states."""
    process = _check_process(source)
    agent = source["agent"]
    if agent == "omp":
        return _omp_plan(*_omp_session(source))
    if agent == "claude":
        journal, cwd = _claude_journal(source)
        return _claude_plan(journal, source["session"], source["home"], cwd)
    if agent == "codex":
        journal, meta = _codex_journal(source, process["command"])
        source.update(journal=str(journal), session=meta["id"])
        home = next((p.parent for p in journal.parents if p.name == "sessions"), Path(source["home"]))
        return _codex_plan(journal, meta["id"], home)
    raise ValueError("Unknown plan source.")


def self_test() -> None:
    """Synthetic consumer checks only; no live agents or private transcripts."""
    def save(path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record) + "\n" for record in records))

    def unavailable(callback):
        try:
            callback()
        except ValueError:
            return
        raise AssertionError("An unrelated or empty session must not produce a plan")

    with TemporaryDirectory(prefix="rex-plan-source-test-") as directory:
        root = Path(directory)
        omp = root / "omp/session.jsonl"
        save(omp, [{"type": "mode_change", "data": {"planFilePath": "local://custom.md"}}])
        local = omp.with_suffix("") / "local"
        local.mkdir(parents=True)
        (local / "custom.md").write_text("# OMP custom")
        assert _omp_plan(omp, root)[1] == "# OMP custom"
        (local / "new-plan.md").write_text("# OMP updated")
        os.utime(local / "new-plan.md", ns=(2_000_000_000_000_000_000,) * 2)
        assert _omp_plan(omp, root)[1] == "# OMP updated"
        other = root / "omp/other.jsonl"
        save(other, [])
        unavailable(lambda: _omp_plan(other, root))

        codex = root / "codex.jsonl"
        header = {"type": "session_meta", "payload": {"id": "one", "source": "cli"}}
        def proposed(text, timestamp):
            return {"type": "response_item", "timestamp": timestamp, "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": f"<proposed_plan>\n{text}\n</proposed_plan>"}]}}
        save(codex, [header, proposed("# First", "2026-01-01T00:00:00Z")])
        assert _meta(codex)["id"] == "one"
        assert _codex_plan(codex, "one", root)[1] == "# First"
        later = json.dumps(proposed("# Revised", "2026-01-02T00:00:00Z"))
        with codex.open("a") as stream:
            stream.write(later[:30])
        assert _codex_plan(codex, "one", root)[1] == "# First"
        with codex.open("a") as stream:
            stream.write(later[30:] + "\n")
        assert _codex_plan(codex, "one", root)[1] == "# Revised"
        progress = {"type": "response_item", "payload": {"type": "function_call", "name": "update_plan", "arguments": json.dumps({"plan": [{"step": "Ship", "status": "in_progress"}]})}}
        checklist = root / "checklist.jsonl"
        save(checklist, [progress])
        title, text = _codex_plan(checklist, "two", root)
        assert "not Plan Mode" in title and "Ship **(in progress)**" in text
        save(checklist, [{"type": "event_msg", "payload": {"type": "plan_update", "plan": [{"step": "Done", "status": "completed"}]}}])
        assert "- [x] Done" in _codex_plan(checklist, "two", root)[1]
        save(other, [])
        unavailable(lambda: _codex_plan(other, "two", root))
        with codex.open("a") as stream:
            stream.write(json.dumps(progress) + "\n")
        assert _codex_plan(codex, "one", root)[1] == "# Revised"
        with codex.open("a") as stream:
            stream.write(json.dumps(proposed("# Replayed old plan", "2026-01-01T00:00:00Z")) + "\n")
            user = proposed("WRONG", "2027-01-01T00:00:00Z")
            user["payload"]["role"] = "user"
            stream.write(json.dumps(user) + "\n")
            stream.write(json.dumps({"type": "response_item", "payload": {"type": "function_call_output", "output": "<proposed_plan>WRONG</proposed_plan>"}}) + "\n")
            quoted = proposed("WRONG", "2027-01-01T00:00:00Z")
            quoted["payload"]["content"][0]["text"] = "Example syntax:\n```\n<proposed_plan>WRONG</proposed_plan>\n```"
            stream.write(json.dumps(quoted) + "\n")
        assert _codex_plan(codex, "one", root)[1] == "# Revised"
        from unittest.mock import patch
        from types import SimpleNamespace
        first = root / "rollout-first.jsonl"
        second = root / "rollout-second.jsonl"
        guardian = root / "rollout-guardian.jsonl"
        for path, identity, origin in ((first, "first", "cli"), (second, "second", "cli"), (guardian, "guardian", {"subagent": {"other": "guardian"}})):
            save(path, [{"type": "session_meta", "payload": {"id": identity, "source": origin, "cwd": str(root)}}, proposed(f"# {identity}", "2026-01-01T00:00:00Z")])
        descriptor = {"pid": 123, "home": str(root)}
        with patch.object(subprocess, "run", return_value=SimpleNamespace(stdout=f"n{first}\nn{guardian}\n")):
            selected, identity = _codex_journal(descriptor, "codex")
            assert selected == first and identity["id"] == "first"
            assert _codex_plan(selected, identity["id"], root)[1] == "# first"
        with patch.object(subprocess, "run", return_value=SimpleNamespace(stdout=f"n{second}\n")):
            selected, identity = _codex_journal(descriptor, "codex")
            assert _codex_plan(selected, identity["id"], root)[1] == "# second"
        with patch.object(subprocess, "run", return_value=SimpleNamespace(stdout=f"n{first}\nn{second}\n")):
            unavailable(lambda: _codex_journal(descriptor, "codex"))

        claude = root / "claude.jsonl"
        plan = root / "plans/only-this-session.md"
        plan.parent.mkdir()
        plan.write_text("# Saved")
        def tool(name, args, session="one"):
            return {"type": "assistant", "sessionId": session, "message": {"content": [{"type": "tool_use", "name": name, "input": args}]}}
        save(claude, [tool("Write", {"file_path": str(plan), "content": "# Draft"}), tool("ExitPlanMode", {}), {"type": "user", "sessionId": "other", "planContent": "WRONG"}])
        assert _claude_plan(claude, "one", root, root)[1] == "# Saved"
        plan.write_text("# Live revision")
        assert _claude_plan(claude, "one", root, root)[1] == "# Live revision"
        plan.unlink()
        with claude.open("a") as stream:
            stream.write(json.dumps(tool("Edit", {"file_path": str(plan), "old_string": "Draft", "new_string": "Edited"})) + "\n")
        assert _claude_plan(claude, "one", root, root)[1] == "# Edited"
        save(other, [tool("ExitPlanMode", {"plan": "# Inline"})])
        assert _claude_plan(other, "one", root, root)[1] == "# Inline"
        save(other, [{"type": "attachment", "sessionId": "one", "attachment": {"type": "plan_file_reference", "planContent": "# Attached"}}])
        assert _claude_plan(other, "one", root, root)[1] == "# Attached"
        unavailable(lambda: _claude_plan(other, "other", root, root))
        save(other, [{"type": "user", "sessionId": "one", "planContent": "# User plan"}])
        assert _claude_plan(other, "one", root, root)[1] == "# User plan"

        pointer = root / "omp-pointer"
        pointer.write_text(f"{root}\n{omp}\n")
        omp_source = {"pid": 123, "pointer": str(pointer)}
        with patch.object(subprocess, "run", return_value=SimpleNamespace(stdout=f"n{omp}\n")):
            assert _omp_plan(*_omp_session(omp_source))[1] == "# OMP updated"
            pointer.write_text(f"{root}\n{other}\n")
            unavailable(lambda: _omp_session(omp_source))
        with patch.object(subprocess, "run", return_value=SimpleNamespace(stdout=f"n{other}\n")):
            assert _omp_session(omp_source)[0] == other
            unavailable(lambda: _omp_plan(*_omp_session(omp_source)))

        session_one = "00000000-0000-0000-0000-000000000001"
        session_two = "00000000-0000-0000-0000-000000000002"
        one = root / "projects/same-cwd" / f"{session_one}.jsonl"
        two = root / "projects/same-cwd" / f"{session_two}.jsonl"
        save(one, [{"type": "user", "sessionId": session_one, "planContent": "# One"}])
        save(two, [{"type": "user", "sessionId": session_two, "planContent": "# Two"}])
        claude_pointer = root / "claude-pointer.json"
        start = "Thu Jan 1 00:00:00 1970"
        descriptor = {"pid": 123, "start": start, "pointer": str(claude_pointer), "home": str(root)}
        for session, expected in ((session_one, "# One"), (session_two, "# Two")):
            claude_pointer.write_text(json.dumps({"pid": 123, "procStart": start, "sessionId": session, "cwd": str(root)}))
            selected, cwd = _claude_journal(descriptor)
            assert _claude_plan(selected, descriptor["session"], root, cwd)[1] == expected
        descriptor["start"] = "Fri Jan 2 00:00:00 1970"
        unavailable(lambda: _claude_journal(descriptor))
    _JOURNALS.clear()
