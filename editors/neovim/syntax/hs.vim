" Vim syntax for holyshit (hs)
" indent-based blocks, # comments, print-without-parens

if exists('b:current_syntax')
  finish
endif

syn case ignore

syn keyword hsDef    def
syn keyword hsIf     if elif else
syn keyword hsLoop   while for in
syn keyword hsJump   break continue return
syn keyword hsScope  global pass
syn keyword hsMod    import from
syn keyword hsTry    try except as finally raise
syn keyword hsLit    true false null
syn keyword hsOp     and or not
syn keyword hsUnsafe unsafe struct extern

syn keyword hsBuiltin print len range str int float input open read write
syn keyword hsBuiltin close append split find join
syn keyword hsBuiltin alloc load8 load32 store8 store32 as_ptr as_int
syn keyword hsBuiltin argv env system ticks readkey pmm_alloc pmm_total
syn keyword hsBuiltin pmm_free meminfo
syn keyword hsBuiltin json_parse json_str json_load json_save read_text
syn keyword hsBuiltin write_text append_text exists ls mkdir
syn keyword hsBuiltin tcp_connect tcp_send tcp_recv tcp_close tcp_listen
syn keyword hsBuiltin tcp_accept http_get

syn match   hsNumber   "\<0[xX]\x\x\+\>"
syn match   hsNumber   "\<\d\+\(\.\d*\)\=\>"
syn match   hsString   "\"[^\\\"]*\""
syn match   hsComment  "#.*$"
syn match   hsComment  "//.*$"

syn region  hsBlock    start=(":\s*$") end="^\s*\S" transparent fold foldenable
syn match   hsDefName  "\<\h\w*\>" containedin=hsDef skipwhite skipempty
            nextgroup=hsDefParen
syn region  hsDefParen start="\(" end="\)" contained transparent

hi def link hsDef       Statement
hi def link hsIf        Statement
hi def link hsLoop      Statement
hi def link hsJump      Statement
hi def link hsScope     Statement
hi def link hsMod       Include
hi def link hsTry       Exception
hi def link hsLit       Constant
hi def link hsOp        Operator
hi def link hsUnsafe    PreProc
hi def link hsBuiltin   Function
hi def link hsNumber    Number
hi def link hsString    String
hi def link hsComment   Comment
hi def link hsDefName   Function
hi def link hsBlock     Delimiter

let b:current_syntax = "holyshit"

" continuation + comments
setlocal comments=:#
setlocal commentstring=#\ %s
setlocal expandtab
setlocal shiftwidth=2
setlocal softtabstop=2
setlocal tabstop=8
setlocal indentexpr=GetHolyshitIndent()
setlocal indentkeys=!^F,o,O,<:>,0),0],=end,=if,=else,=elif,=for,=while,=def,=except,=finally

fun! s:HolyshitIndent()
  let lnum = v:lnum - 1
  let cur = getline(v:lnum)
  if cur =~ '^\s*\(elif\|else\|except\|finally\)\>'
    return indent(lnum + 1)
  endif
  let prev = getline(lnum)
  if prev =~ ':\s*$'
    return indent(lnum + 1) + shiftwidth()
  endif
  return indent(lnum + 1)
endfun

func! GetHolyshitIndent()
  return s:HolyshitIndent()
endfunc
