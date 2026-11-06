/* Linux LP64 adapter: hs I64 is not the C int returned by zlib.
 * Build: cd examples/zlib && gcc -std=c11 -shared -fPIC bridge.c -lz -o zlib_bridge.so
 * Run: cd examples/zlib && python3 ../../hs.py run roundtrip.holy --backend x64
 * Linux x86-64 LP64 only; requires gcc and zlib development headers/library.
 * Run from the source directory: the ELF loader resolves ./zlib_bridge.so
 * relative to the process working directory.
 * The caller owns every buffer. Length pointers refer to writable U64 cells.
 */
#include <zlib.h>

_Static_assert(sizeof(unsigned long) == 8, "requires LP64 unsigned long");
_Static_assert(sizeof(void *) == 8, "requires 64-bit pointers");
_Static_assert(sizeof(long long) == 8, "requires 64-bit hs I64");
_Static_assert(sizeof(int) == 4, "requires 32-bit C int");

unsigned long long hs_z_bound(unsigned long long length) {
    return compressBound((uLong)length);
}

long long hs_z_compress(void *dest, unsigned long long *length,
                        const void *source, unsigned long long source_length,
                        long long level) {
    if (level < -1 || level > 9) return Z_STREAM_ERROR;
    uLongf size = (uLongf)*length;
    int result = compress2(dest, &size, source, (uLong)source_length, (int)level);
    *length = size;
    return result; /* Sign-extend C int into the declared hs I64 result. */
}

long long hs_z_uncompress(void *dest, unsigned long long *length,
                          const void *source, unsigned long long source_length) {
    uLongf size = (uLongf)*length;
    int result = uncompress(dest, &size, source, (uLong)source_length);
    *length = size;
    return result;
}
