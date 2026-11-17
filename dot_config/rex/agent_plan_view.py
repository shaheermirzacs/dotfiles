"""Live, read-only agent plans in the user's configured terminal editor.

Uses VISUAL, then EDITOR, then Neovim/vi. If neither variable is inherited,
read the user's interactive-shell settings without changing any config.
Normal editor config/plugins load. Vim/Neovim auto-reload every 500 ms;
other editors receive an updated read-only Markdown file and control reloads.
Only a temporary copy is opened; source plans are never written.
"""

import os
from pathlib import Path
import pwd
import shlex
import shutil
import subprocess
import tempfile
from threading import Event, Thread


def editor_command():
    visual, editor = os.environ.get("VISUAL", ""), os.environ.get("EDITOR", "")
    if not (visual.strip() or editor.strip()):
        shell = os.environ.get("SHELL") or pwd.getpwuid(os.getuid()).pw_shell
        try:
            result = subprocess.run(
                [shell, "-ic", 'printf "\\0%s\\0%s\\0" "$VISUAL" "$EDITOR"'],
                capture_output=True, text=True, timeout=15,
            )
        except subprocess.TimeoutExpired as error:
            raise ValueError(f"Timed out reading the configured editor from {shell}.") from error
        if result.returncode:
            raise ValueError(f"Cannot read the configured editor from {shell}: {result.stderr.strip()}")
        fields = result.stdout.split("\0")
        if len(fields) < 4:
            raise ValueError(f"The user shell {shell} did not return its editor settings.")
        visual, editor = fields[-3:-1]
    command = shlex.split(visual.strip() or editor.strip() or ("nvim" if shutil.which("nvim") else "vi"))
    if not command:
        raise ValueError("VISUAL/EDITOR must name a terminal editor.")
    search_path = os.pathsep.join((os.environ.get("PATH", os.defpath),
                                  "/opt/homebrew/bin", "/usr/local/bin"))
    executable = shutil.which(command[0], path=search_path)
    if not executable:
        raise ValueError(f"Configured editor not found: {command[0]}")
    command[0] = executable
    return command


def _content(load_callback):
    try:
        title, markdown = load_callback()
        return f"{title}  ·  live / read-only\n\n{markdown}"
    except (ValueError, OSError) as error:
        return f"# Agent Plan\n\n{error}\n"


def view(load_callback) -> int:
    command = editor_command()
    if Path(command[0]).name in ("nvim", "vim", "vi"):
        command += [
            "-i", "NONE", "-n", "-R", "-M",
            "--cmd", "set nomodeline noexrc",
            "-c", "syntax enable",
            "-c", "set autoread wrap linebreak noswapfile shortmess+=F",
            "-c", "nnoremap <buffer> q :qa<CR>",
            "-c", "call timer_start(500, {-> execute('silent checktime')}, {'repeat': -1})",
        ]
    with tempfile.TemporaryDirectory(prefix="rex-agent-plan-") as directory:
        snapshot = Path(directory) / "plan.md"
        content = _content(load_callback)
        snapshot.write_text(content)
        snapshot.chmod(0o400)
        stopped = Event()

        def refresh():
            nonlocal content
            while not stopped.wait(0.5):
                updated = _content(load_callback)
                if updated != content:
                    pending = snapshot.with_suffix(".tmp")
                    pending.write_text(updated)
                    pending.chmod(0o400)
                    pending.replace(snapshot)
                    content = updated

        worker = Thread(target=refresh, daemon=True)
        worker.start()
        try:
            return subprocess.call([*command, str(snapshot)])
        finally:
            stopped.set()
            worker.join()


def self_test():
    from unittest.mock import patch

    with tempfile.TemporaryDirectory(prefix="rex-editor-choice-") as directory:
        editor = Path(directory) / "an editor"
        editor.write_text("#!/bin/sh\nexit 0\n")
        editor.chmod(0o700)
        with patch.dict(os.environ, {"VISUAL": shlex.quote(str(editor)) + " --label 'Plan pane'", "EDITOR": "missing-editor"}):
            assert editor_command() == [str(editor), "--label", "Plan pane"]
        with patch.dict(os.environ, {"VISUAL": "", "EDITOR": shlex.quote(str(editor))}):
            assert editor_command() == [str(editor)]
        with patch.dict(os.environ, {"VISUAL": "missing-editor-" + Path(directory).name}):
            try:
                editor_command()
            except ValueError as error:
                assert "Configured editor not found" in str(error)
            else:
                raise AssertionError("An invalid configured editor must not silently choose another")
