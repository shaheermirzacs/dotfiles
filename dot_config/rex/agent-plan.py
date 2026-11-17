"""Live agent plans in Rex using the user's terminal editor and plugins.

Cmd+Shift+O opens/reuses a right-side pane and keeps agent focus. Sources are
session-specific Codex, OMP, and Claude Code records. VISUAL/EDITOR selects
the editor; normal config/plugins load. Source plans are never written.
Vim/Neovim reload automatically; other editors control their own reloads.

--discover PID prints a JSON source descriptor for the focused agent.
--watch JSON opens an updated read-only Markdown copy of that source.
"""

import argparse
import json
import sys

from agent_plan_sources import discover, load
from agent_plan_view import view


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--discover", type=int, metavar="PID")
    mode.add_argument("--watch", metavar="SOURCE_JSON")
    args = parser.parse_args()
    if args.discover is not None:
        print(json.dumps(discover(args.discover)))
        return 0
    source = json.loads(args.watch)
    if not isinstance(source, dict):
        raise ValueError("The plan source descriptor must be a JSON object.")
    return view(lambda: load(source))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as error:
        sys.exit(f"Agent plan: {error}")
