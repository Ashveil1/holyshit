# holyshit - SPEC v0.3 (simpler than Python for small scripts)

## Write it like Python
- No type declarations: `x = 5` (automatic I64); the old `I64 x = 5;` still works
- No `;`: a newline ends a statement; `;` still works when mixed in
- `Print x` / `Print(x)` / `Print x, y` all work
- A lone `"hello"` line prints immediately (HolyC style)
- `#` comments work like `//`
- `for i in 0..5 { }` (exclusive of 5, range style) instead of while
- Top-level code runs directly, no main needed

## Run
- JIT (recommended): `node jit.js prog.HC` - compiles into memory and runs immediately, writes no `.wasm` file
- AOT (see the innards): `python3 compiler.py prog.HC out.wasm && node run.js out.wasm`

## Print v0.3 (Python style)
`Print` separates args with spaces + always ends with a newline; no printf-style format string
- `Print 42` -> `42`
- `Print "hi"` -> `hi`
- `Print "fib:", fib(10)` -> `fib: 55`
- `Print 1, 2, 3` -> `1 2 3`
- bare `Print` -> empty line
- The old `Print("%d", x)` would print `%d` too - change it to `Print x`

## What exists
I64/U0/U64, functions, if/else, while, for..in, return, + - * / %, == != < > <= >=, strings (print only, cannot be stored in vars yet); F64/struct/pointer/array do not exist yet

## Example
```
# no types, no semicolons
x = 2 + 3 * 4
Print x
Print "hello"

for i in 0..5 {
  Print i
}

I64 fib(I64 n) {
  if (n < 2) {
    return n
  }
  return fib(n-1) + fib(n-2)
}
Print "fib:", fib(10)
```
