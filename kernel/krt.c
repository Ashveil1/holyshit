// holyshit kernel runtime (เฟส 5a) — freestanding, no libc, no GC library.
// Heap: bump allocator (never freed). Console: serial COM1 + VGA text.
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>

#include "krt.h"

// ---------- tiny libc substitutes ----------
static void *km_memset(void *d, int c, size_t n) {
    uint8_t *p = d;
    while (n--)
        *p++ = (uint8_t)c;
    return d;
}

static void *km_memcpy(void *d, const void *s, size_t n) {
    uint8_t *p = d;
    const uint8_t *q = s;
    while (n--)
        *p++ = *q++;
    return d;
}

static int km_memcmp(const void *a, const void *b, size_t n) {
    const uint8_t *p = a, *q = b;
    while (n--) {
        if (*p != *q)
            return *p - *q;
        p++;
        q++;
    }
    return 0;
}

static size_t km_strlen(const char *s) {
    size_t n = 0;
    while (s[n])
        n++;
    return n;
}

static int km_strcmp(const char *a, const char *b) {
    while (*a && *a == *b) {
        a++;
        b++;
    }
    return (uint8_t)*a - (uint8_t)*b;
}

static uint8_t km_inb(uint16_t port) {
    uint8_t v;
    __asm__ volatile("inb %1, %0" : "=a"(v) : "Nd"(port));
    return v;
}

static void km_outb(uint16_t port, uint8_t v) {
    __asm__ volatile("outb %0, %1" : : "a"(v), "Nd"(port));
}

void hs_outb(uint16_t port, uint8_t v) { km_outb(port, v); }
uint8_t hs_inb(uint16_t port) { return km_inb(port); }

// ---------- serial COM1 ----------
#define COM1 0x3F8

static void serial_init(void) {
    km_outb(COM1 + 1, 0x00);
    km_outb(COM1 + 3, 0x80);
    km_outb(COM1 + 0, 0x03);
    km_outb(COM1 + 1, 0x00);
    km_outb(COM1 + 3, 0x03);
    km_outb(COM1 + 2, 0xC7);
    km_outb(COM1 + 4, 0x0B);
}

static void serial_putc(char c) {
    while (!(km_inb(COM1 + 5) & 0x20))
        ;
    km_outb(COM1, (uint8_t)c);
}

// ---------- VGA text 80x25 ----------
static uint16_t *const VGA = (uint16_t *)0xB8000;
static int vga_row, vga_col;

static void vga_scroll(void) {
    for (int r = 1; r < 25; r++)
        for (int c = 0; c < 80; c++)
            VGA[(r - 1) * 80 + c] = VGA[r * 80 + c];
    for (int c = 0; c < 80; c++)
        VGA[24 * 80 + c] = 0x0700;
    vga_row = 24;
}

static void vga_putc(char c) {
    if (c == '\n') {
        vga_col = 0;
        if (++vga_row >= 25)
            vga_scroll();
        return;
    }
    VGA[vga_row * 80 + vga_col] = 0x0700 | (uint8_t)c;
    if (++vga_col >= 80) {
        vga_col = 0;
        if (++vga_row >= 25)
            vga_scroll();
    }
}

static void kputs(const char *s) {
    while (*s) {
        serial_putc(*s);
        vga_putc(*s);
        s++;
    }
}

// ---------- bump heap (never freed; kernel phase 1) ----------
extern char hs_heap_start[];
extern char hs_heap_end[];
static char *hs_brk = 0;

static void *kmalloc(size_t n) {
    if (!hs_brk)
        hs_brk = hs_heap_start;
    n = (n + 7) & ~(size_t)7;
    if (hs_brk + n > hs_heap_end)
        hs_err(-1, "kernel heap exhausted");
    char *p = hs_brk;
    hs_brk += n;
    return p;
}

// ---------- error ----------
static void kputi(int64_t n) {
    char rev[24];
    int j = 0;
    if (n < 0) {
        serial_putc('-');
        vga_putc('-');
        n = -n;
    }
    if (n == 0)
        rev[j++] = '0';
    while (n > 0) {
        rev[j++] = '0' + (n % 10);
        n /= 10;
    }
    while (j > 0) {
        char c = rev[--j];
        serial_putc(c);
        vga_putc(c);
    }
}

static void kputu(uint64_t n) {
    char rev[24];
    int j = 0;
    if (n == 0)
        rev[j++] = '0';
    while (n > 0) {
        rev[j++] = '0' + (n % 10);
        n /= 10;
    }
    while (j > 0) {
        char c = rev[--j];
        serial_putc(c);
        vga_putc(c);
    }
}

static void kputx(uint64_t n) {
    char rev[20];
    int j = 0;
    if (n == 0)
        rev[j++] = '0';
    while (n > 0) {
        int d = n & 0xF;
        rev[j++] = d < 10 ? '0' + d : 'a' + d - 10;
        n >>= 4;
    }
    while (j > 0) {
        char c = rev[--j];
        serial_putc(c);
        vga_putc(c);
    }
}

static void khalt(void) {
    kputs("\nHALT\n");
    __asm__ volatile("cli");
    for (;;)
        __asm__ volatile("hlt");
}

void hs_err(int line, const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    kputs("error: ");
    for (const char *p = fmt; *p; p++) {
        if (*p != '%') {
            serial_putc(*p);
            vga_putc(*p);
            continue;
        }
        p++;
        if (*p == 's') {
            kputs(va_arg(ap, const char *));
        } else if (*p == 'c') {
            char c = (char)va_arg(ap, int);
            serial_putc(c);
            vga_putc(c);
        } else if (*p == 'd') {
            kputi((int64_t)va_arg(ap, int));
        } else if (*p == 'l' && p[1] == 'l' && (p[2] == 'd' || p[2] == 'u')) {
            int is_u = p[2] == 'u';
            p += 2;
            if (is_u)
                kputu(va_arg(ap, uint64_t));
            else
                kputi(va_arg(ap, int64_t));
        } else if (*p == 'u') {
            kputu((uint64_t)va_arg(ap, unsigned));
        } else if (*p == 'x') {
            kputx((uint64_t)va_arg(ap, unsigned));
        } else if (*p == '%') {
            serial_putc('%');
            vga_putc('%');
        } else {
            serial_putc('%');
            vga_putc('%');
            serial_putc(*p);
            vga_putc(*p);
        }
    }
    va_end(ap);
    if (line >= 0) {
        kputs(" at line ");
        kputi(line);
    }
    kputs("\n");
    khalt();
}

// ---------- constructors ----------
Val v_null(void) { return (Val){T_NULL, {0}}; }
Val v_bool(int b) { return (Val){T_BOOL, {.b = !!b}}; }
Val v_int(int64_t i) { return (Val){T_INT, {.i = i}}; }
Val v_float(double f) { return (Val){T_FLOAT, {.f = f}}; }
Val v_unbound(void) { return (Val){T_UNBOUND, {0}}; }

Val v_strn(const char *s, int64_t n) {
    Str *o = kmalloc(sizeof(Str) + (size_t)n + 1);
    o->len = n;
    km_memcpy(o->data, s, (size_t)n);
    o->data[n] = '\0';
    return (Val){T_STR, {.p = o}};
}

Val v_str(const char *s) { return v_strn(s, (int64_t)km_strlen(s)); }

Val v_list(void) {
    List *o = kmalloc(sizeof(List));
    o->len = 0;
    o->cap = 4;
    o->items = kmalloc(sizeof(Val) * (size_t)o->cap);
    return (Val){T_LIST, {.p = o}};
}

static void list_grow(List *o, int64_t need) {
    if (o->cap >= need)
        return;
    int64_t oldcap = o->cap;
    while (o->cap < need)
        o->cap *= 2;
    Val *ni = kmalloc(sizeof(Val) * (size_t)o->cap);
    km_memcpy(ni, o->items, sizeof(Val) * (size_t)oldcap);
    o->items = ni;
}

Val v_dict(void) {
    Dict *o = kmalloc(sizeof(Dict));
    o->len = 0;
    o->cap = 4;
    o->keys = kmalloc(sizeof(char *) * (size_t)o->cap);
    o->vals = kmalloc(sizeof(Val) * (size_t)o->cap);
    return (Val){T_DICT, {.p = o}};
}

static void dict_grow(Dict *o) {
    if (o->len < o->cap)
        return;
    int64_t oldcap = o->cap;
    o->cap *= 2;
    char **nk = kmalloc(sizeof(char *) * (size_t)o->cap);
    Val *nv = kmalloc(sizeof(Val) * (size_t)o->cap);
    km_memcpy(nk, o->keys, sizeof(char *) * (size_t)oldcap);
    km_memcpy(nv, o->vals, sizeof(Val) * (size_t)oldcap);
    o->keys = nk;
    o->vals = nv;
}

Val v_func(Val (*fn)(Val *, int, int), const char *name, int arity) {
    Func *o = kmalloc(sizeof(Func));
    o->fn = fn;
    o->name = name;
    o->arity = arity;
    return (Val){T_FUNC, {.p = o}};
}

Val v_file(void *fp, const char *path) {
    (void)fp;
    (void)path;
    return v_null();
}

// ---------- misc ----------
Val v_chk(Val v, const char *name, int line) {
    if (v.tag == T_UNBOUND)
        hs_err(line, "unknown variable '%s'", name);
    return v;
}

int v_truthy(Val v) {
    switch (v.tag) {
    case T_NULL:
    case T_UNBOUND:
        return 0;
    case T_BOOL:
        return v.u.b;
    case T_INT:
        return v.u.i != 0;
    case T_FLOAT:
        return v.u.f != 0.0;
    case T_STR:
        return AS_STR(v)->len != 0;
    case T_LIST:
        return AS_LIST(v)->len != 0;
    case T_DICT:
        return AS_DICT(v)->len != 0;
    default:
        return 1;
    }
}

const char *hs_tname(Val v) {
    switch (v.tag) {
    case T_UNBOUND:
        return "Unbound";
    case T_NULL:
        return "Null";
    case T_BOOL:
        return "Bool";
    case T_INT:
        return "Int";
    case T_FLOAT:
        return "Float";
    case T_STR:
        return "Str";
    case T_LIST:
        return "List";
    case T_DICT:
        return "Dict";
    case T_FUNC:
        return "Func";
    case T_FILE:
        return "File";
    case T_BUILTIN:
        return "Builtin";
    default:
        return "?";
    }
}

static int is_num(Val v) {
    return v.tag == T_INT || v.tag == T_FLOAT;
}

static double to_f(Val v) {
    return v.tag == T_FLOAT ? v.u.f : (double)v.u.i;
}

// ---------- operators ----------
Val v_add(Val a, Val b, int line) {
    if (is_num(a) && is_num(b)) {
        if (a.tag == T_FLOAT || b.tag == T_FLOAT)
            return v_float(to_f(a) + to_f(b));
        return v_int(a.u.i + b.u.i);
    }
    if (a.tag == T_STR && b.tag == T_STR) {
        Str *x = AS_STR(a), *y = AS_STR(b);
        Str *o = kmalloc(sizeof(Str) + (size_t)(x->len + y->len) + 1);
        o->len = x->len + y->len;
        km_memcpy(o->data, x->data, (size_t)x->len);
        km_memcpy(o->data + x->len, y->data, (size_t)y->len);
        o->data[o->len] = '\0';
        return (Val){T_STR, {.p = o}};
    }
    if (a.tag == T_LIST && b.tag == T_LIST) {
        List *x = AS_LIST(a), *y = AS_LIST(b);
        Val r = v_list();
        List *o = AS_LIST(r);
        list_grow(o, x->len + y->len);
        km_memcpy(o->items, x->items, sizeof(Val) * (size_t)x->len);
        km_memcpy(o->items + x->len, y->items, sizeof(Val) * (size_t)y->len);
        o->len = x->len + y->len;
        return r;
    }
    hs_err(line, "cannot add %s and %s", hs_tname(a), hs_tname(b));
}

static void need_nums(const char *op, Val a, Val b, int line) {
    if (!is_num(a) || !is_num(b))
        hs_err(line, "operator '%s' needs numbers, got %s and %s", op, hs_tname(a), hs_tname(b));
}

Val v_sub(Val a, Val b, int line) {
    need_nums("-", a, b, line);
    if (a.tag == T_FLOAT || b.tag == T_FLOAT)
        return v_float(to_f(a) - to_f(b));
    return v_int(a.u.i - b.u.i);
}

Val v_mul(Val a, Val b, int line) {
    need_nums("*", a, b, line);
    if (a.tag == T_FLOAT || b.tag == T_FLOAT)
        return v_float(to_f(a) * to_f(b));
    return v_int(a.u.i * b.u.i);
}

Val v_div(Val a, Val b, int line) {
    need_nums("/", a, b, line);
    if (to_f(b) == 0.0)
        hs_err(line, "division by zero");
    return v_float(to_f(a) / to_f(b));
}

static double d_floor(double x) {
    int64_t i = (int64_t)x;
    double d = (double)i;
    if (x < 0 && d != x)
        d -= 1.0;
    return d;
}

Val v_mod(Val a, Val b, int line) {
    need_nums("%", a, b, line);
    if (to_f(b) == 0.0)
        hs_err(line, "division by zero");
    if (a.tag == T_FLOAT || b.tag == T_FLOAT)
        return v_float(to_f(a) - d_floor(to_f(a) / to_f(b)) * to_f(b));
    int64_t r = a.u.i % b.u.i;
    if (r != 0 && ((r < 0) != (b.u.i < 0)))
        r += b.u.i;
    return v_int(r);
}

Val v_neg(Val v, int line) {
    if (v.tag == T_INT)
        return v_int(-v.u.i);
    if (v.tag == T_FLOAT)
        return v_float(-v.u.f);
    hs_err(line, "cannot negate %s", hs_tname(v));
}

Val v_not(Val v) { return v_bool(!v_truthy(v)); }

Val v_eq(Val a, Val b) {
    if (a.tag == T_INT && b.tag == T_INT)
        return v_bool(a.u.i == b.u.i);
    if (is_num(a) && is_num(b))
        return v_bool(to_f(a) == to_f(b));
    if (a.tag == T_STR && b.tag == T_STR) {
        Str *x = AS_STR(a), *y = AS_STR(b);
        return v_bool(x->len == y->len && km_memcmp(x->data, y->data, (size_t)x->len) == 0);
    }
    if (a.tag == T_BOOL && b.tag == T_BOOL)
        return v_bool(a.u.b == b.u.b);
    if (a.tag == T_NULL && b.tag == T_NULL)
        return v_bool(1);
    if (a.tag == T_LIST && b.tag == T_LIST) {
        List *x = AS_LIST(a), *y = AS_LIST(b);
        if (x->len != y->len)
            return v_bool(0);
        for (int64_t i = 0; i < x->len; i++)
            if (!v_truthy(v_eq(x->items[i], y->items[i])))
                return v_bool(0);
        return v_bool(1);
    }
    if (a.tag == T_DICT && b.tag == T_DICT) {
        Dict *x = AS_DICT(a), *y = AS_DICT(b);
        if (x->len != y->len)
            return v_bool(0);
        for (int64_t i = 0; i < x->len; i++) {
            int found = 0;
            for (int64_t j = 0; j < y->len; j++) {
                if (km_strcmp(x->keys[i], y->keys[j]) == 0) {
                    found = 1;
                    if (!v_truthy(v_eq(x->vals[i], y->vals[j])))
                        return v_bool(0);
                    break;
                }
            }
            if (!found)
                return v_bool(0);
        }
        return v_bool(1);
    }
    if (a.tag == T_FUNC && b.tag == T_FUNC)
        return v_bool(a.u.p == b.u.p);
    if (a.tag == T_FILE && b.tag == T_FILE)
        return v_bool(a.u.p == b.u.p);
    return v_bool(0);
}

Val v_ne(Val a, Val b) { return v_bool(!v_truthy(v_eq(a, b))); }

static int cmp_ord(Val a, Val b, int line, int *out) {
    if (is_num(a) && is_num(b)) {
        double x = to_f(a), y = to_f(b);
        *out = (x > y) - (x < y);
        return 1;
    }
    if (a.tag == T_STR && b.tag == T_STR) {
        Str *x = AS_STR(a), *y = AS_STR(b);
        int64_t n = x->len < y->len ? x->len : y->len;
        int c = km_memcmp(x->data, y->data, (size_t)n);
        if (c == 0)
            c = (x->len > y->len) - (x->len < y->len);
        *out = (c > 0) - (c < 0);
        return 1;
    }
    hs_err(line, "cannot compare %s and %s", hs_tname(a), hs_tname(b));
    return 0;
}

Val v_lt(Val a, Val b, int line) {
    int c;
    cmp_ord(a, b, line, &c);
    return v_bool(c < 0);
}
Val v_gt(Val a, Val b, int line) {
    int c;
    cmp_ord(a, b, line, &c);
    return v_bool(c > 0);
}
Val v_le(Val a, Val b, int line) {
    int c;
    cmp_ord(a, b, line, &c);
    return v_bool(c <= 0);
}
Val v_ge(Val a, Val b, int line) {
    int c;
    cmp_ord(a, b, line, &c);
    return v_bool(c >= 0);
}

// ---------- access ----------
Val v_index(Val obj, Val idx, int line) {
    if (obj.tag == T_LIST) {
        if (idx.tag != T_INT)
            hs_err(line, "index must be Int");
        List *l = AS_LIST(obj);
        int64_t i = idx.u.i;
        if (i < 0)
            i += l->len;
        if (i < 0 || i >= l->len)
            hs_err(line, "index out of range");
        return l->items[i];
    }
    if (obj.tag == T_STR) {
        if (idx.tag != T_INT)
            hs_err(line, "index must be Int");
        Str *s = AS_STR(obj);
        int64_t i = idx.u.i;
        if (i < 0)
            i += s->len;
        if (i < 0 || i >= s->len)
            hs_err(line, "index out of range");
        return v_strn(s->data + i, 1);
    }
    if (obj.tag == T_DICT) {
        if (idx.tag != T_STR)
            hs_err(line, "dict key must be Str");
        Dict *d = AS_DICT(obj);
        const char *k = AS_STR(idx)->data;
        for (int64_t i = 0; i < d->len; i++)
            if (km_strcmp(d->keys[i], k) == 0)
                return d->vals[i];
        hs_err(line, "key '%s' not found", k);
    }
    hs_err(line, "cannot index %s", hs_tname(obj));
}

void v_setindex(Val obj, Val idx, Val v, int line) {
    if (obj.tag == T_LIST) {
        if (idx.tag != T_INT)
            hs_err(line, "index must be Int");
        List *l = AS_LIST(obj);
        int64_t i = idx.u.i;
        if (i < 0)
            i += l->len;
        if (i < 0 || i >= l->len)
            hs_err(line, "index out of range");
        l->items[i] = v;
        return;
    }
    if (obj.tag == T_DICT) {
        if (idx.tag != T_STR)
            hs_err(line, "dict key must be Str");
        Dict *d = AS_DICT(obj);
        const char *k = AS_STR(idx)->data;
        for (int64_t i = 0; i < d->len; i++) {
            if (km_strcmp(d->keys[i], k) == 0) {
                d->vals[i] = v;
                return;
            }
        }
        dict_grow(d);
        size_t kl = km_strlen(k);
        char *kc = kmalloc(kl + 1);
        km_memcpy(kc, k, kl + 1);
        d->keys[d->len] = kc;
        d->vals[d->len] = v;
        d->len++;
        return;
    }
    hs_err(line, "cannot assign into %s", hs_tname(obj));
}

Val v_call(Val fn, Val *args, int nargs, int line) {
    if (fn.tag == T_FUNC) {
        Func *f = AS_FUNC(fn);
        if (nargs != f->arity)
            hs_err(line, "%s wants %d args, got %d", f->name, f->arity, nargs);
        return f->fn(args, nargs, line);
    }
    if (fn.tag == T_BUILTIN)
        return ((Builtin *)fn.u.p)->fn(args, nargs, line);
    hs_err(line, "not callable: %s", hs_tname(fn));
}

Val v_seq(Val v, int line) {
    if (v.tag == T_LIST)
        return v;
    if (v.tag == T_DICT) {
        Dict *d = AS_DICT(v);
        Val r = v_list();
        List *o = AS_LIST(r);
        list_grow(o, d->len);
        for (int64_t i = 0; i < d->len; i++)
            o->items[i] = v_str(d->keys[i]);
        o->len = d->len;
        return r;
    }
    if (v.tag == T_STR) {
        Str *s = AS_STR(v);
        Val r = v_list();
        List *o = AS_LIST(r);
        list_grow(o, s->len);
        for (int64_t i = 0; i < s->len; i++)
            o->items[i] = v_strn(s->data + i, 1);
        o->len = s->len;
        return r;
    }
    hs_err(line, "not iterable: %s", hs_tname(v));
}

// ---------- display ----------
static char *kitoa(int64_t v) {
    char rev[24];
    int j = 0, neg = 0;
    if (v < 0) {
        neg = 1;
        v = -v;
    }
    if (v == 0)
        rev[j++] = '0';
    while (v > 0) {
        rev[j++] = '0' + (v % 10);
        v /= 10;
    }
    char *o = kmalloc((size_t)(j + neg + 1));
    int i = 0;
    if (neg)
        o[i++] = '-';
    while (j > 0)
        o[i++] = rev[--j];
    o[i] = 0;
    return o;
}

static char *kftoa(double f) {
    if (f != f)
        return "nan";
    int neg = f < 0;
    if (neg)
        f = -f;
    if (f >= 9007199254740992.0)
        return "<bigfloat>";
    int64_t ip = (int64_t)f;
    int64_t fp = (int64_t)((f - (double)ip) * 1000000.0 + 0.5);
    if (fp >= 1000000) {
        ip += 1;
        fp -= 1000000;
    }
    char *o = kmalloc(48);
    int i = 0;
    if (neg)
        o[i++] = '-';
    char *is = kitoa(ip);
    for (char *p = is; *p; p++)
        o[i++] = *p;
    o[i++] = '.';
    if (fp == 0) {
        o[i++] = '0';
    } else {
        char dig[6];
        for (int k = 5; k >= 0; k--) {
            dig[k] = '0' + (fp % 10);
            fp /= 10;
        }
        int end = 6;
        while (end > 0 && dig[end - 1] == '0')
            end--;
        for (int k = 0; k < end; k++)
            o[i++] = dig[k];
    }
    o[i] = 0;
    return o;
}

const char *v_disp(Val v) {
    switch (v.tag) {
    case T_NULL:
        return "null";
    case T_UNBOUND:
        return "<unbound>";
    case T_BOOL:
        return v.u.b ? "true" : "false";
    case T_INT:
        return kitoa(v.u.i);
    case T_FLOAT:
        return kftoa(v.u.f);
    case T_STR:
        return AS_STR(v)->data;
    case T_LIST: {
        List *l = AS_LIST(v);
        size_t cap = 64, n = 0;
        char *buf = kmalloc(cap);
        buf[n++] = '[';
        for (int64_t i = 0; i < l->len; i++) {
            if (i > 0) {
                while (n + 2 >= cap) {
                    size_t oc = cap;
                    cap *= 2;
                    char *nb = kmalloc(cap);
                    km_memcpy(nb, buf, oc);
                    buf = nb;
                }
                buf[n++] = ',';
                buf[n++] = ' ';
            }
            const char *s = v_disp(l->items[i]);
            size_t sl = km_strlen(s);
            while (n + sl + 2 >= cap) {
                size_t oc = cap;
                cap *= 2;
                char *nb = kmalloc(cap);
                km_memcpy(nb, buf, oc);
                buf = nb;
            }
            km_memcpy(buf + n, s, sl);
            n += sl;
        }
        while (n + 2 >= cap) {
            size_t oc = cap;
            cap += 2;
            char *nb = kmalloc(cap);
            km_memcpy(nb, buf, oc);
            buf = nb;
        }
        buf[n++] = ']';
        buf[n] = '\0';
        return buf;
    }
    case T_DICT: {
        Dict *d = AS_DICT(v);
        size_t cap = 64, n = 0;
        char *buf = kmalloc(cap);
        buf[n++] = '{';
        for (int64_t i = 0; i < d->len; i++) {
            if (i > 0) {
                while (n + 2 >= cap) {
                    size_t oc = cap;
                    cap *= 2;
                    char *nb = kmalloc(cap);
                    km_memcpy(nb, buf, oc);
                    buf = nb;
                }
                buf[n++] = ',';
                buf[n++] = ' ';
            }
            const char *s = v_disp(d->vals[i]);
            size_t kl = km_strlen(d->keys[i]), sl = km_strlen(s);
            while (n + kl + sl + 4 >= cap) {
                size_t oc = cap;
                cap *= 2;
                char *nb = kmalloc(cap);
                km_memcpy(nb, buf, oc);
                buf = nb;
            }
            km_memcpy(buf + n, d->keys[i], kl);
            n += kl;
            buf[n++] = ':';
            buf[n++] = ' ';
            km_memcpy(buf + n, s, sl);
            n += sl;
        }
        while (n + 2 >= cap) {
            size_t oc = cap;
            cap += 2;
            char *nb = kmalloc(cap);
            km_memcpy(nb, buf, oc);
            buf = nb;
        }
        buf[n++] = '}';
        buf[n] = '\0';
        return buf;
    }
    case T_FUNC: {
        char *o = kmalloc(64);
        const char *nm = AS_FUNC(v)->name;
        size_t i = 0;
        const char *pre = "<func ";
        while (*pre)
            o[i++] = *pre++;
        while (*nm)
            o[i++] = *nm++;
        o[i++] = '>';
        o[i] = 0;
        return o;
    }
    case T_FILE:
        return "<file>";
    case T_BUILTIN: {
        char *o = kmalloc(64);
        const char *nm = ((Builtin *)v.u.p)->name;
        size_t i = 0;
        const char *pre = "<builtin ";
        while (*pre)
            o[i++] = *pre++;
        while (*nm)
            o[i++] = *nm++;
        o[i++] = '>';
        o[i] = 0;
        return o;
    }
    default:
        return "?";
    }
}

// ---------- builtins ----------
Val b_print(Val *args, int nargs, int line) {
    (void)line;
    for (int i = 0; i < nargs; i++) {
        if (i > 0) {
            serial_putc(' ');
            vga_putc(' ');
        }
        kputs(v_disp(args[i]));
    }
    serial_putc('\n');
    vga_putc('\n');
    return v_null();
}

Val b_len(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "len wants 1 arg, got %d", nargs);
    Val a = args[0];
    if (a.tag == T_STR)
        return v_int(AS_STR(a)->len);
    if (a.tag == T_LIST)
        return v_int(AS_LIST(a)->len);
    if (a.tag == T_DICT)
        return v_int(AS_DICT(a)->len);
    hs_err(line, "len of %s", hs_tname(a));
}

Val b_range(Val *args, int nargs, int line) {
    int64_t lo = 0, hi = 0;
    if (nargs == 1 && args[0].tag == T_INT) {
        hi = args[0].u.i;
    } else if (nargs == 2 && args[0].tag == T_INT && args[1].tag == T_INT) {
        lo = args[0].u.i;
        hi = args[1].u.i;
    } else {
        hs_err(line, "range wants range(n) or range(a, b) with Ints");
    }
    Val r = v_list();
    List *o = AS_LIST(r);
    int64_t n = hi > lo ? hi - lo : 0;
    if (n > 0) {
        list_grow(o, n);
        for (int64_t i = 0; i < n; i++)
            o->items[i] = v_int(lo + i);
        o->len = n;
    }
    return r;
}

Val b_str(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "str wants 1 arg, got %d", nargs);
    return v_str(v_disp(args[0]));
}

static int k_isspace(char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r';
}

static int64_t kstrtoll(const char *s, const char **end, int base, int *ok) {
    while (k_isspace(*s))
        s++;
    int neg = 0;
    if (*s == '+' || *s == '-') {
        neg = *s == '-';
        s++;
    }
    if (base == 0) {
        base = 10;
        if (s[0] == '0' && (s[1] == 'x' || s[1] == 'X')) {
            base = 16;
            s += 2;
        }
    }
    uint64_t v = 0;
    int any = 0;
    while (*s) {
        int d;
        if (*s >= '0' && *s <= '9')
            d = *s - '0';
        else if (*s >= 'a' && *s <= 'f')
            d = *s - 'a' + 10;
        else if (*s >= 'A' && *s <= 'F')
            d = *s - 'A' + 10;
        else
            break;
        if (d >= base)
            break;
        v = v * (uint64_t)base + (uint64_t)d;
        any = 1;
        s++;
    }
    *end = s;
    *ok = any;
    if (neg)
        return -(int64_t)v;
    return (int64_t)v;
}

Val b_int(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "int wants 1 arg, got %d", nargs);
    Val a = args[0];
    if (a.tag == T_BOOL)
        return v_int(a.u.b);
    if (a.tag == T_INT)
        return a;
    if (a.tag == T_FLOAT)
        return v_int((int64_t)a.u.f);
    if (a.tag == T_STR) {
        const char *s = AS_STR(a)->data;
        const char *end = s;
        int ok = 0;
        int64_t v = kstrtoll(s, &end, 10, &ok);
        if (!ok) {
            end = s;
            v = kstrtoll(s, &end, 0, &ok);
            if (!ok)
                hs_err(line, "cannot convert '%s' to Int", AS_STR(a)->data);
        }
        while (k_isspace(*end))
            end++;
        if (*end != '\0')
            hs_err(line, "cannot convert '%s' to Int", AS_STR(a)->data);
        return v_int(v);
    }
    hs_err(line, "cannot convert %s to Int", hs_tname(a));
}

static double kstrtod(const char *s, const char **end, int *ok) {
    while (k_isspace(*s))
        s++;
    int neg = 0;
    if (*s == '+' || *s == '-') {
        neg = *s == '-';
        s++;
    }
    double v = 0;
    int any = 0;
    while (*s >= '0' && *s <= '9') {
        v = v * 10 + (*s - '0');
        any = 1;
        s++;
    }
    if (*s == '.') {
        s++;
        double m = 0.1;
        while (*s >= '0' && *s <= '9') {
            v += (*s - '0') * m;
            m *= 0.1;
            any = 1;
            s++;
        }
    }
    if (any && (*s == 'e' || *s == 'E')) {
        const char *p = s + 1;
        int eneg = 0;
        if (*p == '+' || *p == '-') {
            eneg = *p == '-';
            p++;
        }
        int e = 0, eany = 0;
        while (*p >= '0' && *p <= '9') {
            e = e * 10 + (*p - '0');
            eany = 1;
            p++;
        }
        if (eany) {
            s = p;
            while (e-- > 0)
                v = eneg ? v / 10.0 : v * 10.0;
        }
    }
    *end = s;
    *ok = any;
    return neg ? -v : v;
}

Val b_float(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "float wants 1 arg, got %d", nargs);
    Val a = args[0];
    if (a.tag == T_BOOL)
        return v_float(a.u.b);
    if (a.tag == T_INT)
        return v_float((double)a.u.i);
    if (a.tag == T_FLOAT)
        return a;
    if (a.tag == T_STR) {
        const char *end = AS_STR(a)->data;
        int ok = 0;
        double v = kstrtod(AS_STR(a)->data, &end, &ok);
        if (!ok)
            hs_err(line, "cannot convert '%s' to Float", AS_STR(a)->data);
        return v_float(v);
    }
    hs_err(line, "cannot convert %s to Float", hs_tname(a));
}

Val b_input(Val *args, int nargs, int line) {
    (void)args;
    (void)nargs;
    hs_err(line, "input needs an OS (not available in kernel)");
}

Val b_open(Val *args, int nargs, int line) {
    (void)args;
    (void)nargs;
    hs_err(line, "files need an OS (not available in kernel)");
}

Val b_read(Val *args, int nargs, int line) {
    (void)args;
    (void)nargs;
    hs_err(line, "files need an OS (not available in kernel)");
}

Val b_write(Val *args, int nargs, int line) {
    (void)args;
    (void)nargs;
    hs_err(line, "files need an OS (not available in kernel)");
}

Val b_close(Val *args, int nargs, int line) {
    (void)args;
    (void)nargs;
    hs_err(line, "files need an OS (not available in kernel)");
}

// ---------- unsafe (kernel: real memory via kmalloc) ----------
uint8_t *hs_alloc(int64_t n, int line) {
    if (n < 0)
        hs_err(line, "alloc of negative size %lld", (long long)n);
    size_t m = ((size_t)n + 7) & ~(size_t)7;
    uint8_t *p = kmalloc(m ? m : 8);
    km_memset(p, 0, m);
    return p;
}

static void hs_ptr_check(uint8_t *p, int line) {
    if (!p)
        hs_err(line, "null pointer dereference");
}

int64_t hs_ld64(uint8_t *p, int line) {
    hs_ptr_check(p, line);
    if ((uintptr_t)p % 8 != 0)
        hs_err(line, "unaligned 64-bit access (use load8/load32)");
    int64_t v;
    km_memcpy(&v, p, 8);
    return v;
}

void hs_st64(uint8_t *p, int64_t v, int line) {
    hs_ptr_check(p, line);
    if ((uintptr_t)p % 8 != 0)
        hs_err(line, "unaligned 64-bit access (use load8/load32)");
    km_memcpy(p, &v, 8);
}

int64_t hs_load8(uint8_t *p, int line) {
    hs_ptr_check(p, line);
    return (int64_t)*p;
}

int64_t hs_load32(uint8_t *p, int line) {
    hs_ptr_check(p, line);
    uint32_t v;
    km_memcpy(&v, p, 4);
    return (int64_t)v;
}

int64_t hs_store8(uint8_t *p, int64_t v, int line) {
    hs_ptr_check(p, line);
    *p = (uint8_t)(v & 0xFF);
    return v & 0xFF;
}

int64_t hs_store32(uint8_t *p, int64_t v, int line) {
    hs_ptr_check(p, line);
    uint32_t w = (uint32_t)(v & 0xFFFFFFFF);
    km_memcpy(p, &w, 4);
    return (int64_t)w;
}

int64_t hs_unbox_I64(Val v, int line) {
    if (v.tag == T_INT)
        return v.u.i;
    if (v.tag == T_BOOL)
        return v.u.b;
    hs_err(line, "cannot use %s as I64", hs_tname(v));
}

uint64_t hs_unbox_U64(Val v, int line) {
    if (v.tag == T_INT && v.u.i >= 0)
        return (uint64_t)v.u.i;
    if (v.tag == T_BOOL)
        return (uint64_t)v.u.b;
    hs_err(line, "cannot use %s as U64", hs_tname(v));
}

uint8_t *hs_unbox_Ptr(Val v, int line) {
    if (v.tag == T_INT && v.u.i >= 0)
        return (uint8_t *)(uintptr_t)(uint64_t)v.u.i;
    if (v.tag == T_BOOL)
        return (uint8_t *)(uintptr_t)(uint64_t)v.u.b;
    hs_err(line, "cannot use %s as Ptr", hs_tname(v));
}

Val hs_box_U64(uint64_t v, int line) {
    if (v > (uint64_t)INT64_MAX)
        hs_err(line, "U64 value too large for Int");
    return v_int((int64_t)v);
}

static int64_t k_addr_arg(Val a, const char *name, int line) {
    int64_t p = -1;
    if (a.tag == T_INT)
        p = a.u.i;
    else if (a.tag == T_BOOL)
        p = a.u.b;
    else
        hs_err(line, "%s needs Int, got %s", name, hs_tname(a));
    if (p < 0)
        hs_err(line, "negative address");
    return p;
}

static int64_t k_int_arg(Val a, const char *name, int line) {
    if (a.tag == T_INT)
        return a.u.i;
    if (a.tag == T_BOOL)
        return a.u.b;
    hs_err(line, "%s needs Int, got %s", name, hs_tname(a));
}

Val b_alloc(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "alloc arg count mismatch");
    int64_t n = k_int_arg(args[0], "alloc", line);
    return v_int((int64_t)(uintptr_t)hs_alloc(n, line));
}

Val b_load8(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "load8 arg count mismatch");
    int64_t p = k_addr_arg(args[0], "load8", line);
    return v_int(hs_load8((uint8_t *)(uintptr_t)(uint64_t)p, line));
}

Val b_load32(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "load32 arg count mismatch");
    int64_t p = k_addr_arg(args[0], "load32", line);
    return v_int(hs_load32((uint8_t *)(uintptr_t)(uint64_t)p, line));
}

Val b_store8(Val *args, int nargs, int line) {
    if (nargs != 2)
        hs_err(line, "store8 arg count mismatch");
    int64_t p = k_addr_arg(args[0], "store8", line);
    int64_t v = k_int_arg(args[1], "store8", line);
    return v_int(hs_store8((uint8_t *)(uintptr_t)(uint64_t)p, v, line));
}

Val b_store32(Val *args, int nargs, int line) {
    if (nargs != 2)
        hs_err(line, "store32 arg count mismatch");
    int64_t p = k_addr_arg(args[0], "store32", line);
    int64_t v = k_int_arg(args[1], "store32", line);
    return v_int(hs_store32((uint8_t *)(uintptr_t)(uint64_t)p, v, line));
}

Val b_as_ptr(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "as_ptr arg count mismatch");
    int64_t v = k_int_arg(args[0], "as_ptr", line);
    if (v < 0)
        hs_err(line, "negative value %lld as Ptr", (long long)v);
    return v_int(v);
}

Val b_as_int(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "as_int arg count mismatch");
    return v_int(k_int_arg(args[0], "as_int", line));
}

Val v_builtin(const char *name) {
    static Builtin tab[] = {
        {b_print, "print"}, {b_len, "len"}, {b_range, "range"},
        {b_str, "str"}, {b_int, "int"}, {b_float, "float"},
        {b_input, "input"}, {b_open, "open"}, {b_read, "read"},
        {b_write, "write"}, {b_close, "close"},
        {b_alloc, "alloc"}, {b_load8, "load8"}, {b_load32, "load32"},
        {b_store8, "store8"}, {b_store32, "store32"},
        {b_as_ptr, "as_ptr"}, {b_as_int, "as_int"},
        {b_ticks, "ticks"}, {b_readkey, "readkey"},
        {b_pmm_alloc, "pmm_alloc"}, {b_meminfo, "meminfo"},
    };
    for (unsigned i = 0; i < sizeof(tab) / sizeof(tab[0]); i++)
        if (km_strcmp(tab[i].name, name) == 0)
            return (Val){T_BUILTIN, {.p = &tab[i]}};
    return v_unbound();
}

void v_push(Val list, Val v, int line) {
    if (list.tag != T_LIST)
        hs_err(line, "v_push on %s", hs_tname(list));
    List *o = AS_LIST(list);
    list_grow(o, o->len + 1);
    o->items[o->len++] = v;
}

// ---------- IDT (64-bit interrupt gates, DPL0) ----------
struct __attribute__((packed)) IdtEnt {
    uint16_t off_lo;
    uint16_t sel;
    uint8_t ist;
    uint8_t attr;
    uint16_t off_mid;
    uint32_t off_hi;
    uint32_t zero;
};

struct __attribute__((packed)) Idtr {
    uint16_t lim;
    uint64_t base;
};

static struct IdtEnt hs_idt[256];

static void idt_gate(int n, void *addr) {
    uint64_t a = (uint64_t)addr;
    hs_idt[n].off_lo = a & 0xFFFF;
    hs_idt[n].sel = 0x08;
    hs_idt[n].ist = 0;
    hs_idt[n].attr = 0x8E;
    hs_idt[n].off_mid = (a >> 16) & 0xFFFF;
    hs_idt[n].off_hi = (uint32_t)(a >> 32);
    hs_idt[n].zero = 0;
}

#define DECL_EXC(n) extern void hs_exc##n(void)
DECL_EXC(0); DECL_EXC(1); DECL_EXC(2); DECL_EXC(3);
DECL_EXC(4); DECL_EXC(5); DECL_EXC(6); DECL_EXC(7);
DECL_EXC(8); DECL_EXC(9); DECL_EXC(10); DECL_EXC(11);
DECL_EXC(12); DECL_EXC(13); DECL_EXC(14); DECL_EXC(15);
DECL_EXC(16); DECL_EXC(17); DECL_EXC(18); DECL_EXC(19);
DECL_EXC(20); DECL_EXC(21); DECL_EXC(22); DECL_EXC(23);
DECL_EXC(24); DECL_EXC(25); DECL_EXC(26); DECL_EXC(27);
DECL_EXC(28); DECL_EXC(29); DECL_EXC(30); DECL_EXC(31);
extern void hs_irq0_stub(void);
extern void hs_irq1_stub(void);

static void idt_init(void) {
    void *exc[] = {
        hs_exc0, hs_exc1, hs_exc2, hs_exc3,
        hs_exc4, hs_exc5, hs_exc6, hs_exc7,
        hs_exc8, hs_exc9, hs_exc10, hs_exc11,
        hs_exc12, hs_exc13, hs_exc14, hs_exc15,
        hs_exc16, hs_exc17, hs_exc18, hs_exc19,
        hs_exc20, hs_exc21, hs_exc22, hs_exc23,
        hs_exc24, hs_exc25, hs_exc26, hs_exc27,
        hs_exc28, hs_exc29, hs_exc30, hs_exc31,
    };
    for (int i = 0; i < 32; i++)
        idt_gate(i, exc[i]);
    idt_gate(32, hs_irq0_stub);
    idt_gate(33, hs_irq1_stub);
    struct Idtr idtr = {sizeof(hs_idt) - 1, (uint64_t)hs_idt};
    __asm__ volatile("lidt %0" : : "m"(idtr));
}

void hs_exc_c(uint64_t vec, uint64_t err, uint64_t rip) {
    kputs("EXC ");
    kputu(vec);
    kputs(" err=");
    kputu(err);
    kputs(" rip=0x");
    kputx(rip);
    kputs("\n");
    khalt();
}

// ---------- PIC 8259 + PIT ----------
// IRQ0 (timer) -> vec 32, IRQ1 (keyboard) -> vec 33
static void pic_init(void) {
    km_outb(0x20, 0x11);
    km_outb(0xA0, 0x11);
    km_outb(0x21, 0x20);
    km_outb(0xA1, 0x28);
    km_outb(0x21, 0x04);
    km_outb(0xA1, 0x02);
    km_outb(0x21, 0x01);
    km_outb(0xA1, 0x01);
    km_outb(0x21, 0xF8);  // unmask cascade + timer + keyboard
    km_outb(0xA1, 0xFF);
}

static void pit_init_hz(int hz) {
    int div = 1193182 / hz;
    km_outb(0x43, 0x36);
    km_outb(0x40, div & 0xFF);
    km_outb(0x40, (div >> 8) & 0xFF);
}

volatile uint64_t hs_ticks = 0;

void hs_irq0(void) {
    hs_ticks++;
    km_outb(0x20, 0x20);
}

// ---------- keyboard: AT set 1 (no shift), 256-byte ring ----------
static char kbd_buf[256];
static int kbd_head, kbd_tail;

static char sc_to_ascii(uint8_t sc) {
    static const char *rows[4] = {
        "1234567890-=",
        "qwertyuiop[]",
        "asdfghjkl;'",
        "zxcvbnm,./",
    };
    static const uint8_t codes[4][12] = {
        {0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D},
        {0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x1B},
        {0x1E, 0x1F, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0},
        {0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0},
    };
    if (sc == 0x39)
        return ' ';
    if (sc == 0x1C)
        return '\n';
    if (sc == 0x0E)
        return '\b';
    for (int r = 0; r < 4; r++)
        for (int c = 0; c < 12 && codes[r][c]; c++)
            if (codes[r][c] == sc)
                return rows[r][c];
    return 0;
}

void hs_irq1(uint64_t scancode) {
    uint8_t sc = (uint8_t)scancode;
    if (!(sc & 0x80)) {
        char c = sc_to_ascii(sc);
        if (c) {
            int nxt = (kbd_head + 1) % 256;
            if (nxt != kbd_tail) {
                kbd_buf[kbd_head] = c;
                kbd_head = nxt;
            }
        }
    }
    km_outb(0x20, 0x20);
}

// ---------- PMM: bitmap over [0, top), 4K pages ----------
#define PGSZ 4096
static uint64_t pmm_total, pmm_free, pmm_top;
static uint8_t *pmm_bits;

static void pmm_mark(uint64_t addr, int used) {
    uint64_t pg = addr / PGSZ;
    if (used)
        pmm_bits[pg / 8] |= (uint8_t)(1 << (pg % 8));
    else
        pmm_bits[pg / 8] &= (uint8_t)~(1 << (pg % 8));
}

static int pmm_test(uint64_t pg) {
    return (pmm_bits[pg / 8] >> (pg % 8)) & 1;
}

static void pmm_range(uint64_t base, uint64_t len, int used) {
    if (len == 0)
        return;
    uint64_t lo = base & ~(uint64_t)4095;
    uint64_t hi = (base + len + PGSZ - 1) & ~(uint64_t)4095;
    if (hi > pmm_top)
        hi = pmm_top;
    for (uint64_t a = lo; a < hi; a += PGSZ) {
        uint64_t pg = a / PGSZ;
        int was = pmm_test(pg);
        pmm_mark(a, used);
        if (was && !used)
            pmm_free++;
        else if (!was && used && pmm_free > 0)
            pmm_free--;
    }
}

static void pmm_init(uint32_t magic, uint32_t info) {
    // default: 128MB (QEMU default) capped at identity-mapped 1GB
    uint64_t top = 128ULL * 1024 * 1024;
    pmm_top = top;
    uint64_t npages = top / PGSZ;
    pmm_total = npages;
    pmm_free = npages;
    pmm_bits = kmalloc((size_t)((npages + 7) / 8));
    km_memset(pmm_bits, 0, (size_t)((npages + 7) / 8));

    int have_map = 0;
    if (magic == 0x36D76289) {
        // multiboot2: tags
        uint32_t total = *(volatile uint32_t *)(uintptr_t)info;
        uint32_t off = 8;
        while (off < total) {
            uint32_t type = *(volatile uint32_t *)(uintptr_t)(info + off);
            uint32_t size = *(volatile uint32_t *)(uintptr_t)(info + off + 4);
            if (type == 0)
                break;
            if (type == 6) {
                uint32_t esz = *(volatile uint32_t *)(uintptr_t)(info + off + 8);
                uint32_t eoff = off + 16;
                while (eoff < off + size) {
                    uint64_t base = *(volatile uint64_t *)(uintptr_t)(info + eoff);
                    uint64_t len = *(volatile uint64_t *)(uintptr_t)(info + eoff + 8);
                    uint32_t mtype = *(volatile uint32_t *)(uintptr_t)(info + eoff + 16);
                    if (mtype == 1 && !have_map) {
                        // first usable region defines the map; start all-used
                        for (uint64_t p = 0; p < npages; p++)
                            if (!pmm_test(p)) {
                                pmm_mark(p * PGSZ, 1);
                                pmm_free--;
                            }
                        have_map = 1;
                    }
                    if (have_map && mtype == 1)
                        pmm_range(base, len, 0);
                    eoff += esz;
                }
            }
            off += (size + 7) & ~7u;
        }
    } else if (magic == 0x2BADB002) {
        // multiboot1
        uint32_t flags = *(volatile uint32_t *)(uintptr_t)info;
        if (flags & (1u << 6)) {
            uint32_t mmap = *(volatile uint32_t *)(uintptr_t)(info + 48);
            uint32_t mlen = *(volatile uint32_t *)(uintptr_t)(info + 44);
            uint32_t eoff = 0;
            while (eoff < mlen) {
                uint32_t esz = *(volatile uint32_t *)(uintptr_t)(mmap + eoff);
                uint64_t base = *(volatile uint64_t *)(uintptr_t)(mmap + eoff + 4);
                uint64_t len = *(volatile uint64_t *)(uintptr_t)(mmap + eoff + 12);
                uint32_t mtype = *(volatile uint32_t *)(uintptr_t)(mmap + eoff + 20);
                if (mtype == 1 && !have_map) {
                    for (uint64_t p = 0; p < npages; p++)
                        if (!pmm_test(p)) {
                            pmm_mark(p * PGSZ, 1);
                            pmm_free--;
                        }
                    have_map = 1;
                }
                if (have_map && mtype == 1)
                    pmm_range(base, len, 0);
                eoff += esz + 4;
            }
        }
        if (!have_map && (flags & 1)) {
            // fallback: mem_upper KB above 1MB
            uint32_t upper = *(volatile uint32_t *)(uintptr_t)(info + 8);
            uint64_t end = 0x100000ULL + (uint64_t)upper * 1024;
            if (end > top)
                end = top;
            for (uint64_t p = 0; p < npages; p++) {
                pmm_mark(p * PGSZ, 1);
            }
            pmm_free = 0;
            pmm_range(0x100000, end - 0x100000, 0);
            have_map = 1;
        }
    }
    // reserve low 1MB + kernel image/heap + bitmap itself
    pmm_range(0, 0x100000, 1);
    extern char hs_heap_end[];
    pmm_range(0x100000, (uint64_t)(uintptr_t)hs_heap_end - 0x100000, 1);
}

uint64_t pmm_alloc_pages(uint64_t n) {
    if (n == 0)
        return 0;
    uint64_t npages = pmm_top / PGSZ;
    for (uint64_t p = 0; p + n <= npages; p++) {
        uint64_t q;
        for (q = 0; q < n; q++)
            if (pmm_test(p + q))
                break;
        if (q == n) {
            for (q = 0; q < n; q++)
                pmm_mark((p + q) * PGSZ, 1);
            pmm_free -= n;
            uint64_t addr = p * PGSZ;
            km_memset((void *)(uintptr_t)addr, 0, (size_t)(n * PGSZ));
            return addr;
        }
    }
    return 0;
}

// ---------- new init + builtins ----------
void hs_kinit(uint32_t mb_magic, uint32_t mb_info) {
    serial_init();
    for (int i = 0; i < 80 * 25; i++)
        VGA[i] = 0x0720;
    vga_row = 0;
    vga_col = 0;
    idt_init();
    pic_init();
    pit_init_hz(100);
    pmm_init(mb_magic, mb_info);
    __asm__ volatile("sti");
}

Val b_ticks(Val *args, int nargs, int line) {
    if (nargs != 0)
        hs_err(line, "ticks takes no args");
    if (hs_ticks > (uint64_t)INT64_MAX)
        hs_err(line, "ticks overflow");
    return v_int((int64_t)hs_ticks);
}

Val b_readkey(Val *args, int nargs, int line) {
    if (nargs != 0)
        hs_err(line, "readkey takes no args");
    if (kbd_head == kbd_tail)
        return v_null();
    char c = kbd_buf[kbd_tail];
    kbd_tail = (kbd_tail + 1) % 256;
    return v_strn(&c, 1);
}

Val b_pmm_alloc(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_INT || args[0].u.i < 0)
        hs_err(line, "pmm_alloc wants pmm_alloc(npages)");
    uint64_t addr = pmm_alloc_pages((uint64_t)args[0].u.i);
    if (!addr)
        hs_err(line, "pmm_alloc: out of memory");
    return v_int((int64_t)addr);
}

Val b_meminfo(Val *args, int nargs, int line) {
    if (nargs != 0)
        hs_err(line, "meminfo takes no args");
    Val r = v_dict();
    Dict *d = AS_DICT(r);
    dict_grow(d);
    d->keys[0] = "total";
    d->vals[0] = v_int((int64_t)pmm_total);
    d->keys[1] = "free";
    d->vals[1] = v_int((int64_t)pmm_free);
    d->keys[2] = "page";
    d->vals[2] = v_int(4096);
    d->len = 3;
    return r;
}
