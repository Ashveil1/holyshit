# Neovim - holyshit

1. Copy `syntax/hs.vim` to `~/.config/nvim/syntax/hs.vim`
   (or keep the folder and add it to `runtimepath`)
2. Put this in `init.lua`:

```lua
vim.opt.runtimepath:append("/path/to/holyshit/editors/neovim")
require("holyshit").setup({ repo = "/path/to/holyshit" })
```

You get: syntax + indent (2 spaces) + LSP (diagnostics/hover/completion/definition)
+ the `:HolyshitCheck` command

Extra settings:

```lua
require("holyshit").setup({
  repo = "/path/to/holyshit",
  python = "python3.12",
})
```
