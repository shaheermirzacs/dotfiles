return {
  "e-sigs/winbuf.nvim",
  event = "VeryLazy",
  opts = {},
  keys = {
    { "<S-h>", "<Cmd>WinBufPrev<CR>", desc = "Previous buffer in split" },
    { "<S-l>", "<Cmd>WinBufNext<CR>", desc = "Next buffer in split" },
    { "<leader>bd", "<Cmd>WinBufClose<CR>", desc = "Close buffer in split" },
  },
}
