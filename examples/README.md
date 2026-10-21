# tour: every example file really runs

Every file in `examples/` is executed by `tests/test_examples.py` - a broken
example turns the test red instead of silently drifting.

| File | Topic |
|---|---|
| `01_basics.holy` | values, variables, functions, conditions, loops, `and/or/not` |
| `02_strings.holy` | Str: `split`/`join`/`find`, slicing, `str()` |
| `03_collections.holy` | List + Dict (Str keys), nested loops, `break/continue` |
| `04_functions.holy` | recursion, closures, functions as values, `global` |
| `05_errors.holy` | `try/except/finally/raise` including raise inside a handler |
| `06_modules.holy` | `import` + `std.str` / `std.list` + closures into stdlib |
| `07_extern.holy` | libc, `-lm` and `.c` files through the C ABI |
| `08_unsafe.holy` | `I64/U64/Ptr`, structs, pointer walking, raw bytes |
| `hello.holy` `fib.holy` `closure.holy` `ffi.holy` | short examples from the first release |

## Run

```sh
python3 interp.py examples/01_basics.holy
python3 hs.py run examples/04_functions.holy          # via gcc
HSPATH=$PWD python3 interp.py examples/06_modules.holy   # needs std/ visible
```

## Read in this order if you are new

1. `01_basics.holy` - the whole syntax in one file
2. `04_functions.holy` - where the language differs from C/Python (closures capture at def time)
3. `05_errors.holy` - errors are catchable Strs with line numbers
4. `07_extern.holy` - where it connects to other languages
5. `08_unsafe.holy` - where it can touch hardware
