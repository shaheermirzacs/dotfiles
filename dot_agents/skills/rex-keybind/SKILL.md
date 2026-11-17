---
name: rex-keybind
description: Look up Neovim shortcuts or commands, remember the ones Mr.Sklk asks about in the curated Rex floating reference, and create new mappings when requested. Use for questions like "what's the nvim keybind for file picker?", "$rex-keybind modified files", and follow-up requests to remember or change a shortcut.
---

# Rex keybind

Keep the answer and the Cmd+Shift+K reference consistent. The reference contains
only shortcuts and commands the user has asked about, not every available mapping.

## Look up and remember

1. Read `~/.local/state/rex-keybind/keybinds.json` and the relevant live Neovim
   config under `~/.config/nvim/`. Inspect installed plugin mappings/help under
   `~/.local/share/nvim/lazy/` when needed. Check built-in commands with installed
   Neovim help. The saved list is a reference, not proof a mapping still exists.
2. Answer with readable keys (for example **Space → f → f**) and the relevant
   mode/context. Distinguish commands, alternate bindings, sequential keys,
   simultaneous keys, and uppercase letters. Explain material limits briefly.
3. If it exists, record it immediately using the helper below. Match the existing
   action and context before adding an entry; reuse its ID for synonyms or updates.
   Keep unrelated entries. Correct stale entries when verified.
4. If there is no mapping, say so. If a built-in command does the job, offer it and
   remember the command. Suggest a free, mnemonic mapping after checking global,
   buffer-local, plugin, and leader-prefix conflicts. Ask before creating a mapping
   unless the user already explicitly asked to create that binding. Never record
   a proposed binding as if it existed.
5. When a new binding is authorized, make the smallest change in the existing
   Neovim config, preserving its conventions. Verify the mapping/callback and any
   affected behavior, then record it. Explain that existing editor processes may
   need a config reload/restart. If the user prefers a command, record the command
   without creating a binding (for example `:tabnew`).

Use existing categories where appropriate: Files, Explorer, Git, Splits, Tabs,
Navigation, Clipboard, View, Save, Annotations, Reference. Add a category only
when needed. Put context and caveats in their fields, not in the key sequence.

## State helper

Run with Python 3 (standard library only):

```sh
python3 \
  ~/.agents/skills/rex-keybind/scripts/rex_keybind.py record find-file \
  --category Files --action 'Find/open a file' \
  --keys 'Ctrl+P or Space f f' --context 'Normal; Ctrl+P also in Insert'
```

The helper atomically upserts by ID and prevents duplicate action/context pairs.
Use a stable lowercase ID, `--notes` for limits, and quote arguments literally.
Use `--state PATH` before the subcommand only for isolated testing. Entries have
`id`, `category`, `action`, `keys`, `context`, and `notes` string fields.

`show` opens a colored reference using Rex's native terminal text rendering and
current font settings. It reads the JSON file. Cmd+Shift+K invokes `show` in a Rex
floating pane; an open viewer notices saved changes automatically. No Rex config
reload is required when recording an entry. Use n/p to page, and Esc/q to close.

Do not create an MR, commit, or change unrelated mappings for a lookup. If a
modified config is chezmoi-managed, sync only that file with autocommit and autopush
disabled. Runtime state stays in `~/.local/state/rex-keybind/`.
