# Neovim — holyshit

1. คัดลอก `syntax/hs.vim` ไป `~/.config/nvim/syntax/hs.vim`
   (หรือเก็บทั้งโฟลเดอร์แล้วใส่ `runtimepath`)
2. ใส่ใน `init.lua`:

```lua
vim.opt.runtimepath:append("/path/to/holyshit/editors/neovim")
require("holyshit").setup({ repo = "/path/to/holyshit" })
```

ได้: syntax + indent (2 ช่องว่าง) + LSP (diagnostics/hover/completion/definition)
+ คำสั่ง `:HolyshitCheck`

ตั้งค่าเสริม:

```lua
require("holyshit").setup({
  repo = "/path/to/holyshit",
  python = "python3.12",
})
```
