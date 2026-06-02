# Migrating from GNU Stow to chezmoi

This guide walks through converting this dotfiles repo from GNU Stow to chezmoi,
including removing existing symlinks, restructuring the repo, adding Ghostty
config, and getting chezmoi up and running.

## Prerequisites

Install chezmoi:

```bash
brew install chezmoi
```

Make sure your current dotfiles repo is committed or backed up:

```bash
cd ~/development/dotfiles
git stash --include-untracked  # or commit
```

## Step 1: Remove stow symlinks

Unstow every package to remove all symlinks that stow created in `~`:

```bash
cd ~/development/dotfiles
stow -D --dotfiles -t ~ */
```

Verify symlinks are gone:

```bash
# These should all report "No such file or directory"
ls -la ~/.gitconfig ~/.inputrc ~/.vimrc ~/.tmux.conf ~/.tmux
ls -la ~/.ssh/config
ls -la ~/.claude/CLAUDE.md ~/.claude/settings.json ~/.claude/scripts
ls -la ~/.config/starship.toml ~/.config/bat ~/.config/pip ~/.config/uv ~/.config/just
ls -la ~/bashrc-extensions
```

If any symlinks remain, remove them manually:

```bash
# Example: rm ~/.gitconfig  (only if it's still a symlink)
```

## Step 2: Restructure the repo for chezmoi

chezmoi uses a flat directory structure that mirrors `~`, with special naming
conventions. The prefix `dot_` becomes `.` in the target, `private_` sets
restrictive permissions, and `executable_` preserves the execute bit.

### 2a: Clean out old stow artifacts

```bash
cd ~/development/dotfiles

# Remove stow ignore file
rm -f .stow-local-ignore

# Remove git submodules (tmux plugins no longer used)
git submodule deinit -f tmux/dot-tmux/plugins/tpm
git submodule deinit -f tmux/dot-tmux/plugins/tmux-themepack
git rm -f tmux/dot-tmux/plugins/tpm
git rm -f tmux/dot-tmux/plugins/tmux-themepack
rm -rf .git/modules/tmux
rm -f .gitmodules

# Remove Linux-specific files
rm -rf scripts/
rm -f install.sh
rm -f VictorMono.zip

# Remove Linux-only configs
rm -rf config/dot-config/alacritty
rm -rf config/dot-config/fontconfig
rm -rf config/dot-config/htop
rm -rf config/dot-config/op
rm -rf config/dot-config/paco
rm -rf config/dot-config/picom
rm -rf config/dot-config/polybar
rm -rf config/dot-config/rofi
rm -rf config/dot-config/tealdeer

# Remove themes.gitconfig (not referenced)
rm -f git/themes.gitconfig

# Remove vim runtime files (auto-generated)
rm -rf vim/dot-vim

# Remove stale zsh files if staged
git rm -f zsh/zshrc-extensions/admin zsh/zshrc-extensions/global zsh/zshrc-extensions/local 2>/dev/null
rm -rf zsh
```

### 2b: Move files into chezmoi source layout

Each `mv` below moves a file from the old stow package structure into the flat
chezmoi source layout. Run these from the repo root:

```bash
cd ~/development/dotfiles

# --- Shell ---
# Merge bashrc-extensions/global into dot_bashrc (the managed ~/.bashrc)
cp bash/bashrc-extensions/global dot_bashrc
# Append cargo env line that was in the old ~/.bashrc
echo '' >> dot_bashrc
echo '. "$HOME/.cargo/env"' >> dot_bashrc
rm -rf bash/bashrc-extensions

mv bash/dot-inputrc dot_inputrc
rmdir bash

# --- Git ---
mv git/.gitconfig dot_gitconfig
rmdir git

# --- Tmux ---
mv tmux/dot-tmux.conf dot_tmux.conf
rm -rf tmux

# --- Vim ---
mv vim/dot-vimrc dot_vimrc
rm -rf vim

# --- SSH (private permissions) ---
mkdir -p private_dot_ssh
mv ssh/dot-ssh/config private_dot_ssh/private_config
rm -rf ssh

# --- Claude Code ---
mkdir -p dot_claude/scripts
mv claude/dot-claude/CLAUDE.md dot_claude/CLAUDE.md
mv claude/dot-claude/settings.json dot_claude/settings.json
mv claude/dot-claude/scripts/statusline.sh dot_claude/scripts/executable_statusline.sh
rm -rf claude

# --- ~/.config files ---
mkdir -p dot_config/bat dot_config/just dot_config/pip dot_config/uv dot_config/jj

mv config/dot-config/starship.toml dot_config/starship.toml
mv config/dot-config/bat/config dot_config/bat/config
mv config/dot-config/just/justfile dot_config/just/justfile
mv config/dot-config/pip/pip.conf dot_config/pip/pip.conf
mv config/dot-config/uv/uv.toml dot_config/uv/uv.toml
rm -rf config

# --- Jujutsu (new, copy from live config) ---
cp ~/.config/jj/config.toml dot_config/jj/config.toml

# --- Ghostty (new, copy from live config) ---
mkdir -p "Library/Application Support/com.mitchellh.ghostty"
cp ~/Library/Application\ Support/com.mitchellh.ghostty/config.ghostty \
   "Library/Application Support/com.mitchellh.ghostty/config.ghostty"

# --- Brewfile → run_onchange_ script ---
# Remove the standalone Brewfile; its contents move into a chezmoi script (see Step 2c)
rm -f Brewfile
```

### 2c: Create the Homebrew `run_onchange_` script

chezmoi's `run_onchange_` prefix means "re-run this script whenever its contents
change." By embedding the Brewfile directly in the script, any time you add or
remove a brew/cask, chezmoi detects the change and runs `brew bundle`
automatically on the next `chezmoi apply`.

The `before_` in the filename makes it run **before** deploying dotfiles, so
your tools are installed before their configs land.

Create the file:

```bash
cat > ~/dev/dotfiles/run_onchange_before_install-packages-darwin.sh.tmpl << 'OUTER'
{{- if eq .chezmoi.os "darwin" -}}
#!/bin/bash

brew bundle --no-lock --file=/dev/stdin <<EOF
# Bourne-Again SHell, a UNIX command interpreter
brew "bash"
# Programmable completion for Bash 4.2+
brew "bash-completion@2"
# Clone of cat(1) with syntax highlighting and Git integration
brew "bat"
# Manage your dotfiles across multiple diverse machines, securely
brew "chezmoi"
# Embeddable SQL OLAP Database Management System
brew "duckdb"
# Simple, fast and user-friendly alternative to find
brew "fd"
# Command-line fuzzy finder written in Go
brew "fzf"
# Interact with Google Gemini AI models from the command-line
brew "gemini-cli"
# GitHub command-line tool
brew "gh"
# Distributed revision control system
brew "git"
# Git extension for versioning large files
brew "git-lfs"
# Open source programming language to build simple/reliable/efficient software
brew "go"
# CLI for Drive, Gmail, Calendar, Sheets, Docs, Chat, Admin, and more
brew "googleworkspace-cli"
# Git-compatible distributed version control system
brew "jj"
# Handy way to save and run project-specific commands
brew "just"
# Swiss-army knife of markup format conversion
brew "pandoc"
# PDF rendering library (based on the xpdf-3.0 code base)
brew "poppler"
# Search tool like grep and The Silver Searcher
brew "ripgrep"
# CLI proxy to minimize LLM token consumption
brew "rtk"
# Cross-shell prompt for astronauts
brew "starship"
# Extremely fast LaTeX formatter written in Rust
brew "tex-fmt"
# Terminal multiplexer
brew "tmux"
# Display directories as trees (with optional color/HTML output)
brew "tree"
# Extremely fast Python package installer and resolver, written in Rust
brew "uv"
# Shell extension to navigate your filesystem faster
brew "zoxide"
cask "font-victor-mono"
# Set of tools to manage resources and applications hosted on Google Cloud
cask "gcloud-cli"
# Full TeX Live distribution with GUI applications
cask "mactex"
EOF
{{ end -}}
OUTER
```

> **To add or remove packages later:** edit this script directly (or
> `chezmoi edit ~/run_onchange_before_install-packages-darwin.sh.tmpl`),
> then run `chezmoi apply`. chezmoi sees the content changed and re-runs
> `brew bundle`.

### 2d: Verify the new layout

After restructuring, your repo should look like this:

```
~/development/dotfiles/
├── .chezmoiignore
├── .editorconfig
├── CLAUDE.md
├── Library/
│   └── Application Support/
│       └── com.mitchellh.ghostty/
│           └── config.ghostty
├── MIGRATION.md
├── README.md
├── dot_bashrc
├── dot_claude/
│   ├── CLAUDE.md
│   ├── scripts/
│   │   └── executable_statusline.sh
│   └── settings.json
├── dot_config/
│   ├── bat/
│   │   └── config
│   ├── jj/
│   │   └── config.toml
│   ├── just/
│   │   └── justfile
│   ├── pip/
│   │   └── pip.conf
│   ├── starship.toml
│   └── uv/
│       └── uv.toml
├── dot_gitconfig
├── dot_inputrc
├── dot_tmux.conf
├── dot_vimrc
├── private_dot_ssh/
│   └── private_config
└── run_onchange_before_install-packages-darwin.sh.tmpl
```

Confirm with:

```bash
fd -H --max-depth 4 --type f --exclude .git .
```

## Step 3: Create chezmoi metadata files

### `.chezmoiignore`

This tells chezmoi which files in the source directory are NOT dotfiles to deploy:

```bash
cat > ~/dev/dotfiles/.chezmoiignore << 'EOF'
README.md
CLAUDE.md
MIGRATION.md
.editorconfig
.gitattributes
.gitignore
LICENSE
EOF
```

### `.chezmoi.toml.tmpl`

chezmoi config template. This **must** include `sourceDir` so chezmoi knows
the source lives in `~/dev/dotfiles` instead of the default
`~/.local/share/chezmoi`:

```bash
cat > ~/dev/dotfiles/.chezmoi.toml.tmpl << 'EOF'
sourceDir = "{{ .chezmoi.homeDir }}/dev/dotfiles"

[git]
    autoCommit = false
    autoPush = false
EOF
```

## Step 4: Initialize chezmoi with this repo

Point chezmoi at your restructured repo:

```bash
chezmoi init --source ~/dev/dotfiles
```

This tells chezmoi to use `~/dev/dotfiles` as its source directory
instead of the default `~/.local/share/chezmoi`.

Preview what chezmoi will do:

```bash
chezmoi diff
```

Review the diff carefully. It should show chezmoi wanting to create every
managed file in `~`.

## Step 5: Apply

```bash
chezmoi apply -v
```

This copies files from the source directory into their target locations in `~`.
Unlike stow, chezmoi creates **real files** (not symlinks) by default.

### Verify

```bash
# Check files exist and are regular files (not symlinks)
file ~/.gitconfig ~/.inputrc ~/.bashrc ~/.vimrc ~/.tmux.conf

# Check SSH config has correct permissions (should be 0600 or 0644)
ls -la ~/.ssh/config

# Check Claude Code files
ls -la ~/.claude/CLAUDE.md ~/.claude/settings.json ~/.claude/scripts/statusline.sh

# Check ~/.config files
ls -la ~/.config/starship.toml ~/.config/bat/config ~/.config/jj/config.toml
ls -la ~/.config/pip/pip.conf ~/.config/uv/uv.toml ~/.config/just/justfile

# Check Ghostty config
ls -la ~/Library/Application\ Support/com.mitchellh.ghostty/config.ghostty

# Test the shell
source ~/.bashrc
```

## Step 6: Cleanup

### Update the Brewfile

Remove stow, since it's no longer needed:

```bash
# Edit Brewfile and remove the line:
#   brew "stow"
```

### Update README.md

Replace stow instructions with chezmoi usage.

### Commit the restructured repo

```bash
cd ~/development/dotfiles
git add -A
git commit -m "Migrate from GNU Stow to chezmoi"
git push
```

## Step 7: Moving to the default source directory (later)

When you're ready to use the standard chezmoi location (`~/.local/share/chezmoi`),
you can either clone your repo there or move it:

**Option A: Clone from remote**

```bash
# Remove the source dir override
rm -f ~/.config/chezmoi/chezmoi.toml

# Re-init from your git remote
chezmoi init https://github.com/<your-username>/dotfiles.git
chezmoi apply
```

**Option B: Move the directory**

```bash
mv ~/development/dotfiles ~/.local/share/chezmoi
rm -f ~/.config/chezmoi/chezmoi.toml
chezmoi apply
```

## Daily Usage Reference

| Command | What it does |
|---|---|
| `chezmoi add <file>` | Start managing a new file (copies it into the source dir) |
| `chezmoi edit <file>` | Open a managed file's source for editing |
| `chezmoi apply` | Deploy all source files to their targets in `~` |
| `chezmoi apply -v` | Same, but show what changed |
| `chezmoi diff` | Preview what `apply` would change (dry run) |
| `chezmoi update` | Pull latest from git remote, then apply |
| `chezmoi cd` | Open a shell in the source directory |
| `chezmoi managed` | List all files chezmoi manages |
| `chezmoi status` | Show which managed files differ from source |
| `chezmoi re-add` | Update the source from a target you edited in-place |
| `chezmoi doctor` | Diagnose chezmoi configuration issues |

### Typical workflow

```bash
# Edit a config directly, then sync it back to chezmoi source
vim ~/.gitconfig
chezmoi re-add ~/.gitconfig

# Or edit via chezmoi (opens the source copy)
chezmoi edit ~/.gitconfig

# Deploy changes
chezmoi apply -v

# Commit
chezmoi cd
git add -A && git commit -m "update gitconfig"
git push
```

### Adding a new config file

```bash
# Example: start managing a new tool's config
chezmoi add ~/.config/gh/config.yml
chezmoi cd
git add -A && git commit -m "add gh config"
```
