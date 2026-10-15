-- Neovim setup for holyshit (.holy)
--   :lua require('holyshit').setup()  after copying this repo to ~/.config/nvim/
-- Or just drop the two lines below into init.lua.

local M = {}

function M.setup(opts)
  opts = opts or {}
  local root = opts.repo or vim.fn.expand("$HOME") .. "/holyshit"
  local python = opts.python or "python3"
  local server = root .. "/lsp.py"

  vim.filetype.add({ extension = { holy = "holyshit", hs = "holyshit" } })
  vim.api.nvim_create_user_command("HolyshitCheck", function()
    local f = vim.api.nvim_buf_get_name(0)
    vim.fn.jobstart({ python, root .. "/hs.py", "check", f }, {
      on_stdout = function(_, out)
        vim.schedule(function()
          for _, l in ipairs(out) do if l ~= "" then print(l) end end
        end)
      end
    })
  end, { desc = "run hs.py check on the current file" })

  vim.api.nvim_create_autocmd("FileType", {
    pattern = "holyshit",
    callback = function()
      vim.lsp.start({
        name = "holyshit",
        cmd = { python, server },
        root_dir = root,
        capabilities = vim.tbl_deep_extend(
          "force", vim.lsp.protocol.make_client_capabilities(),
          { textDocument = { completion = { completionItem = {
            snippetSupport = false } } } })
      })
    end,
  })
end

return M
