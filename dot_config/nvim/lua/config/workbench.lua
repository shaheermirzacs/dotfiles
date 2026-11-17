for _, name in ipairs({ "icons", "pick", "extra", "files", "completion", "statusline", "diff" }) do
	require("mini." .. name).setup()
end

local default_statusline = MiniStatusline.active
MiniStatusline.active = function()
	return default_statusline() .. " " .. require("rex-nvim").statusline()
end

require("mini.clue").setup({
	triggers = { { mode = "n", keys = "<Leader>" }, { mode = "n", keys = "<C-w>" } },
	clues = { require("mini.clue").gen_clues.windows() },
	window = { delay = 300 },
})

require("mini.sessions").setup({
  autoread = vim.fn.getcwd() ~= vim.env.HOME,
  autowrite = true,
  directory = "",
})

vim.api.nvim_create_autocmd("VimLeavePre", {
  callback = function()
    if vim.fn.argc() == 0 and vim.fn.getcwd() ~= vim.env.HOME then
      MiniSessions.write("Session.vim")
    end
  end,
})

vim.opt.mouse = "a"
vim.opt.clipboard = "unnamedplus"
vim.opt.ignorecase = true
vim.opt.smartcase = true
vim.opt.signcolumn = "yes"
vim.opt.termguicolors = true
vim.opt.splitright = true
vim.opt.splitbelow = true
vim.opt.updatetime = 250
vim.opt.completeopt = "menuone,noselect,fuzzy"
vim.opt.cursorline = true

vim.api.nvim_create_autocmd({ "WinEnter", "WinLeave" }, {
  callback = function(event)
    vim.opt_local.cursorline = event.event == "WinEnter"
  end,
})

local function find_files()
  MiniPick.builtin.cli({
    command = { "rg", "--files", "--hidden", "--glob", "!.git" },
  })
end

local map = vim.keymap.set
map({ "n", "i" }, "<C-p>", find_files, { desc = "Find files" })
map("n", "<leader>ff", find_files, { desc = "Find files" })
map("n", "<leader>fc", "<Cmd>Pick git_files scope='modified'<CR>", { desc = "Find changed files" })
map("n", "<leader>fg", MiniPick.builtin.grep_live, { desc = "Search project text" })
map("n", "<leader>/", MiniPick.builtin.grep_live, { desc = "Search project text" })
map("n", "<leader>fb", MiniPick.builtin.buffers, { desc = "Switch open file" })
map("n", "<leader>fr", MiniExtra.pickers.oldfiles, { desc = "Recent files" })
map("n", "<leader>p", MiniExtra.pickers.commands, { desc = "Command palette" })
map("n", "<leader>?", MiniExtra.pickers.keymaps, { desc = "Search shortcuts" })
map("n", "<leader>e", function()
	if not MiniFiles.close() then
		MiniFiles.open()
	end
end, { desc = "Toggle file browser" })
map("n", "<C-b>", "<leader>e", { remap = true, desc = "Toggle file browser" })
map({ "n", "i", "x" }, "<C-s>", "<Cmd>write<CR>", { desc = "Save file" })
-- map("n", "<leader>bd", "<Cmd>bdelete<CR>", { desc = "Close file" })
-- map("n", "<S-l>", "<Cmd>bnext<CR>", { desc = "Next open file" })
-- map("n", "<S-h>", "<Cmd>bprevious<CR>", { desc = "Previous open file" })
map("n", "<leader>sv", "<Cmd>vsplit<CR>", { desc = "Split right" })
map("n", "<leader>sh", "<Cmd>split<CR>", { desc = "Split below" })
map("n", "<leader>t", "<Cmd>botright 12split | terminal<CR>", { desc = "Open terminal" })
map("t", "<Esc><Esc>", "<C-\\><C-n>", { desc = "Leave terminal input" })
map("n", "<leader>gd", MiniDiff.toggle_overlay, { desc = "Toggle Git diff" })
map("n", "<leader>xx", MiniExtra.pickers.diagnostic, { desc = "Problems" })
map("n", "<leader>cf", function()
	vim.lsp.buf.format()
end, { desc = "Format file" })
map("n", "<F12>", vim.lsp.buf.definition, { desc = "Go to definition" })
map("n", "<F2>", vim.lsp.buf.rename, { desc = "Rename symbol" })
map("n", "<leader>ca", vim.lsp.buf.code_action, { desc = "Code actions" })
map("n", "<leader>fs", function()
	MiniExtra.pickers.lsp({ scope = "document_symbol" })
end, { desc = "File symbols" })
map("i", "<Tab>", function()
	return vim.fn.pumvisible() == 1 and "<C-n>" or "<Tab>"
end, { expr = true })
map("i", "<S-Tab>", function()
	return vim.fn.pumvisible() == 1 and "<C-p>" or "<S-Tab>"
end, { expr = true })
map("i", "<CR>", function()
	return vim.fn.pumvisible() == 1 and "<C-y>" or "<CR>"
end, { expr = true })

require("config.lsp")
