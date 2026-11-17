local node_modules = vim.fn.stdpath("data") .. "/language-servers/node_modules"
vim.env.PATH = node_modules .. "/.bin:" .. vim.fn.expand("~/.local/bin") .. ":" .. vim.env.PATH

vim.lsp.config("*", { capabilities = MiniCompletion.get_lsp_capabilities() })
vim.lsp.config("ruff", {
	on_attach = function(client)
		client.server_capabilities.hoverProvider = false
	end,
})
vim.lsp.config("ts_ls", {
	init_options = { tsserver = { fallbackPath = node_modules .. "/typescript/lib/tsserver.js" } },
})
vim.lsp.config("lua_ls", {
	settings = {
		Lua = {
			runtime = { version = "LuaJIT" },
			workspace = { checkThirdParty = false, library = { vim.env.VIMRUNTIME } },
		},
	},
})
-- Only attach the Angular server inside Angular projects.
vim.lsp.config("angularls", {
	workspace_required = true,
	cmd = function(dispatchers, config)
		local paths = config.root_dir .. "/node_modules," .. node_modules
		return vim.lsp.rpc.start({
			"ngserver",
			"--stdio",
			"--tsProbeLocations",
			paths,
			"--ngProbeLocations",
			paths,
		}, dispatchers)
	end,
})
vim.lsp.enable({
	"ty",
	"ruff",
	"clangd",
	"rust_analyzer",
	"ts_ls",
	"angularls",
	"bashls",
	"yamlls",
	"jsonls",
	"taplo",
	"dockerls",
	"html",
	"cssls",
	"lua_ls",
	"marksman",
})
