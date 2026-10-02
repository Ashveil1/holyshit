#include <stdint.h>

// helper C source for the ffi test: compiled and linked automatically
// via `extern from "ffic.c"`.
int64_t hs_add3(int64_t a, int64_t b, int64_t c) {
    return a + b + c;
}
