local terminal = "com.superlogical.terminal"

local issue_command = [[
set -e
mr=$(glab mr view --output json)
endpoint=$(printf '%s' "$mr" | jq -er 'select(.project_id and .iid) | "projects/\(.project_id)/merge_requests/\(.iid)/related_issues"')
issues=$(glab api "$endpoint" --paginate)
url=$(printf '%s' "$issues" | jq -ers '
  add | unique_by(.web_url) |
  if length == 1 then .[0].web_url
  elif length == 0 then error("No issue is linked to the current MR.")
  else error("Multiple issues are linked to the current MR:\n" + (map(.web_url + " " + .title) | join("\n")))
  end')
exec glab issue view "$url"
]]

rex.action{
  name = "gitlab_view",
  title = "Open GitLab Floating Pane",
  args = { view = "string" },
  run = function(ctx, args)
    local commands = {
      mr = { "glab", "mr", "view" },
      issue = { "sh", "-c", issue_command },
      ci = { "glab", "ci", "view" },
    }
    local command = assert(commands[args.view], "Unknown GitLab view")
    local process, err = rex.block.call(terminal, "process", { block_id = ctx.block_id })
    if not process then error(err, 0) end
    local cwd = process.foreground and process.foreground.cwd
      or process.child and process.child.cwd

    local view
    view, err = rex.session.view{}
    if not view then error(err, 0) end
    local window, current_label
    for _, candidate in ipairs(view.windows or {}) do
      for _, layer in ipairs(candidate.layers or {}) do
        for _, block in ipairs(layer.blocks or {}) do
          if block.block_id == ctx.block_id then
            window, current_label = candidate, block.label
          end
        end
      end
    end
    if not window then error("The focused pane is not in a window", 0) end
    -- Completed viewer panes have no foreground process left to report their directory.
    cwd = cwd or (current_label or ""):match("^GitLab %w+: (.+)$")
    if not cwd then error("Cannot determine the focused pane's directory", 0) end

    local label = "GitLab " .. args.view .. ": " .. cwd
    -- shortcut: reuse preserves output; close the pane to refresh after MR or branch changes.
    for _, layer in ipairs(window.layers or {}) do
      if layer.kind == "floating" then
        for _, block in ipairs(layer.blocks or {}) do
          if block.label == label then
            local result
            result, err = rex.session.set_layer_state{
              layer_id = layer.layer_id, state = "normal", focus = true,
            }
            if not result then error(err, 0) end
            return { layer_id = layer.layer_id, block_id = block.block_id }
          end
        end
      end
    end

    local result
    result, err = rex.session.new_layer{
      window_id = window.window_id,
      bounds = { 0.05, 0.05, 0.9, 0.9 },
      focus = true,
      layout = rex.layout.block{
        flavor = terminal .. ".shell",
        label = label,
        options = { cwd = cwd, command = command, exit = { on_completion = false } },
      },
    }
    if not result then error(err, 0) end
    return result
  end,
}

rex.bind("cmd+shift+m", "gitlab_view", { view = "mr" })
rex.bind("cmd+shift+i", "gitlab_view", { view = "issue" })
rex.bind("cmd+shift+c", "gitlab_view", { view = "ci" })

rex.action{
  name = "neovim_keymaps",
  title = "Show Neovim Keybinds",
  run = function(ctx)
    local view, err = rex.session.view{}
    if not view then error(err, 0) end
    local window
    for _, candidate in ipairs(view.windows or {}) do
      for _, layer in ipairs(candidate.layers or {}) do
        for _, block in ipairs(layer.blocks or {}) do
          if block.block_id == ctx.block_id then window = candidate end
        end
      end
    end
    if not window then error("The focused pane is not in a window", 0) end

    for _, layer in ipairs(window.layers or {}) do
      if layer.kind == "floating" then
        for _, block in ipairs(layer.blocks or {}) do
          if block.label == "Neovim Keybinds" then
            local result
            result, err = rex.session.set_layer_state{
              layer_id = layer.layer_id, state = "normal", focus = true,
            }
            if not result then error(err, 0) end
            return { layer_id = layer.layer_id, block_id = block.block_id }
          end
        end
      end
    end

    local result
    result, err = rex.session.new_layer{
      window_id = window.window_id,
      bounds = { 0.1, 0.1, 0.8, 0.8 },
      focus = true,
      layout = rex.layout.block{
        flavor = terminal .. ".shell",
        label = "Neovim Keybinds",
        options = {
          command = {
            "python3",
            os.getenv("HOME") .. "/.agents/skills/rex-keybind/scripts/rex_keybind.py",
            "show",
          },
          exit = { on_completion = true },
        },
      },
    }
    if not result then error(err, 0) end
    return result
  end,
}

rex.bind("cmd+shift+k", "neovim_keymaps")

rex.action{
  name = "agent_plan_preview",
  title = "Show Live Agent Plan",
  description = "Follow the focused Codex, OMP, or Claude Code plan in your configured editor, with plugins.",
  run = function(ctx)
    local label = "Agent Plan (editor): " .. ctx.block_id
    local view, err = rex.session.view{}
    if not view then error(err, 0) end
    for _, window in ipairs(view.windows or {}) do
      for _, layer in ipairs(window.layers or {}) do
        for _, block in ipairs(layer.blocks or {}) do
          if block.label == label then return { block_id = block.block_id } end
        end
      end
    end
    local process, err = rex.block.call(terminal, "process", { block_id = ctx.block_id })
    if not process then error(err, 0) end
    local foreground = process.foreground
    if not foreground then
      error("Focus a Codex, OMP, or Claude Code agent pane first.", 0)
    end
    local resolved
    resolved, err = rex.exec({
      "python3", os.getenv("HOME") .. "/.config/rex/agent-plan.py", "--discover", tostring(foreground.pid),
    }, { timeout = 15 })
    if not resolved then error(err, 0) end
    if not resolved.ok then error(resolved.stderr, 0) end
    local source = resolved.stdout:gsub("\n$", "")
    local result
    result, err = rex.session.new_split{
      anchor_id = ctx.block_id,
      direction = "horizontal",
      side = "after",
      focus = false,
      layout = rex.layout.block{
        flavor = terminal .. ".shell",
        label = label,
        options = {
          command = { "python3", os.getenv("HOME") .. "/.config/rex/agent-plan.py", "--watch", source },
          exit = { on_completion = true },
        },
      },
    }
    if not result then error(err, 0) end
    return result
  end,
}

rex.bind("cmd+shift+o", "agent_plan_preview")

-- rexdiff: git changes panel next to the focused pane.
-- https://github.com/victorvf/rexdiff — expects the binary at ~/.local/bin/rexdiff (`make install`).

-- Folder of the focused terminal: the one the shell reported, or the running program's.
local function pane_dir(block_id)
  local r = rex.block.call(terminal, "pwd", { block_id = block_id })
  if r and r.pwd and r.pwd ~= "" then return r.pwd end
  local p = rex.block.call(terminal, "process", { block_id = block_id })
  return p and p.foreground and p.foreground.cwd or ""
end

rex.action{
  name = "rexdiff",
  title = "rexdiff: Toggle Changes",
  description = "Opens or closes the git changes panel next to the focused pane.",
  category = "Git",
  keywords = "git diff changes rexdiff",
  run = function(ctx)
    if not ctx.block_id then return end
    local r, err = rex.exec(
      { os.getenv("HOME") .. "/.local/bin/rexdiff", "toggle", "--focus", "--cwd", pane_dir(ctx.block_id) },
      { env = { REX_SESSION = ctx.session_id, REX_BLOCK = ctx.block_id }, timeout = 15 }
    )
    if not r then
      rex.log("error", "rexdiff: " .. tostring(err))
    elseif not r.ok then
      rex.log("warn", "rexdiff: " .. r.stderr)
    end
  end,
}

-- Option+Shift+? (Rex wants the key without Shift applied: "?" is Shift+/).
rex.bind("alt+shift+/", "rexdiff")
