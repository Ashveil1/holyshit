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

Runs on x64 (xbuild/xkernel) - uses only slice/index/while/len.

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
