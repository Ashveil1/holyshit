// holyshit native runtime (เฟส 3a). Build: gcc rt.c prog.c -lgc
#include <gc.h>
#include <math.h>
#include <setjmp.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <dlfcn.h>
#include <errno.h>
#include <dirent.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>
#include <unistd.h>

#include "rt.h"

static int hs_init_done = 0;

static void hs_init(void) {
    if (!hs_init_done) {
        GC_INIT();
        hs_init_done = 1;
    }
}

__attribute__((constructor)) static void hs_ctor(void) { hs_init(); }

void hs_err(int line, const char *fmt, ...) {
    char buf[1024];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    if (hs_try_top) {
        // an enclosing try handles it: deliver to its frame, unwinding one level
        HSTry *f = hs_try_top;
        hs_try_top = f->prev;
        snprintf(f->msg, sizeof(f->msg), "%s", buf);
        f->line = line;
        longjmp(f->buf, 1);
    }
    fprintf(stderr, "error: %s at line %d\n", buf, line);
    exit(1);
}

// ---------- try/except ----------
HSTry *hs_try_top = NULL;

void hs_try_push(HSTry *f) {
    f->prev = hs_try_top;
    hs_try_top = f;
}

void hs_try_pop(void) {
    if (!hs_try_top)
        hs_err(-1, "try stack underflow");
    hs_try_top = hs_try_top->prev;
}

// ---------- constructors ----------
Val v_null(void) { return (Val){T_NULL, {0}}; }
Val v_bool(int b) { return (Val){T_BOOL, {.b = !!b}}; }
Val v_int(int64_t i) { return (Val){T_INT, {.i = i}}; }
Val v_float(double f) { return (Val){T_FLOAT, {.f = f}}; }

// float literals can overflow to inf (1e400) or be nan; neither has a
// portable C literal, so hand the raw bits over instead
double hs_f64raw(uint64_t bits) {
    union { uint64_t u; double d; } v;
    v.u = bits;
    return v.d;
}
Val v_unbound(void) { return (Val){T_UNBOUND, {0}}; }

Val v_strn(const char *s, int64_t n) {
    Str *o = GC_MALLOC(sizeof(Str) + (size_t)n + 1);
    o->len = n;
    memcpy(o->data, s, (size_t)n);
    o->data[n] = '\0';
    return (Val){T_STR, {.p = o}};
}

Val v_str(const char *s) { return v_strn(s, (int64_t)strlen(s)); }

Val v_list(void) {
    List *o = GC_MALLOC(sizeof(List));
    o->len = 0;
    o->cap = 4;
    o->items = GC_MALLOC(sizeof(Val) * (size_t)o->cap);
    return (Val){T_LIST, {.p = o}};
}

Val v_dict(void) {
    Dict *o = GC_MALLOC(sizeof(Dict));
    o->len = 0;
    o->cap = 4;
    o->keys = GC_MALLOC(sizeof(char *) * (size_t)o->cap);
    o->vals = GC_MALLOC(sizeof(Val) * (size_t)o->cap);
    return (Val){T_DICT, {.p = o}};
}

Val v_func(Val (*fn)(Val *, int, int), const char *name, int arity) {
    Func *o = GC_MALLOC(sizeof(Func));
    o->fn = fn;
    o->name = name;
    o->arity = arity;
    o->ncaps = 0;
    o->caps = NULL;
    return (Val){T_FUNC, {.p = o}};
}

void v_func_setcaps(Val fn, Val *caps, int n) {
    if (fn.tag != T_FUNC)
        hs_err(-1, "v_func_setcaps on non-function");
    Func *f = AS_FUNC(fn);
    Val *c = GC_MALLOC(sizeof(Val) * (size_t)(n > 0 ? n : 1));
    for (int i = 0; i < n; i++)
        c[i] = caps[i];
    f->caps = c;
    f->ncaps = n;
}

Val *hs_cur_caps = NULL;
int hs_cur_ncaps = 0;

// program arguments (set by generated main, without argv[0])
int hs_argc = 0;
char **hs_argv = NULL;

Val v_file(void *fp, const char *path) {
    File *o = GC_MALLOC(sizeof(File));
    o->fp = fp;
    o->path = GC_MALLOC(strlen(path) + 1);
    strcpy(o->path, path);
    o->closed = 0;
    return (Val){T_FILE, {.p = o}};
}

Val v_module(const char *name) {
    typedef struct Reg { const char *name; HsMod *mod; struct Reg *next; } Reg;
    static Reg *head = NULL;
    for (Reg *r = head; r; r = r->next)
        if (strcmp(r->name, name) == 0)
            return (Val){T_MOD, {.p = r->mod}};
    HsMod *o = GC_MALLOC(sizeof(HsMod));
    o->name = name;
    Reg *r = GC_MALLOC(sizeof(Reg));
    r->name = name;
    r->mod = o;
    r->next = head;
    head = r;
    return (Val){T_MOD, {.p = o}};
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
    case T_MOD:
        return "Module";
    case T_SOCK:
        return "Sock";
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
        Str *o = GC_MALLOC(sizeof(Str) + (size_t)(x->len + y->len) + 1);
        o->len = x->len + y->len;
        memcpy(o->data, x->data, (size_t)x->len);
        memcpy(o->data + x->len, y->data, (size_t)y->len);
        o->data[o->len] = '\0';
        return (Val){T_STR, {.p = o}};
    }
    if (a.tag == T_LIST && b.tag == T_LIST) {
        List *x = AS_LIST(a), *y = AS_LIST(b);
        Val r = v_list();
        List *o = AS_LIST(r);
        while (o->cap < x->len + y->len) {
            o->cap *= 2;
            o->items = GC_REALLOC(o->items, sizeof(Val) * (size_t)o->cap);
        }
        memcpy(o->items, x->items, sizeof(Val) * (size_t)x->len);
        memcpy(o->items + x->len, y->items, sizeof(Val) * (size_t)y->len);
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

Val v_mod(Val a, Val b, int line) {
    need_nums("%", a, b, line);
    if (to_f(b) == 0.0)
        hs_err(line, "division by zero");
    if (a.tag == T_FLOAT || b.tag == T_FLOAT)
        return v_float(to_f(a) - floor(to_f(a) / to_f(b)) * to_f(b));
    int64_t r = a.u.i % b.u.i;
    if (r != 0 && ((r < 0) != (b.u.i < 0)))
        r += b.u.i;
    return v_int(r);
}

static void need_ints(const char *op, Val a, Val b, int line) {
    // bitwise is Int-only (Bool is not an Int, matching interp)
    if (a.tag != T_INT || b.tag != T_INT)
        hs_err(line, "operator '%s' needs Ints, got %s and %s", op,
               hs_tname(a), hs_tname(b));
}

static int64_t shift_count(Val b, const char *op, int line) {
    need_ints(op, v_int(0), b, line);
    int64_t n = b.tag == T_INT ? b.u.i : b.u.b;
    if (n < 0 || n > 63)
        hs_err(line, "shift count %lld out of range (0..63)", (long long)n);
    return n;
}

Val v_and(Val a, Val b, int line) {
    need_ints("&", a, b, line);
    return v_int(a.u.i & b.u.i);
}

Val v_or(Val a, Val b, int line) {
    need_ints("|", a, b, line);
    return v_int(a.u.i | b.u.i);
}

Val v_xor(Val a, Val b, int line) {
    need_ints("^", a, b, line);
    return v_int(a.u.i ^ b.u.i);
}

Val v_shl(Val a, Val b, int line) {
    need_ints("<<", a, b, line);
    return v_int(a.u.i << shift_count(b, "<<", line));
}

Val v_shr(Val a, Val b, int line) {
    need_ints(">>", a, b, line);
    return v_int(a.u.i >> shift_count(b, ">>", line));  // arithmetic, like C
}

Val v_bnot(Val v, int line) {
    if (v.tag == T_INT)
        return v_int(~v.u.i);
    hs_err(line, "cannot bitwise-not %s", hs_tname(v));
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
        return v_bool(x->len == y->len && memcmp(x->data, y->data, (size_t)x->len) == 0);
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
                if (strcmp(x->keys[i], y->keys[j]) == 0) {
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
    if (a.tag == T_MOD && b.tag == T_MOD)
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
        int c = memcmp(x->data, y->data, (size_t)n);
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
            if (strcmp(d->keys[i], k) == 0)
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
            if (strcmp(d->keys[i], k) == 0) {
                d->vals[i] = v;
                return;
            }
        }
        if (d->len == d->cap) {
            d->cap *= 2;
            d->keys = GC_REALLOC(d->keys, sizeof(char *) * (size_t)d->cap);
            d->vals = GC_REALLOC(d->vals, sizeof(Val) * (size_t)d->cap);
        }
        char *kc = GC_MALLOC(strlen(k) + 1);
        strcpy(kc, k);
        d->keys[d->len] = kc;
        d->vals[d->len] = v;
        d->len++;
        return;
    }
    hs_err(line, "cannot assign into %s", hs_tname(obj));
}

Val v_slice(Val obj, Val start, Val stop, int line) {
    int64_t lo, hi, n;
    int has_lo = start.tag != T_NULL, has_hi = stop.tag != T_NULL;
    if (has_lo && start.tag != T_INT)
        hs_err(line, "slice index must be Int");
    if (has_hi && stop.tag != T_INT)
        hs_err(line, "slice index must be Int");
    if (obj.tag == T_LIST || obj.tag == T_STR) {
        n = (obj.tag == T_LIST) ? AS_LIST(obj)->len : AS_STR(obj)->len;
        lo = has_lo ? start.u.i : 0;
        hi = has_hi ? stop.u.i : n;
        if (lo < 0)
            lo += n;
        if (hi < 0)
            hi += n;
        if (lo < 0)
            lo = 0;
        if (lo > n)
            lo = n;
        if (hi < 0)
            hi = 0;
        if (hi > n)
            hi = n;
        if (obj.tag == T_LIST) {
            Val r = v_list();
            for (int64_t i = lo; i < hi; i++)
                v_push(r, AS_LIST(obj)->items[i], line);
            return r;
        }
        if (hi <= lo)
            return v_str("");
        return v_strn(AS_STR(obj)->data + lo, hi - lo);
    }
    hs_err(line, "cannot slice %s", hs_tname(obj));
}

void v_push(Val list, Val v, int line) {
    if (list.tag != T_LIST)
        hs_err(line, "v_push on %s", hs_tname(list));
    List *o = AS_LIST(list);
    if (o->len == o->cap) {
        o->cap *= 2;
        o->items = GC_REALLOC(o->items, sizeof(Val) * (size_t)o->cap);
    }
    o->items[o->len++] = v;
}

Val v_builtin(const char *name) {
    static Builtin tab[] = {
        {b_print, "print"}, {b_len, "len"}, {b_range, "range"},
        {b_str, "str"}, {b_int, "int"}, {b_float, "float"},
        {b_input, "input"}, {b_open, "open"}, {b_read, "read"},
        {b_write, "write"}, {b_close, "close"},
        {b_alloc, "alloc"}, {b_load8, "load8"}, {b_load32, "load32"},
        {b_load64, "load64"},
        {b_store8, "store8"}, {b_store32, "store32"}, {b_store64, "store64"},
        {b_as_ptr, "as_ptr"}, {b_as_int, "as_int"},
        {b_ticks, "ticks"}, {b_readkey, "readkey"},
        {b_pmm_alloc, "pmm_alloc"}, {b_meminfo, "meminfo"},
        {b_append, "append"}, {b_split, "split"},
        {b_find, "find"}, {b_join, "join"},
        {b_argv, "argv"}, {b_env, "env"}, {b_system, "system"},
        {b_tcp_connect, "tcp_connect"}, {b_tcp_send, "tcp_send"},
        {b_tcp_recv, "tcp_recv"}, {b_tcp_close, "tcp_close"},
        {b_tcp_listen, "tcp_listen"}, {b_tcp_accept, "tcp_accept"},
        {b_http_get, "http_get"},
        {b_json_parse, "json_parse"}, {b_json_str, "json_str"},
        {b_read_text, "read_text"}, {b_read_mem, "read_mem"},
        {b_write_text, "write_text"},
        {b_append_text, "append_text"}, {b_exists, "exists"},
        {b_ls, "ls"}, {b_mkdir, "mkdir"},
        {b_json_load, "json_load"}, {b_json_save, "json_save"},
    };
    for (unsigned i = 0; i < sizeof(tab) / sizeof(tab[0]); i++)
        if (strcmp(tab[i].name, name) == 0)
            return (Val){T_BUILTIN, {.p = &tab[i]}};
    return v_unbound();
}

Val v_call(Val fn, Val *args, int nargs, int line) {
    if (fn.tag == T_FUNC) {
        Func *f = AS_FUNC(fn);
        if (nargs != f->arity)
            hs_err(line, "%s wants %d args, got %d", f->name, f->arity, nargs);
        // install callee captures; save/restore (longjmp dirt is harmless:
        // every v_call sets before use, and try/except restores explicitly)
        Val *saved_caps = hs_cur_caps;
        int saved_n = hs_cur_ncaps;
        hs_cur_caps = f->caps;
        hs_cur_ncaps = f->ncaps;
        Val r = f->fn(args, nargs, line);
        hs_cur_caps = saved_caps;
        hs_cur_ncaps = saved_n;
        return r;
    }
    if (fn.tag == T_BUILTIN)
        return ((Builtin *)fn.u.p)->fn(args, nargs, line);
    hs_err(line, "not callable: %s", hs_tname(fn));
}

// ---------- dynamic module attributes ----------
typedef struct AttrReg {
    const char *mod, *name;
    Val *slot;
    struct AttrReg *next;
} AttrReg;

static AttrReg *hs_attr_head = NULL;

void hs_reg_attr(const char *mod, const char *name, Val *slot) {
    for (AttrReg *r = hs_attr_head; r; r = r->next)
        if (strcmp(r->mod, mod) == 0 && strcmp(r->name, name) == 0)
            return;
    AttrReg *r = GC_MALLOC(sizeof(AttrReg));
    r->mod = mod;
    r->name = name;
    r->slot = slot;
    r->next = hs_attr_head;
    hs_attr_head = r;
}

static Val *hs_find_attr(Val mod, const char *name, int line) {
    if (mod.tag != T_MOD)
        hs_err(line, "only modules have attributes");
    const char *mn = ((HsMod *)mod.u.p)->name;
    for (AttrReg *r = hs_attr_head; r; r = r->next)
        if (strcmp(r->mod, mn) == 0 && strcmp(r->name, name) == 0)
            return r->slot;
    hs_err(line, "module '%s' has no attribute '%s'", mn, name);
}

Val v_getattr(Val mod, const char *name, int line) {
    return *hs_find_attr(mod, name, line);
}

void v_setattr(Val mod, const char *name, Val v, int line) {
    *hs_find_attr(mod, name, line) = v;
}

Val v_seq(Val v, int line) {
    if (v.tag == T_LIST)
        return v;
    if (v.tag == T_DICT) {
        Dict *d = AS_DICT(v);
        Val r = v_list();
        List *o = AS_LIST(r);
        while (o->cap < d->len) {
            o->cap *= 2;
            o->items = GC_REALLOC(o->items, sizeof(Val) * (size_t)o->cap);
        }
        for (int64_t i = 0; i < d->len; i++)
            o->items[i] = v_str(d->keys[i]);
        o->len = d->len;
        return r;
    }
    if (v.tag == T_STR) {
        Str *s = AS_STR(v);
        Val r = v_list();
        List *o = AS_LIST(r);
        while (o->cap < s->len) {
            o->cap *= 2;
            o->items = GC_REALLOC(o->items, sizeof(Val) * (size_t)o->cap);
        }
        for (int64_t i = 0; i < s->len; i++)
            o->items[i] = v_strn(s->data + i, 1);
        o->len = s->len;
        return r;
    }
    hs_err(line, "not iterable: %s", hs_tname(v));
}

// ---------- display ----------

// repr() of a double: the shortest decimal string that reads back to the
// same bits, formatted like CPython (fixed while 10^-4 <= |x| < 10^16,
// ".0" kept so it still reads as a float, at least two exponent digits).
// A plain "%.17g" prints 17 digits for every inexact value, which is what
// interp/Python never do: 0.1 must be "0.1", not "0.10000000000000001".
static void fmt_repr(double x, char *out, size_t cap) {
    if (isnan(x)) {
        snprintf(out, cap, "%snan", signbit(x) ? "-" : "");
        return;
    }
    if (isinf(x)) {
        snprintf(out, cap, "%sinf", x < 0 ? "-" : "");
        return;
    }
    int neg = signbit(x);
    double a = neg ? -x : x;
    char buf[64], digits[24];
    int prec = 17;
    for (int p = 1; p <= 17; p++) {
        snprintf(buf, sizeof(buf), "%.*e", p - 1, a);
        if (strtod(buf, NULL) == a) {
            prec = p;
            break;
        }
    }
    snprintf(buf, sizeof(buf), "%.*e", prec - 1, a);
    char *ep = strchr(buf, 'e');
    int exp10 = atoi(ep + 1);
    int nd = 0;
    for (char *q = buf; q < ep; q++)
        if (*q != '.')
            digits[nd++] = *q;
    digits[nd] = 0;
    char *o = out;
    if (neg)
        *o++ = '-';
    if (exp10 >= -4 && exp10 <= 15) {
        if (exp10 >= 0) {
            for (int i = 0; i <= exp10; i++)
                *o++ = i < nd ? digits[i] : '0';
            *o++ = '.';
            if (nd > exp10 + 1) {
                memcpy(o, digits + exp10 + 1, nd - exp10 - 1);
                o += nd - exp10 - 1;
            } else {
                *o++ = '0';
            }
        } else {
            *o++ = '0';
            *o++ = '.';
            for (int i = 0; i < -exp10 - 1; i++)
                *o++ = '0';
            memcpy(o, digits, nd);
            o += nd;
        }
        *o = 0;
    } else {
        *o++ = digits[0];
        if (nd > 1) {
            *o++ = '.';
            memcpy(o, digits + 1, nd - 1);
            o += nd - 1;
        }
        *o = 0;
        snprintf(o, cap - (size_t)(o - out), "e%c%02d", exp10 < 0 ? '-' : '+',
                 exp10 < 0 ? -exp10 : exp10);
    }
}

const char *v_disp(Val v) {
    char tmp[64];
    switch (v.tag) {
    case T_NULL:
        return "null";
    case T_UNBOUND:
        return "<unbound>";
    case T_BOOL:
        return v.u.b ? "true" : "false";
    case T_INT:
        snprintf(tmp, sizeof(tmp), "%lld", (long long)v.u.i);
        break;
    case T_FLOAT:
        fmt_repr(v.u.f, tmp, sizeof(tmp));
        break;
    case T_STR:
        return AS_STR(v)->data;
    case T_LIST: {
        List *l = AS_LIST(v);
        size_t cap = 64, n = 0;
        char *buf = GC_MALLOC(cap);
        buf[n++] = '[';
        for (int64_t i = 0; i < l->len; i++) {
            if (i > 0) {
                if (n + 2 >= cap) {
                    cap *= 2;
                    buf = GC_REALLOC(buf, cap);
                }
                buf[n++] = ',';
                buf[n++] = ' ';
            }
            const char *s = v_disp(l->items[i]);
            size_t sl = strlen(s);
            while (n + sl + 2 >= cap) {
                cap *= 2;
                buf = GC_REALLOC(buf, cap);
            }
            memcpy(buf + n, s, sl);
            n += sl;
        }
        if (n + 2 >= cap) {
            cap += 2;
            buf = GC_REALLOC(buf, cap);
        }
        buf[n++] = ']';
        buf[n] = '\0';
        return buf;
    }
    case T_DICT: {
        Dict *d = AS_DICT(v);
        size_t cap = 64, n = 0;
        char *buf = GC_MALLOC(cap);
        buf[n++] = '{';
        for (int64_t i = 0; i < d->len; i++) {
            if (i > 0) {
                if (n + 2 >= cap) {
                    cap *= 2;
                    buf = GC_REALLOC(buf, cap);
                }
                buf[n++] = ',';
                buf[n++] = ' ';
            }
            const char *s = v_disp(d->vals[i]);
            size_t kl = strlen(d->keys[i]), sl = strlen(s);
            while (n + kl + sl + 4 >= cap) {
                cap *= 2;
                buf = GC_REALLOC(buf, cap);
            }
            memcpy(buf + n, d->keys[i], kl);
            n += kl;
            buf[n++] = ':';
            buf[n++] = ' ';
            memcpy(buf + n, s, sl);
            n += sl;
        }
        if (n + 2 >= cap) {
            cap += 2;
            buf = GC_REALLOC(buf, cap);
        }
        buf[n++] = '}';
        buf[n] = '\0';
        return buf;
    }
    case T_FUNC:
        snprintf(tmp, sizeof(tmp), "<func %s>", AS_FUNC(v)->name);
        break;
    case T_FILE:
        snprintf(tmp, sizeof(tmp), "<file %s>", AS_FILE(v)->path);
        break;
    case T_BUILTIN:
        snprintf(tmp, sizeof(tmp), "<builtin %s>", ((Builtin *)v.u.p)->name);
        break;
    case T_MOD:
        snprintf(tmp, sizeof(tmp), "<module %s>", ((HsMod *)v.u.p)->name);
        break;
    case T_SOCK:
        snprintf(tmp, sizeof(tmp), "<sock>");
        break;
    default:
        return "?";
    }
    char *o = GC_MALLOC(strlen(tmp) + 1);
    strcpy(o, tmp);
    return o;
}

// ---------- builtins ----------
Val b_print(Val *args, int nargs, int line) {
    (void)line;
    for (int i = 0; i < nargs; i++) {
        if (i > 0)
            putchar(' ');
        fputs(v_disp(args[i]), stdout);
    }
    putchar('\n');
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
        while (o->cap < n) {
            o->cap *= 2;
            o->items = GC_REALLOC(o->items, sizeof(Val) * (size_t)o->cap);
        }
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
        while (*s == ' ' || *s == '\t' || *s == '\n' || *s == '\r')
            s++;
        char *end = NULL;
        long long v = strtoll(s, &end, 10);
        if (end == s) {
            v = strtoll(s, &end, 0);
            if (end == s)
                hs_err(line, "cannot convert '%s' to Int", AS_STR(a)->data);
        }
        while (*end == ' ' || *end == '\t' || *end == '\n' || *end == '\r')
            end++;
        if (*end != '\0')
            hs_err(line, "cannot convert '%s' to Int", AS_STR(a)->data);
        return v_int((int64_t)v);
    }
    hs_err(line, "cannot convert %s to Int", hs_tname(a));
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
        char *end = NULL;
        double v = strtod(AS_STR(a)->data, &end);
        if (end == AS_STR(a)->data)
            hs_err(line, "cannot convert '%s' to Float", AS_STR(a)->data);
        return v_float(v);
    }
    hs_err(line, "cannot convert %s to Float", hs_tname(a));
}

Val b_input(Val *args, int nargs, int line) {
    if (nargs != 0)
        hs_err(line, "input takes no args");
    char *buf = NULL;
    size_t cap = 0;
    ssize_t n = getline(&buf, &cap, stdin);
    if (n < 0)
        hs_err(line, "input: EOF");
    while (n > 0 && buf[n - 1] == '\n')
        buf[--n] = '\0';
    Val r = v_strn(buf, n);
    free(buf);
    return r;
}

Val b_open(Val *args, int nargs, int line) {
    if (nargs != 2 || args[0].tag != T_STR || args[1].tag != T_STR)
        hs_err(line, "open wants open(path, mode)");
    const char *mode = AS_STR(args[1])->data;
    if (strcmp(mode, "r") != 0 && strcmp(mode, "w") != 0)
        hs_err(line, "open mode must be \"r\" or \"w\"");
    FILE *fp = fopen(AS_STR(args[0])->data, mode);
    if (!fp)
        hs_err(line, "open failed for '%s'", AS_STR(args[0])->data);
    return v_file(fp, AS_STR(args[0])->data);
}

Val b_read(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_FILE)
        hs_err(line, "read wants read(f)");
    File *f = AS_FILE(args[0]);
    if (f->closed)
        hs_err(line, "file is closed");
    size_t cap = 256, n = 0;
    char *buf = GC_MALLOC(cap);
    size_t r;
    while ((r = fread(buf + n, 1, cap - n, (FILE *)f->fp)) > 0) {
        n += r;
        if (n == cap) {
            cap *= 2;
            buf = GC_REALLOC(buf, cap);
        }
    }
    return v_strn(buf, (int64_t)n);
}

Val b_write(Val *args, int nargs, int line) {
    if (nargs != 2 || args[0].tag != T_FILE || args[1].tag != T_STR)
        hs_err(line, "write wants write(f, str)");
    File *f = AS_FILE(args[0]);
    if (f->closed)
        hs_err(line, "file is closed");
    Str *s = AS_STR(args[1]);
    size_t w = fwrite(s->data, 1, (size_t)s->len, (FILE *)f->fp);
    fflush((FILE *)f->fp);
    return v_int((int64_t)w);
}

Val b_close(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_FILE)
        hs_err(line, "close wants close(f)");
    File *f = AS_FILE(args[0]);
    if (!f->closed) {
        fclose((FILE *)f->fp);
        f->closed = 1;
    }
    return v_null();
}

// ---------- unsafe ----------
uint8_t *hs_alloc(int64_t n, int line) {
    if (n < 0)
        hs_err(line, "alloc of negative size %lld", (long long)n);
    size_t m = ((size_t)n + 7) & ~(size_t)7;
    uint8_t *p = GC_MALLOC(m ? m : 8);
    memset(p, 0, m);
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
    memcpy(&v, p, 8);
    return v;
}

void hs_st64(uint8_t *p, int64_t v, int line) {
    hs_ptr_check(p, line);
    if ((uintptr_t)p % 8 != 0)
        hs_err(line, "unaligned 64-bit access (use load8/load32)");
    memcpy(p, &v, 8);
}

int64_t hs_load8(uint8_t *p, int line) {
    hs_ptr_check(p, line);
    return (int64_t)*p;
}

int64_t hs_load32(uint8_t *p, int line) {
    hs_ptr_check(p, line);
    uint32_t v;
    memcpy(&v, p, 4);
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
    memcpy(p, &w, 4);
    return (int64_t)w;
}

int64_t hs_load64(uint8_t *p, int line) {
    hs_ptr_check(p, line);
    uint64_t v;
    memcpy(&v, p, 8);
    return (int64_t)v;
}

int64_t hs_store64(uint8_t *p, int64_t v, int line) {
    hs_ptr_check(p, line);
    uint64_t w = (uint64_t)v;
    memcpy(p, &w, 8);
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

// ---------- extern ffi ----------
int64_t hs_ffi_I64(Val v, int line) {
    if (v.tag != T_INT)
        hs_err(line, "ffi arg wants I64, got %s", hs_tname(v));
    return v.u.i;
}

uint64_t hs_ffi_U64(Val v, int line) {
    if (v.tag != T_INT || v.u.i < 0)
        hs_err(line, "ffi arg wants U64, got %s", hs_tname(v));
    return (uint64_t)v.u.i;
}

double hs_ffi_F64(Val v, int line) {
    if (v.tag == T_FLOAT)
        return v.u.f;
    if (v.tag == T_INT)
        return (double)v.u.i;
    hs_err(line, "ffi arg wants F64, got %s", hs_tname(v));
}

const char *hs_ffi_Str(Val v, int line) {
    if (v.tag != T_STR)
        hs_err(line, "ffi arg wants Str, got %s", hs_tname(v));
    return AS_STR(v)->data;
}

Val hs_box_Str(const char *s) {
    if (!s)
        return v_null();
    return v_str(s);
}

void hs_raise_val(int line, Val v) {
    if (v.tag != T_STR)
        hs_err(line, "raise wants Str");
    hs_err(line, "%s", AS_STR(v)->data);
}

void *hs_ffi_lib(const char *lib, int line) {
    void *h;
    if (!lib) {
        h = dlopen(NULL, RTLD_NOW | RTLD_GLOBAL);
        if (!h)
            hs_err(line, "ffi: cannot open main program: %s", dlerror());
        return h;
    }
    if (strchr(lib, '/')) {
        FILE *f = fopen(lib, "r");
        if (!f)
            hs_err(line, "cannot find ffi library '%s'", lib);
        fclose(f);
        h = dlopen(lib, RTLD_NOW);
        if (!h)
            hs_err(line, "ffi: cannot load '%s': %s", lib, dlerror());
        return h;
    }
    h = dlopen(lib, RTLD_NOW);
    if (!h) {
        char cand[512];
        snprintf(cand, sizeof(cand), "lib%s.so", lib);
        h = dlopen(cand, RTLD_NOW);
    }
    if (!h) {
        char cand[512];
        snprintf(cand, sizeof(cand), "lib%s.so.6", lib);
        h = dlopen(cand, RTLD_NOW);
    }
    if (!h)
        hs_err(line, "ffi: cannot load library '%s': %s", lib, dlerror());
    return h;
}

void *hs_ffi_sym(void *h, const char *name, int line) {
    dlerror();
    void *p = dlsym(h, name);
    const char *e = dlerror();
    if (e || !p)
        hs_err(line, "unknown ffi symbol '%s'%s%s", name, e ? ": " : "", e ? e : "");
    return p;
}

static int64_t b_addr_arg(Val a, const char *name, int line) {
    int64_t p = a.tag == T_INT ? a.u.i : -1;
    if (a.tag == T_BOOL)
        p = a.u.b;
    if (a.tag != T_INT && a.tag != T_BOOL)
        hs_err(line, "%s needs Int, got %s", name, hs_tname(a));
    if (p < 0)
        hs_err(line, "negative address");
    return p;
}

Val b_alloc(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "alloc arg count mismatch");
    if (args[0].tag != T_INT && args[0].tag != T_BOOL)
        hs_err(line, "alloc needs Int, got %s", hs_tname(args[0]));
    int64_t n = args[0].tag == T_INT ? args[0].u.i : args[0].u.b;
    return v_int((int64_t)(uintptr_t)hs_alloc(n, line));
}

Val b_load8(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "load8 arg count mismatch");
    return v_int(hs_load8((uint8_t *)(uintptr_t)(uint64_t)b_addr_arg(args[0], "load8", line), line));
}

Val b_load32(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "load32 arg count mismatch");
    return v_int(hs_load32((uint8_t *)(uintptr_t)(uint64_t)b_addr_arg(args[0], "load32", line), line));
}

Val b_load64(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "load64 arg count mismatch");
    return v_int(hs_load64((uint8_t *)(uintptr_t)(uint64_t)b_addr_arg(args[0], "load64", line), line));
}

Val b_store8(Val *args, int nargs, int line) {
    if (nargs != 2)
        hs_err(line, "store8 arg count mismatch");
    int64_t p = b_addr_arg(args[0], "store8", line);
    if (args[1].tag != T_INT && args[1].tag != T_BOOL)
        hs_err(line, "store8 needs Int, got %s", hs_tname(args[1]));
    int64_t v = args[1].tag == T_INT ? args[1].u.i : args[1].u.b;
    return v_int(hs_store8((uint8_t *)(uintptr_t)(uint64_t)p, v, line));
}

Val b_store32(Val *args, int nargs, int line) {
    if (nargs != 2)
        hs_err(line, "store32 arg count mismatch");
    int64_t p = b_addr_arg(args[0], "store32", line);
    if (args[1].tag != T_INT && args[1].tag != T_BOOL)
        hs_err(line, "store32 needs Int, got %s", hs_tname(args[1]));
    int64_t v = args[1].tag == T_INT ? args[1].u.i : args[1].u.b;
    return v_int(hs_store32((uint8_t *)(uintptr_t)(uint64_t)p, v, line));
}

Val b_store64(Val *args, int nargs, int line) {
    if (nargs != 2)
        hs_err(line, "store64 arg count mismatch");
    int64_t p = b_addr_arg(args[0], "store64", line);
    if (args[1].tag != T_INT && args[1].tag != T_BOOL)
        hs_err(line, "store64 needs Int, got %s", hs_tname(args[1]));
    int64_t v = args[1].tag == T_INT ? args[1].u.i : args[1].u.b;
    return v_int(hs_store64((uint8_t *)(uintptr_t)(uint64_t)p, v, line));
}

Val b_as_ptr(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "as_ptr arg count mismatch");
    if (args[0].tag != T_INT && args[0].tag != T_BOOL)
        hs_err(line, "as_ptr needs Int, got %s", hs_tname(args[0]));
    int64_t v = args[0].tag == T_INT ? args[0].u.i : args[0].u.b;
    if (v < 0)
        hs_err(line, "negative value %lld as Ptr", (long long)v);
    return v_int(v);
}

Val b_as_int(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "as_int arg count mismatch");
    if (args[0].tag != T_INT && args[0].tag != T_BOOL)
        hs_err(line, "as_int needs Int, got %s", hs_tname(args[0]));
    return v_int(args[0].tag == T_INT ? args[0].u.i : args[0].u.b);
}

// hosted approximations of kernel-surface builtins
Val b_ticks(Val *args, int nargs, int line) {
    if (nargs != 0)
        hs_err(line, "ticks takes no args");
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return v_int((int64_t)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000));
}

Val b_readkey(Val *args, int nargs, int line) {
    if (nargs != 0)
        hs_err(line, "readkey takes no args");
    int c = getchar();
    if (c == EOF)
        return v_null();
    char s[2] = {(char)c, 0};
    return v_str(s);
}

static int64_t fake_pmm_total = 65536, fake_pmm_free = 65536;
static int64_t fake_pmm_next = 0x10000000LL;

Val b_pmm_alloc(Val *args, int nargs, int line) {
    if (nargs != 1 || (args[0].tag != T_INT) || args[0].u.i < 0)
        hs_err(line, "pmm_alloc wants pmm_alloc(npages)");
    if (args[0].u.i > fake_pmm_free)
        hs_err(line, "pmm_alloc: out of memory");
    int64_t addr = fake_pmm_next;
    fake_pmm_next += args[0].u.i * 4096;
    fake_pmm_free -= args[0].u.i;
    return v_int(addr);
}

Val b_meminfo(Val *args, int nargs, int line) {
    if (nargs != 0)
        hs_err(line, "meminfo takes no args");
    Val r = v_dict();
    v_setindex(r, v_str("total"), v_int(fake_pmm_total), line);
    v_setindex(r, v_str("free"), v_int(fake_pmm_free), line);
    v_setindex(r, v_str("page"), v_int(4096), line);
    return r;
}

Val b_argv(Val *args, int nargs, int line) {
    if (nargs != 0)
        hs_err(line, "argv takes no args");
    Val r = v_list();
    for (int i = 0; i < hs_argc; i++)
        v_push(r, v_str(hs_argv[i]), line);
    return r;
}

Val b_env(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_STR)
        hs_err(line, "env wants env(name)");
    const char *v = getenv(AS_STR(args[0])->data);
    if (!v)
        return v_null();
    return v_str(v);
}

Val b_system(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_STR)
        hs_err(line, "system wants system(cmd)");
    fflush(stdout);
    int rc = system(AS_STR(args[0])->data);
    if (rc == -1)
        hs_err(line, "system failed to run shell");
    if (WIFEXITED(rc))
        return v_int(WEXITSTATUS(rc));
    hs_err(line, "system: child did not exit normally");
}

// ---------- sockets ----------
#define HSock_OF(v) ((HSock *)((v).u.p))

static HSock *hs_sock_new(int fd) {
    HSock *o = GC_MALLOC(sizeof(HSock));
    o->fd = fd;
    o->closed = 0;
    return o;
}

static HSock *hs_sock_arg(Val a, const char *what, int line) {
    if (a.tag != T_SOCK || HSock_OF(a)->closed)
        hs_err(line, "%s wants an open socket", what);
    return HSock_OF(a);
}

static int hs_dial(const char *host, int64_t port, int line, const char *what) {
    char ps[32];
    snprintf(ps, sizeof(ps), "%lld", (long long)port);
    struct addrinfo hints, *res = NULL;
    memset(&hints, 0, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    if (getaddrinfo(host, ps, &hints, &res) != 0 || !res)
        hs_err(line, "%s failed: cannot resolve '%s'", what, host);
    int fd = -1;
    for (struct addrinfo *ai = res; ai; ai = ai->ai_next) {
        fd = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
        if (fd < 0)
            continue;
        struct timeval tv = {20, 0};
        setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        if (connect(fd, ai->ai_addr, ai->ai_addrlen) == 0)
            break;
        close(fd);
        fd = -1;
    }
    freeaddrinfo(res);
    if (fd < 0)
        hs_err(line, "%s failed: cannot connect to %s:%lld", what, host, (long long)port);
    return fd;
}

Val b_tcp_connect(Val *args, int nargs, int line) {
    if (nargs != 2 || args[0].tag != T_STR || args[1].tag != T_INT)
        hs_err(line, "tcp_connect wants tcp_connect(host, port)");
    return (Val){T_SOCK, {.p = hs_sock_new(hs_dial(AS_STR(args[0])->data, args[1].u.i, line, "tcp_connect"))}};
}

Val b_tcp_send(Val *args, int nargs, int line) {
    if (nargs != 2 || args[1].tag != T_STR)
        hs_err(line, "tcp_send wants tcp_send(sock, str)");
    HSock *o = hs_sock_arg(args[0], "tcp_send", line);
    Str *s = AS_STR(args[1]);
    size_t left = (size_t)s->len;
    const char *p = s->data;
    while (left > 0) {
        ssize_t n = send(o->fd, p, left, 0);
        if (n <= 0)
            hs_err(line, "tcp_send failed");
        p += n;
        left -= (size_t)n;
    }
    return v_int(s->len);
}

Val b_tcp_recv(Val *args, int nargs, int line) {
    if (nargs != 2 || args[1].tag != T_INT)
        hs_err(line, "tcp_recv wants tcp_recv(sock, n)");
    HSock *o = hs_sock_arg(args[0], "tcp_recv", line);
    int64_t n = args[1].u.i;
    if (n < 1)
        n = 1;
    if (n > (1 << 20))
        n = 1 << 20;
    char *buf = GC_MALLOC((size_t)n);
    ssize_t r = recv(o->fd, buf, (size_t)n, 0);
    if (r < 0)
        hs_err(line, "tcp_recv failed");
    if (r == 0)
        return v_str("");
    // decode errors replaced (same as interpreter)
    for (ssize_t i = 0; i < r; i++)
        if ((buf[i] & 0x80) && (i + 1 >= r || (buf[i + 1] & 0xC0) != 0x80))
            buf[i] = '?';
    return v_strn(buf, r);
}

Val b_tcp_close(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_SOCK)
        hs_err(line, "tcp_close wants tcp_close(sock)");
    HSock *o = HSock_OF(args[0]);
    if (!o->closed) {
        close(o->fd);
        o->closed = 1;
    }
    return v_null();
}

Val b_tcp_listen(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_INT)
        hs_err(line, "tcp_listen wants tcp_listen(port)");
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0)
        hs_err(line, "tcp_listen failed");
    int one = 1;
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    struct sockaddr_in a;
    memset(&a, 0, sizeof(a));
    a.sin_family = AF_INET;
    a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    a.sin_port = htons((uint16_t)args[0].u.i);
    if (bind(fd, (struct sockaddr *)&a, sizeof(a)) != 0 || listen(fd, 8) != 0) {
        close(fd);
        hs_err(line, "tcp_listen failed: cannot bind port %lld", (long long)args[0].u.i);
    }
    return (Val){T_SOCK, {.p = hs_sock_new(fd)}};
}

Val b_tcp_accept(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "tcp_accept wants tcp_accept(sock)");
    HSock *o = hs_sock_arg(args[0], "tcp_accept", line);
    int fd = accept(o->fd, NULL, NULL);
    if (fd < 0)
        hs_err(line, "tcp_accept failed");
    return (Val){T_SOCK, {.p = hs_sock_new(fd)}};
}

Val b_http_get(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_STR)
        hs_err(line, "http_get wants http_get(url)");
    const char *url = AS_STR(args[0])->data;
    if (strncmp(url, "http://", 7) != 0)
        hs_err(line, "http_get wants an http:// url (no https in v1)");
    const char *rest = url + 7;
    const char *slash = strchr(rest, '/');
    char host[256];
    const char *path = slash ? slash : "/";
    size_t hlen = slash ? (size_t)(slash - rest) : strlen(rest);
    if (hlen == 0 || hlen >= sizeof(host))
        hs_err(line, "http_get bad url");
    memcpy(host, rest, hlen);
    host[hlen] = '\0';
    int64_t port = 80;
    char *colon = strchr(host, ':');
    if (colon) {
        *colon = '\0';
        port = atoll(colon + 1);
        if (port <= 0 || port > 65535)
            hs_err(line, "http_get bad port in url");
    }
    if (!host[0])
        hs_err(line, "http_get bad url");
    int fd = hs_dial(host, port, line, "http_get");
    char req[1024];
    snprintf(req, sizeof(req), "GET %s HTTP/1.0\r\nHost: %s\r\nConnection: close\r\n\r\n", path, host);
    size_t left = strlen(req);
    const char *pp = req;
    while (left > 0) {
        ssize_t n = send(fd, pp, left, 0);
        if (n <= 0) {
            close(fd);
            hs_err(line, "http_get failed: send error");
        }
        pp += n;
        left -= (size_t)n;
    }
    size_t cap = 1 << 16, len = 0;
    char *raw = GC_MALLOC(cap);
    for (;;) {
        if (len + 65536 > cap) {
            cap *= 2;
            raw = GC_REALLOC(raw, cap);
        }
        ssize_t n = recv(fd, raw + len, 65536, 0);
        if (n < 0) {
            close(fd);
            hs_err(line, "http_get failed: recv error");
        }
        if (n == 0)
            break;
        len += (size_t)n;
    }
    close(fd);
    raw[len] = '\0';
    char *sep = strstr(raw, "\r\n\r\n");
    if (!sep)
        hs_err(line, "http_get got a bad response");
    int status = 0;
    if (sscanf(raw, "HTTP/%*s %d", &status) != 1)
        hs_err(line, "http_get got a bad response");
    if (status < 200 || status > 299)
        hs_err(line, "http status %d", status);
    return v_str(sep + 4);
}

// ---------- json ----------
#define HS_JSON_MAXDEPTH 200

typedef struct {
    const char *p;
    int line;
    int depth;
} JParse;

static void j_err(JParse *j, const char *msg) {
    hs_err(j->line, "json_parse failed: %s", msg);
}

static void j_ws(JParse *j) {
    while (*j->p == ' ' || *j->p == '\t' || *j->p == '\n' || *j->p == '\r')
        j->p++;
}

static Val j_value(JParse *j);

static unsigned j_hex4(JParse *j) {
    unsigned v = 0;
    for (int i = 0; i < 4; i++) {
        char c = *j->p++;
        v <<= 4;
        if (c >= '0' && c <= '9')
            v |= (unsigned)(c - '0');
        else if (c >= 'a' && c <= 'f')
            v |= (unsigned)(c - 'a' + 10);
        else if (c >= 'A' && c <= 'F')
            v |= (unsigned)(c - 'A' + 10);
        else
            j_err(j, "bad \\u escape");
    }
    return v;
}

static void j_utf8(char **o, size_t *n, size_t *cap, unsigned cp) {
    char tmp[4];
    int m = 0;
    if (cp < 0x80)
        tmp[m++] = (char)cp;
    else if (cp < 0x800) {
        tmp[m++] = (char)(0xC0 | (cp >> 6));
        tmp[m++] = (char)(0x80 | (cp & 0x3F));
    } else if (cp < 0x10000) {
        tmp[m++] = (char)(0xE0 | (cp >> 12));
        tmp[m++] = (char)(0x80 | ((cp >> 6) & 0x3F));
        tmp[m++] = (char)(0x80 | (cp & 0x3F));
    } else {
        tmp[m++] = (char)(0xF0 | (cp >> 18));
        tmp[m++] = (char)(0x80 | ((cp >> 12) & 0x3F));
        tmp[m++] = (char)(0x80 | ((cp >> 6) & 0x3F));
        tmp[m++] = (char)(0x80 | (cp & 0x3F));
    }
    while (*n + (size_t)m + 1 >= *cap) {
        *cap *= 2;
        *o = GC_REALLOC(*o, *cap);
    }
    memcpy(*o + *n, tmp, (size_t)m);
    *n += (size_t)m;
}

static Val j_string(JParse *j) {
    j->p++;  // opening quote
    size_t cap = 32, n = 0;
    char *o = GC_MALLOC(cap);
    for (;;) {
        unsigned char c = (unsigned char)*j->p++;
        if (c == '"')
            break;
        if (c == '\0')
            j_err(j, "unterminated string");
        if (c < 0x20)
            j_err(j, "bad string");
        if (c == '\\') {
            char e = *j->p++;
            switch (e) {
            case '"': c = '"'; break;
            case '\\': c = '\\'; break;
            case '/': c = '/'; break;
            case 'b': c = '\b'; break;
            case 'f': c = '\f'; break;
            case 'n': c = '\n'; break;
            case 'r': c = '\r'; break;
            case 't': c = '\t'; break;
            case 'u': {
                unsigned cp = j_hex4(j);
                if (cp >= 0xD800 && cp <= 0xDBFF && j->p[0] == '\\' && j->p[1] == 'u') {
                    j->p += 2;
                    unsigned lo = j_hex4(j);
                    if (lo >= 0xDC00 && lo <= 0xDFFF)
                        cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00);
                    else
                        j_err(j, "bad surrogate pair");
                } else if (cp >= 0xDC00 && cp <= 0xDFFF) {
                    j_err(j, "bad surrogate pair");
                }
                j_utf8(&o, &n, &cap, cp);
                continue;
            }
            default:
                j_err(j, "bad escape");
            }
        }
        while (n + 2 >= cap) {
            cap *= 2;
            o = GC_REALLOC(o, cap);
        }
        o[n++] = (char)c;
    }
    return v_strn(o, (int64_t)n);
}

static Val j_number(JParse *j) {
    const char *start = j->p;
    if (*j->p == '-')
        j->p++;
    if (!(*j->p >= '0' && *j->p <= '9'))
        j_err(j, "bad number");
    if (*j->p == '0')
        j->p++;
    else
        while (*j->p >= '0' && *j->p <= '9')
            j->p++;
    int is_float = 0;
    if (*j->p == '.') {
        is_float = 1;
        j->p++;
        if (!(*j->p >= '0' && *j->p <= '9'))
            j_err(j, "bad number");
        while (*j->p >= '0' && *j->p <= '9')
            j->p++;
    }
    if (*j->p == 'e' || *j->p == 'E') {
        is_float = 1;
        j->p++;
        if (*j->p == '+' || *j->p == '-')
            j->p++;
        if (!(*j->p >= '0' && *j->p <= '9'))
            j_err(j, "bad number");
        while (*j->p >= '0' && *j->p <= '9')
            j->p++;
    }
    if (is_float)
        return v_float(strtod(start, NULL));
    errno = 0;
    long long v = strtoll(start, NULL, 10);
    if (errno == ERANGE)
        j_err(j, "number out of range");
    return v_int((int64_t)v);
}

static Val j_array(JParse *j) {
    j->p++;  // [
    Val r = v_list();
    j_ws(j);
    if (*j->p == ']') {
        j->p++;
        return r;
    }
    for (;;) {
        v_push(r, j_value(j), j->line);
        j_ws(j);
        if (*j->p == ',') {
            j->p++;
            continue;
        }
        if (*j->p == ']') {
            j->p++;
            return r;
        }
        j_err(j, "expected ',' or ']'");
    }
}

static Val j_object(JParse *j) {
    j->p++;  // {
    Val r = v_dict();
    j_ws(j);
    if (*j->p == '}') {
        j->p++;
        return r;
    }
    for (;;) {
        j_ws(j);
        if (*j->p != '"')
            j_err(j, "expected string key");
        Val k = j_string(j);
        j_ws(j);
        if (*j->p != ':')
            j_err(j, "expected ':'");
        j->p++;
        v_setindex(r, k, j_value(j), j->line);
        j_ws(j);
        if (*j->p == ',') {
            j->p++;
            continue;
        }
        if (*j->p == '}') {
            j->p++;
            return r;
        }
        j_err(j, "expected ',' or '}'");
    }
}

static Val j_value(JParse *j) {
    if (++j->depth > HS_JSON_MAXDEPTH)
        j_err(j, "too deeply nested");
    j_ws(j);
    char c = *j->p;
    Val v;
    if (c == '{')
        v = j_object(j);
    else if (c == '[')
        v = j_array(j);
    else if (c == '"')
        v = j_string(j);
    else if ((c >= '0' && c <= '9') || c == '-')
        v = j_number(j);
    else if (strncmp(j->p, "true", 4) == 0) {
        j->p += 4;
        v = v_bool(1);
    } else if (strncmp(j->p, "false", 5) == 0) {
        j->p += 5;
        v = v_bool(0);
    } else if (strncmp(j->p, "null", 4) == 0) {
        j->p += 4;
        v = v_null();
    } else {
        j_err(j, "unexpected character");
        v = v_null();
    }
    j->depth--;
    return v;
}

Val b_json_parse(Val *args, int nargs, int line) {
    if (nargs != 1 || args[0].tag != T_STR)
        hs_err(line, "json_parse wants json_parse(str)");
    JParse j = {AS_STR(args[0])->data, line, 0};
    Val v = j_value(&j);
    j_ws(&j);
    if (*j.p != '\0')
        hs_err(line, "json_parse failed: trailing data");
    return v;
}

static void js_buf(char **o, size_t *n, size_t *cap, const char *s, size_t m) {
    while (*n + m + 1 >= *cap) {
        *cap *= 2;
        *o = GC_REALLOC(*o, *cap);
    }
    memcpy(*o + *n, s, m);
    *n += m;
}

static void js_str(char **o, size_t *n, size_t *cap, const char *s, int64_t len, int line) {
    js_buf(o, n, cap, "\"", 1);
    for (int64_t i = 0; i < len; i++) {
        unsigned char c = (unsigned char)s[i];
        switch (c) {
        case '"': js_buf(o, n, cap, "\\\"", 2); break;
        case '\\': js_buf(o, n, cap, "\\\\", 2); break;
        case '\b': js_buf(o, n, cap, "\\b", 2); break;
        case '\f': js_buf(o, n, cap, "\\f", 2); break;
        case '\n': js_buf(o, n, cap, "\\n", 2); break;
        case '\r': js_buf(o, n, cap, "\\r", 2); break;
        case '\t': js_buf(o, n, cap, "\\t", 2); break;
        default:
            if (c < 0x20) {
                char esc[7];
                snprintf(esc, sizeof(esc), "\\u%04x", c);
                js_buf(o, n, cap, esc, 6);
            } else {
                js_buf(o, n, cap, (const char *)&s[i], 1);
            }
        }
    }
    js_buf(o, n, cap, "\"", 1);
    (void)line;
}

static void js_val(Val v, char **o, size_t *n, size_t *cap, int line, int depth) {
    if (depth > HS_JSON_MAXDEPTH)
        hs_err(line, "json too deeply nested");
    char tmp[64];
    switch (v.tag) {
    case T_NULL:
        js_buf(o, n, cap, "null", 4);
        return;
    case T_BOOL:
        js_buf(o, n, cap, v.u.b ? "true" : "false", v.u.b ? 4 : 5);
        return;
    case T_INT:
        snprintf(tmp, sizeof(tmp), "%lld", (long long)v.u.i);
        js_buf(o, n, cap, tmp, strlen(tmp));
        return;
    case T_FLOAT: {
        if (!isfinite(v.u.f))
            hs_err(line, "json_str failed: non-finite float");
        snprintf(tmp, sizeof(tmp), "%.17g", v.u.f);
        js_buf(o, n, cap, tmp, strlen(tmp));
        return;
    }
    case T_STR: {
        Str *s = AS_STR(v);
        js_str(o, n, cap, s->data, s->len, line);
        return;
    }
    case T_LIST: {
        List *l = AS_LIST(v);
        js_buf(o, n, cap, "[", 1);
        for (int64_t i = 0; i < l->len; i++) {
            if (i > 0)
                js_buf(o, n, cap, ", ", 2);
            js_val(l->items[i], o, n, cap, line, depth + 1);
        }
        js_buf(o, n, cap, "]", 1);
        return;
    }
    case T_DICT: {
        Dict *d = AS_DICT(v);
        js_buf(o, n, cap, "{", 1);
        for (int64_t i = 0; i < d->len; i++) {
            if (i > 0)
                js_buf(o, n, cap, ", ", 2);
            js_str(o, n, cap, d->keys[i], (int64_t)strlen(d->keys[i]), line);
            js_buf(o, n, cap, ": ", 2);
            js_val(d->vals[i], o, n, cap, line, depth + 1);
        }
        js_buf(o, n, cap, "}", 1);
        return;
    }
    default:
        break;
    }
    hs_err(line, "not JSON-serializable: %s", hs_tname(v));
}

Val b_json_str(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "json_str wants json_str(x)");
    size_t cap = 128, n = 0;
    char *o = GC_MALLOC(cap);
    js_val(args[0], &o, &n, &cap, line, 0);
    return v_strn(o, (int64_t)n);
}

// ---------- agent-friendly fs helpers ----------
static const char *hs_fs_str(Val v, const char *what, int line) {
    if (v.tag != T_STR)
        hs_err(line, "%s wants Str paths", what);
    return AS_STR(v)->data;
}

Val b_read_text(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "read_text wants read_text(path)");
    const char *path = hs_fs_str(args[0], "read_text", line);
    FILE *f = fopen(path, "r");
    if (!f)
        hs_err(line, "read_text failed: cannot open '%s'", path);
    size_t cap = 4096, n = 0;
    char *o = GC_MALLOC(cap);
    size_t r;
    while ((r = fread(o + n, 1, cap - n - 1, f)) > 0) {
        n += r;
        if (n + 1 >= cap) {
            cap *= 2;
            o = GC_REALLOC(o, cap);
        }
    }
    fclose(f);
    return v_strn(o, (int64_t)n);
}

Val b_read_mem(Val *args, int nargs, int line) {
    if (nargs != 2)
        hs_err(line, "read_mem wants read_mem(ptr, nbytes)");
    if (args[0].tag != T_INT || args[1].tag != T_INT)
        hs_err(line, "read_mem wants read_mem(ptr, nbytes)");
    int64_t p = args[0].u.i, n = args[1].u.i;
    if (n < 0)
        hs_err(line, "read_mem length must be >= 0");
    if (n == 0)
        return v_strn("", 0);
    if (p == 0)
        hs_err(line, "null pointer dereference");
    char *o = GC_MALLOC((size_t)n);
    memcpy(o, (const void *)(uintptr_t)p, (size_t)n);
    return v_strn(o, n);
}

Val b_write_text(Val *args, int nargs, int line) {
    if (nargs != 2)
        hs_err(line, "write_text wants write_text(path, str)");
    const char *path = hs_fs_str(args[0], "write_text", line);
    if (args[1].tag != T_STR)
        hs_err(line, "write_text wants Str content");
    FILE *f = fopen(path, "w");
    if (!f)
        hs_err(line, "write_text failed: cannot open '%s'", path);
    Str *s = AS_STR(args[1]);
    if (s->len > 0 && fwrite(s->data, 1, (size_t)s->len, f) != (size_t)s->len) {
        fclose(f);
        hs_err(line, "write_text failed: cannot write '%s'", path);
    }
    fclose(f);
    return v_null();
}

Val b_append_text(Val *args, int nargs, int line) {
    if (nargs != 2)
        hs_err(line, "append_text wants append_text(path, str)");
    const char *path = hs_fs_str(args[0], "append_text", line);
    if (args[1].tag != T_STR)
        hs_err(line, "append_text wants Str content");
    FILE *f = fopen(path, "a");
    if (!f)
        hs_err(line, "append_text failed: cannot open '%s'", path);
    Str *s = AS_STR(args[1]);
    if (s->len > 0 && fwrite(s->data, 1, (size_t)s->len, f) != (size_t)s->len) {
        fclose(f);
        hs_err(line, "append_text failed: cannot write '%s'", path);
    }
    fclose(f);
    return v_null();
}

Val b_exists(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "exists wants exists(path)");
    const char *path = hs_fs_str(args[0], "exists", line);
    struct stat st;
    return v_bool(stat(path, &st) == 0);
}

static int hs_cmp_val_str(const void *a, const void *b) {
    return strcmp(AS_STR(*(const Val *)a)->data, AS_STR(*(const Val *)b)->data);
}

Val b_ls(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "ls wants ls(dir)");
    const char *path = hs_fs_str(args[0], "ls", line);
    DIR *d = opendir(path);
    if (!d)
        hs_err(line, "ls failed: cannot open '%s'", path);
    Val r = v_list();
    struct dirent *e;
    while ((e = readdir(d)) != NULL) {
        if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0)
            continue;
        v_push(r, v_str(e->d_name), line);
    }
    closedir(d);
    List *l = AS_LIST(r);
    qsort(l->items, (size_t)l->len, sizeof(Val), hs_cmp_val_str);
    return r;
}

Val b_mkdir(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "mkdir wants mkdir(path)");
    const char *path = hs_fs_str(args[0], "mkdir", line);
    // mkdir -p semantics: create parents as needed, ok if exists
    char tmp[1024];
    snprintf(tmp, sizeof(tmp), "%s", path);
    for (char *p = tmp + 1; *p; p++) {
        if (*p == '/') {
            *p = '\0';
            mkdir(tmp, 0755);
            *p = '/';
        }
    }
    struct stat st;
    if (stat(tmp, &st) == 0)
        return v_null();
    if (mkdir(tmp, 0755) != 0)
        hs_err(line, "mkdir failed: cannot create '%s'", path);
    return v_null();
}

Val b_json_load(Val *args, int nargs, int line) {
    if (nargs != 1)
        hs_err(line, "json_load wants json_load(path)");
    Val args1[1] = {b_read_text(args, nargs, line)};
    return b_json_parse(args1, 1, line);
}

Val b_json_save(Val *args, int nargs, int line) {
    if (nargs != 2 || args[0].tag != T_STR)
        hs_err(line, "json_save wants json_save(path, x)");
    Val s = b_json_str(args + 1, 1, line);
    Val args2[2] = {args[0], s};
    return b_write_text(args2, 2, line);
}

Val b_append(Val *args, int nargs, int line) {
    if (nargs != 2 || args[0].tag != T_LIST)
        hs_err(line, "append wants append(list, x)");
    v_push(args[0], args[1], line);
    return v_null();
}

static int hs_is_space(char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f';
}

Val b_split(Val *args, int nargs, int line) {
    if ((nargs != 1 && nargs != 2) || args[0].tag != T_STR ||
            (nargs == 2 && args[1].tag != T_STR))
        hs_err(line, "split wants split(s) or split(s, sep)");
    Str *s = AS_STR(args[0]);
    Val r = v_list();
    if (nargs == 1) {
        int64_t i = 0;
        while (i < s->len) {
            while (i < s->len && hs_is_space(s->data[i]))
                i++;
            if (i >= s->len)
                break;
            int64_t j = i;
            while (j < s->len && !hs_is_space(s->data[j]))
                j++;
            v_push(r, v_strn(s->data + i, j - i), line);
            i = j;
        }
        return r;
    }
    Str *sep = AS_STR(args[1]);
    if (sep->len == 0)
        hs_err(line, "split with empty separator");
    int64_t i = 0, start = 0;
    while (i + sep->len <= s->len) {
        if (memcmp(s->data + i, sep->data, (size_t)sep->len) == 0) {
            v_push(r, v_strn(s->data + start, i - start), line);
            i += sep->len;
            start = i;
        } else {
            i++;
        }
    }
    v_push(r, v_strn(s->data + start, s->len - start), line);
    return r;
}

Val b_find(Val *args, int nargs, int line) {
    if (nargs != 2 || args[0].tag != T_STR || args[1].tag != T_STR)
        hs_err(line, "find wants find(s, sub)");
    Str *s = AS_STR(args[0]), *sub = AS_STR(args[1]);
    if (sub->len == 0)
        return v_int(0);
    for (int64_t i = 0; i + sub->len <= s->len; i++)
        if (memcmp(s->data + i, sub->data, (size_t)sub->len) == 0)
            return v_int(i);
    return v_int(-1);
}

Val b_join(Val *args, int nargs, int line) {
    if (nargs != 2 || args[0].tag != T_STR || args[1].tag != T_LIST)
        hs_err(line, "join wants join(sep, list)");
    Str *sep = AS_STR(args[0]);
    List *l = AS_LIST(args[1]);
    int64_t total = 0;
    for (int64_t i = 0; i < l->len; i++) {
        if (l->items[i].tag != T_STR)
            hs_err(line, "join needs a list of Str");
        total += AS_STR(l->items[i])->len;
    }
    if (l->len > 1)
        total += sep->len * (l->len - 1);
    char *buf = GC_MALLOC((size_t)total + 1);
    int64_t n = 0;
    for (int64_t i = 0; i < l->len; i++) {
        if (i > 0) {
            memcpy(buf + n, sep->data, (size_t)sep->len);
            n += sep->len;
        }
        Str *p = AS_STR(l->items[i]);
        memcpy(buf + n, p->data, (size_t)p->len);
        n += p->len;
    }
    buf[n] = '\0';
    return v_strn(buf, total);
}
