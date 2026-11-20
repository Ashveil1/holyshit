# stdlib - `std/` (written in pure hs)

`import std.str` needs `std/` visible as a directory on `HSPATH`
(the program's own directory always comes first, then `HSPATH`, colon-separated):

```sh
# from the repo directory: point HSPATH at the repo (which contains std/)
HSPATH=/path/to/holyshit python3 interp.py prog.holy
# or copy std/ next to your program and import directly with nothing set
```

An example that really runs in the tests:

```hs
import std.str
import std.list

def add(a, b):
  return a + b

print std.str.trim("  hi  ")
print std.list.fold(add, 0, [1, 2, 3])
print std.str.starts_with("holyshit", "holy")
# => hi
# => 6
# => true
```

## std.str - text

| Function | What it does |
|---|---|
| `trim(s)` | strip surrounding whitespace (`" \t\n\r`) |
| `pad_left(s, w)` / `pad_right(s, w)` | pad with spaces to width `w` |
| `starts_with(s, pre)` / `ends_with(s, suf)` | prefix/suffix check |
| `lines(s)` | split into a List of lines (`split(s, "\n")`) |
| `lower(s)` / `upper(s)` | ASCII case mapping; every other character passes through byte-identical on every backend |
| `replace(s, old, new)` | non-overlapping replacement, left to right; an empty `old` raises |
| `count(s, sub)` | non-overlapping occurrences; an empty `sub` raises |
| `find_from(s, sub, start)` | `find` with a start index; a negative start counts from the end; -1 when absent |
| `split_n(s, sep, maxsplit)` | `split` with a split limit (negative = no limit, 0 returns `[s]`); an empty separator raises |
| `strip(s, chars)` / `lstrip(s, chars)` / `rstrip(s, chars)` | strip any character in `chars` (printable ASCII plus `\t` `\n` `\r`); an empty `chars` strips nothing |

Runs on x64 (xbuild/xkernel) - uses only slice/index/while/len.

Backend note: the reference interpreter indexes strings per character,
while the compiled x64 backends index per byte (a known language-level
divergence for non-ASCII text). These helpers give the same result under
both models: `lower`/`upper` only transform ASCII bytes, which never
appear inside multi-byte UTF-8 sequences, and `replace`, `count`,
`split_n` and the `strip` family rebuild their output from original
slices. Inputs whose answer would depend on the indexing model raise
instead of silently diverging: an empty `old` in `replace`, an empty
`sub` in `count`, and non-ASCII `chars` in the `strip` family. Like the
builtin `find`, the index returned by `find_from` counts characters on
the reference interpreter and bytes on compiled x64; the models agree on
plain ASCII text.

```hs
import std.str
print std.str.replace("a-b-c", "-", "+")
print std.str.upper("mix Ed 123")
print std.str.split_n("a,b,c,d", ",", 2)
print std.str.strip("..hi..", ".")
# => a+b+c
# => MIX ED 123
# => [a, b, c,d]
# => hi
```

## std.fmt - string formatting

`format(template, args)` substitutes sequential `{}` placeholders from the
List `args` using `str()` conversion. Extra arguments are ignored (like
Python); a `{}` with no argument left raises. `{{` and `}}` are literal
braces. Anything else inside braces raises: there are no positional `{0}`,
named `{name}` or format-spec fields, and a lone `}` raises.

All scanning looks for the ASCII tokens `{` and `}` and rebuilds the output
from original slices, so the reference interpreter (per-character indexing)
and the compiled x64 backends (per-byte indexing) agree for every template
and argument.

```hs
import std.fmt
print std.fmt.format("{} + {} = {}", [2, 3, 5])
print std.fmt.format("{{{}?}}", ["no"])
print std.fmt.format("{} and {}", ["hi", [1, true]])
# => 2 + 3 = 5
# => {no?}
# => hi and [1, true]
```

## std.path - lexical POSIX paths

All arguments are Str. Only `/` is a separator; backslashes and drive letters
are ordinary text. These helpers never access the filesystem. They do not
resolve symlinks, check existence or permissions, or prove a path stays inside
a directory. In particular, lexical `..` removal can change a symlinked path's
meaning. Do not use it as a sandbox or containment check.

| Function | What it does |
|---|---|
| `isabs(path)` | true when the first character is `/` |
| `join(base, path)` | join two paths; an absolute right argument replaces the base; an empty right argument preserves/adds a trailing slash |
| `basename(path)` | last component; empty for a trailing slash |
| `dirname(path)` | directory component; drops trailing slashes except when the head is all slashes |
| `splitext(path)` | `[root, extension]`, extension includes its dot; leading dots alone do not count |
| `normpath(path)` | collapse repeated separators, `.` and lexical `..`; empty becomes `.`; preserve exactly two initial slashes, reduce three or more to one |

`normpath` preserves unresolved leading `..` in relative paths and never climbs
above an absolute root. It removes trailing separators except at roots.
These are POSIX string rules, not Windows path rules. `join` takes exactly two
strings, and does not normalize its result.

```hs
import std.path
print std.path.join("cache", "runs/model.json")  # cache/runs/model.json
print std.path.normpath("//cache/a/../b/")       # //cache/b
print std.path.basename("cache/")               # empty string
print std.path.dirname("report.txt")            # empty string
print std.path.splitext(".cache.tar.gz")         # [.cache.tar, .gz]
```

The installed native bundle supplies the library search path automatically,
including after relocation. `hs run`, `hs build`, `hs interpret` and `hs repl`
can import `std.path` without a checkout or Python. In the REPL, import and
use the module in the same submission (for example, one multiline block);
module-name parsing does not persist between submissions. The corpus tests compare
with Python's `posixpath` on edge cases, deterministic random paths, Unicode,
control characters and long paths across reference, IR and native routes.

## std.list - functional list helpers

| Function | What it does |
|---|---|
| `map(f, xs)` | new List of `f(x)` for each element |
| `filter(f, xs)` | only elements where `f(x)` is true |
| `fold(f, acc, xs)` | accumulate `acc = f(acc, x)` |
| `any(f, xs)` / `all(f, xs)` | whether any/every element is true |

Runs on x64 (demonstrates closures too)

## std.bitmap - bit set over bytes (for frame allocators, GDT/IDT slots)

bit `i` lives at byte `i / 8` mask `1 << (i % 8)` - every function takes the
base as an Int address (from `alloc()`) and uses only `load8/store8`, so it
runs on every backend

| Function | What it does |
|---|---|
| `bit_get/set/clear/toggle(base, i)` | read/write/flip a single bit |
| `bit_reserve(base, start, count)` / `bit_release(...)` | mark a bit range |
| `bit_count_used(base, nbits)` | count used bits |
| `bit_find(base, nbits)` / `bit_find_from(..., start)` | first free bit, `-1` when full |
| `bit_run_free(base, start, want)` | number of consecutive free bits from `start` |
| `bit_alloc_run(base, nbits, want, start)` | find a free run of `want`, `-1` when short |
| `bit_take(base, nbits, start, want)` | `alloc_run` + mark immediately |
| `bitmap_bytes(nbits)` | number of bytes needed |

> x64 note: module-level names are resolved statically - **a called function
> must be defined before its caller** (order the file accordingly)

## std.heap - malloc/free over unsafe (K&R style)

| Function | What it does |
|---|---|
| `heap_init(nbytes)` | prepare the region (call once) |
| `malloc(nbytes)` | allocate -> address (Int), `0` when full |
| `free(p)` | release (coalesces neighbors) |
| `heap_free()` / `heap_nblocks()` | free space / block count |

Addresses are plain Ints (`as_int`/`as_ptr` cross the boundary), single-threaded.
Usable on x64 when the whole program stays inside the `unsafe:` subset.

## Software graphics: std.gfx

A hardware-independent RGB24 drawing foundation. Import `std.gfx`, allocate
`s = std.gfx.surface(width, height, color)`, then use `pixel(s,x,y,color)`,
`rect(s,x,y,width,height,color)`, `blit(dst,src,x,y)` and `sample(s,x,y)` through
the module. Colors are packed `0xRRGGBB`; rectangles are half-open and clipped.
Writes outside the surface are ignored; reads outside it raise. Self-blits
snapshot their source. Dimensions/pixel-list storage must remain intact.

Surface storage is `[width,height,pixels]`, limited to1,048,576 pixels and
4096 per dimension. Coordinates/extents are Ints within ±1,048,576. This module
has no framebuffer mapping, fonts, input events or windows. The software
preview in `examples/gfx_surface.holy` prints dimensions and a deterministic pixel checksum; it is not a
running desktop. Kernel execution is checked with serial output in full CI.
