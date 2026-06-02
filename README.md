# dotfiles

Managed with [chezmoi](https://www.chezmoi.io/).

## Getting started

Install chezmoi and apply the dotfiles in one step:

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply git@knot.shaheermirza.sh:shaheermirza.sh/dotfiles
```

If chezmoi is already installed:

```bash
chezmoi init --apply git@knot.shaheermirza.sh:shaheermirza.sh/dotfiles
```

On macOS, packages are installed automatically from the `Brewfile` via the
`run_onchange_before_install-packages-darwin.sh.tmpl` script.

## Adding dotfiles

This repo has `autoCommit` and `autoPush` enabled (see `.chezmoi.toml.tmpl`), so
any change chezmoi makes to the source directory is **automatically committed and
pushed** to the remote.

Track an existing dotfile (it gets the `dot_` prefix automatically):

```bash
chezmoi add ~/.zshrc
```

Edit a tracked file, then preview and apply:

```bash
chezmoi edit ~/.zshrc
chezmoi diff
chezmoi apply
```

Commands like `chezmoi add`, `chezmoi edit`, and `chezmoi chattr` all commit and
push for you - no manual `git` needed.

### When you still need a manual `git add`

`autoCommit`/`autoPush` only fire for changes made **through chezmoi commands**.
If you edit the source directory directly (bypassing `chezmoi`) — you must commit
and push by hand. This applies when you:

- Edit repo files that aren't managed dotfiles (`README.md`, `CLAUDE.md`,
  `Brewfile`, `.chezmoiignore`, the `run_onchange_*` scripts, templates).
- Create or modify files in the source dir with your own editor instead of
  `chezmoi edit`.
- Resolve a merge conflict or otherwise run raw git operations.

In those cases:

```bash
chezmoi cd
git add -A && git commit -m "Update dotfiles" && git push
```
