"""Curated Neovim reference using Rex's native terminal text rendering."""

import argparse
from collections import OrderedDict
import fcntl
import json
import os
from pathlib import Path
import re
import select
import sys
import tempfile
import termios
import textwrap
import tty

STATE = Path.home() / ".local/state/rex-keybind/keybinds.json"
FIELDS = ("id", "category", "action", "keys", "context", "notes")
BG, FG, MUTED = "#0d111a", "#e2e7ef", "#bec9da"
COLORS = ("#80c7ff", "#a9d98a", "#e5c07b", "#c5a0ef", "#70cfd2", "#ef9c9c")


def load(path):
    entries = json.loads(path.read_text())
    if not isinstance(entries, list):
        raise ValueError("Reference must be a JSON list")
    ids, actions = set(), set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != set(FIELDS):
            raise ValueError(f"Each entry needs these fields: {', '.join(FIELDS)}")
        if any(not isinstance(entry[field], str) for field in FIELDS):
            raise ValueError("Entry fields must be strings")
        if any(not entry[field].strip() for field in FIELDS[:4]):
            raise ValueError("ID, category, action, and keys cannot be empty")
        if any(any(ord(c) < 32 or ord(c) == 127 for c in value) for value in entry.values()):
            raise ValueError("Entry fields cannot contain terminal control characters")
        action = (entry["action"].casefold(), entry["context"].casefold())
        if entry["id"] in ids or action in actions:
            raise ValueError("Duplicate entry ID or action/context")
        ids.add(entry["id"])
        actions.add(action)
    return entries


def record(path, entry):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.with_suffix(".lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = load(path) if path.exists() else []
        action = (entry["action"].casefold(), entry["context"].casefold())
        for index, old in enumerate(entries):
            if old["id"] == entry["id"] or (old["action"].casefold(), old["context"].casefold()) == action:
                entry = dict(entry, id=old["id"])
                entries[index] = entry
                break
        else:
            entries.append(entry)
        temp = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as out:
                temp = Path(out.name)
                json.dump(entries, out, ensure_ascii=False, indent=2)
                out.write("\n")
            load(temp)
            os.replace(temp, path)
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)


def pages(entries, width, height):
    """Lay out readable columns; overflow goes to another page, never smaller type."""
    columns = max(1, min(3, width // 60))
    col_width = (width - 6) // columns
    capacity = max(1, height - 8)
    wrap = max(12, col_width - 4)
    key_width = min(24, wrap // 2)
    groups = OrderedDict()
    for entry in entries:
        groups.setdefault(entry["category"], []).append(entry)
    result, page, column, row = [], [], 0, 0

    def advance():
        nonlocal page, column, row
        column, row = column + 1, 0
        if column == columns:
            result.append(page)
            page, column = [], 0

    def compact(keys):
        for before, after in [("Space", "SPC"), ("Ctrl+", "C-"), ("Shift+", "S-"),
                              ("Cmd+", "D-"), (" or ", " / "), (" then ", " ")]:
            keys = keys.replace(before, after)
        return keys

    for group_index, (category, items) in enumerate(groups.items()):
        color = COLORS[group_index % len(COLORS)]
        lines = []
        for entry in items:
            keys = textwrap.wrap(compact(entry["keys"]), key_width)
            labels = textwrap.wrap(entry["action"], wrap - key_width - 2)
            for index in range(max(len(keys), len(labels))):
                lines.append((keys[index] if index < len(keys) else "", color,
                              labels[index] if index < len(labels) else ""))
        if row and (len(lines) + 2 > capacity - row):
            advance()
        headings = [(line, color, "") for line in textwrap.wrap(category.upper(), wrap)]
        for text, ink, label in headings + [("", FG, "")] + lines + [("", FG, "")]:
            if row == capacity:
                advance()
            page.append((3 + column * col_width, 5 + row, text, ink))
            if label:
                page.append((3 + column * col_width + key_width + 2,
                             5 + row, label, FG))
            row += 1
    if page or not result:
        result.append(page)
    return result


def render(page, width, height, number, total, count):
    def ansi_color(value, background=False):
        rgb = ";".join(str(int(value[i:i + 2], 16)) for i in (1, 3, 5))
        return f"\033[{48 if background else 38};2;{rgb}m"

    output = [ansi_color(BG, background=True), "\033[2J\033[H"]

    def put_text(x, y, value, ink=FG, bold=False):
        output.append(f"\033[{y + 1};{x + 1}H\033[{1 if bold else 22}m{ansi_color(ink)}{value}")

    put_text(3, 1, f"NEOVIM / YOUR KEYBINDS  ·  {count} actions", bold=True)
    hint = "SPC Space · C- Ctrl · S- Shift · D- Cmd"
    put_text(3, 2, hint, MUTED)
    put_text(3, 3, "─" * (width - 6), MUTED)
    for x, y, text, color in page:
        put_text(x, y, text, color, bold=color not in (FG, MUTED))
    put_text(3, height - 2, f"n/p pages  ·  Esc/q close    {number + 1}/{total}", MUTED)
    return "".join(output)


def show(path):
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    current, previous = 0, None
    sys.stdout.write("\033[?1049h\033[?25l")
    sys.stdout.flush()
    try:
        tty.setcbreak(fd)
        while True:
            columns, rows = os.get_terminal_size(fd)
            if rows < 12 or columns < 50:
                raise ValueError("Enlarge the floating reference to at least 50 columns and 12 rows")
            stamp = (path.stat().st_mtime_ns, columns, rows, current)
            if stamp != previous:
                entries = load(path)
                layout = pages(entries, columns, rows)
                current = min(current, len(layout) - 1)
                sys.stdout.write(render(layout[current], columns, rows, current, len(layout), len(entries)))
                sys.stdout.flush()
                previous = (*stamp[:-1], current)
            if select.select([fd], [], [], 0.25)[0]:
                key = os.read(fd, 32)
                if key in (b"n", b"j", b" "):
                    current = (current + 1) % len(layout)
                elif key in (b"p", b"k", b"b"):
                    current = (current - 1) % len(layout)
                else:
                    break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        sys.stdout.write("\033[0m\033[?25h\033[?1049l")
        sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=STATE)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("record")
    add.add_argument("id")
    for field in FIELDS[1:]:
        add.add_argument("--" + field, required=field in FIELDS[1:4], default="")
    commands.add_parser("show")
    args = parser.parse_args()
    if args.command == "record":
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", args.id):
            parser.error("Use a lowercase, hyphen-separated ID")
        record(args.state, {field: getattr(args, field) for field in FIELDS})
    elif args.command == "show":
        show(args.state)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        sys.exit(f"rex-keybind: {error}")
