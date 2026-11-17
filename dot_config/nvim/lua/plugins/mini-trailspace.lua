return {
  'nvim-mini/mini.nvim',
  config = function()
    require('mini.trailspace').setup()
    vim.keymap.set('n', '<F4>', function()
      MiniTrailspace.trim()
      MiniTrailspace.trim_last_lines()
    end, { desc = 'Trim trailing whitespace' })
  end,
}
