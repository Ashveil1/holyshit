# Real zlib through the existing C ABI

This example compresses and restores six bytes, including embedded NUL and
0xff, then checks too-small output, invalid compression level and corrupt data.
It prints the compressed byte list, restored byte list and error codes -5, -2,
-3. Compressed bytes can differ between zlib versions; the roundtrip matters.

Requirements: Linux x86-64 LP64, gcc and zlib development headers/library
(`zlib1g-dev` on Debian/Ubuntu). The GCC-native hs route also needs `libgc-dev`.
Build the tiny adapter once, then run from this directory:

```sh
cd examples/zlib
gcc -std=c11 -Wall -Wextra -Werror -shared -fPIC bridge.c -lz -o zlib_bridge.so
python3 ../../hs.py run roundtrip.holy --backend x64
```

The ELF loader resolves `./zlib_bridge.so` from the process working directory,
not from the source file's directory. Keep the working directory as shown.
The interpreter, `--backend native` and the audited hosted compiler can use the
same adapter. Building the adapter needs C; this is not a pure-hs zlib binding.

zlib returns C `int`, while hs exposes I64/U64 rather than an I32 FFI type.
Declaring the zlib functions as I64 directly gives wrong negative error values.
The adapter calls the exact header signatures and sign-extends the result to
`long long`. It copies each 64-bit length cell through a local `uLongf`, avoiding
pointer aliasing between distinct C integer types. Compile-time size assertions
reject platforms outside this example's ABI scope.

The caller owns the source, compressed, output and length buffers and frees
all four in `finally`. `compressBound` sizes the compressed buffer; decompression
uses the known original size, not a guessed expansion factor. Compressed bytes
stay in Ptr buffers, so no raw-byte/Unicode string conversion is involved.
The adapter is not a sandbox: callers must supply valid buffers and lengths.

`python3 tests/test_zlib.py` builds in a disposable directory and requires all
four routes (interpreter, GCC-native, x64 IR and hosted native compiler). It
checks actual compressed bytes with Python's independent zlib decoder. Missing
dependencies fail that test rather than becoming a skipped pass.
