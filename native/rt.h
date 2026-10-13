// holyshit native runtime (เฟส 3a) — tagged values + Boehm GC.
// Generated programs link against rt.c with -lgc.
#ifndef HS_RT_H
#define HS_RT_H

#include <stdint.h>

// float literal bits -> double (see hs_f64raw in rt.c)
double hs_f64raw(uint64_t bits);

typedef enum {
    T_UNBOUND = 0,
    T_NULL,
    T_BOOL,
    T_INT,
    T_FLOAT,
    T_STR,
    T_LIST,
    T_DICT,
    T_FUNC,
    T_FILE,
    T_BUILTIN,
    T_MOD,
    T_SOCK
} Tag;

typedef struct {
    Tag tag;
    union {
        int b;
        int64_t i;
        double f;
        void *p;
    } u;
} Val;

typedef struct {
    int64_t len;
    char data[];
} Str;

typedef struct {
    int64_t len, cap;
    Val *items;
} List;

typedef struct {
    int64_t len, cap;
    Val *keys;  // Str or Int
    Val *vals;
} Dict;

typedef struct {
    Val (*fn)(Val *args, int nargs, int line);
    const char *name;
    int arity;
    int ncaps;
    Val *caps;  // snapshot taken at def (copy semantics)
} Func;

typedef struct {
    void *fp;
    char *path;
    int closed;
} File;

typedef struct {
    const char *name;
} HsMod;

typedef struct {
    int fd;
    int closed;
} HSock;

typedef Val (*BuiltinFn)(Val *args, int nargs, int line);
typedef struct {
    BuiltinFn fn;
    const char *name;
} Builtin;

// error (noreturn): prints "error: <msg> at line N", exit 1.
// If a try handler is active, delivers to it instead (longjmp).
void hs_err(int line, const char *fmt, ...);

// try/except machinery (setjmp based)
#include <setjmp.h>
typedef struct HSTry {
    jmp_buf buf;
    struct HSTry *prev;
    char msg[1024];
    int line;
} HSTry;
extern HSTry *hs_try_top;
void hs_try_push(HSTry *f);
void hs_try_pop(void);

// constructors
Val v_null(void);
Val v_bool(int b);
Val v_int(int64_t i);
Val v_float(double f);
Val v_str(const char *s);
Val v_strn(const char *s, int64_t n);
Val v_list(void);
Val v_dict(void);
Val v_func(Val (*fn)(Val *, int, int), const char *name, int arity);
void v_func_setcaps(Val fn, Val *caps, int n);  // snapshot captures (copy)
extern Val *hs_cur_caps;  // active closure captures (set by v_call)
extern int hs_cur_ncaps;
Val v_file(void *fp, const char *path);
Val v_unbound(void);

// read check (unknown variable) + truthiness
Val v_chk(Val v, const char *name, int line);
int v_truthy(Val v);
const char *hs_tname(Val v);

// operators (line = source line for errors)
Val v_add(Val a, Val b, int line);
Val v_sub(Val a, Val b, int line);
Val v_mul(Val a, Val b, int line);
Val v_div(Val a, Val b, int line);
Val v_mod(Val a, Val b, int line);
Val v_and(Val a, Val b, int line);
Val v_or(Val a, Val b, int line);
Val v_xor(Val a, Val b, int line);
Val v_shl(Val a, Val b, int line);
Val v_shr(Val a, Val b, int line);
Val v_bnot(Val v, int line);
Val v_neg(Val v, int line);
Val v_not(Val v);
Val v_eq(Val a, Val b);
Val v_ne(Val a, Val b);
Val v_lt(Val a, Val b, int line);
Val v_gt(Val a, Val b, int line);
Val v_le(Val a, Val b, int line);
Val v_ge(Val a, Val b, int line);

// access
Val v_index(Val obj, Val idx, int line);
Val v_slice(Val obj, Val start, Val stop, int line); // T_NULL start/stop = missing
void v_setindex(Val obj, Val idx, Val v, int line);
void v_push(Val list, Val v, int line);
Val v_builtin(const char *name);
Val v_call(Val fn, Val *args, int nargs, int line);
Val v_seq(Val v, int line); // materialize iterable -> List Val

// display (also used by str())
const char *v_disp(Val v);

// dynamic module attribute access (registry filled by generated initfns)
void hs_reg_attr(const char *mod, const char *name, Val *slot);
Val v_getattr(Val mod, const char *name, int line);
void v_setattr(Val mod, const char *name, Val v, int line);
Val v_module(const char *name);

// builtins (callable directly from generated code)
Val b_print(Val *args, int nargs, int line);
Val b_len(Val *args, int nargs, int line);
Val b_range(Val *args, int nargs, int line);
Val b_str(Val *args, int nargs, int line);
Val b_int(Val *args, int nargs, int line);
Val b_float(Val *args, int nargs, int line);
Val b_input(Val *args, int nargs, int line);
Val b_open(Val *args, int nargs, int line);
Val b_read(Val *args, int nargs, int line);
Val b_write(Val *args, int nargs, int line);
Val b_close(Val *args, int nargs, int line);
Val b_alloc(Val *args, int nargs, int line);
Val b_load8(Val *args, int nargs, int line);
Val b_load32(Val *args, int nargs, int line);
Val b_load64(Val *args, int nargs, int line);
Val b_store8(Val *args, int nargs, int line);
Val b_store32(Val *args, int nargs, int line);
Val b_store64(Val *args, int nargs, int line);
Val b_as_ptr(Val *args, int nargs, int line);
Val b_as_int(Val *args, int nargs, int line);
Val b_append(Val *args, int nargs, int line);
Val b_split(Val *args, int nargs, int line);
Val b_find(Val *args, int nargs, int line);
Val b_join(Val *args, int nargs, int line);
Val b_has(Val *args, int nargs, int line);
Val b_keys(Val *args, int nargs, int line);
Val b_values(Val *args, int nargs, int line);
Val b_contains(Val *args, int nargs, int line);
Val b_ticks(Val *args, int nargs, int line);
Val b_readkey(Val *args, int nargs, int line);
Val b_pmm_alloc(Val *args, int nargs, int line);
Val b_meminfo(Val *args, int nargs, int line);
Val b_append(Val *args, int nargs, int line);
Val b_split(Val *args, int nargs, int line);
Val b_find(Val *args, int nargs, int line);
Val b_join(Val *args, int nargs, int line);
Val b_argv(Val *args, int nargs, int line);
Val b_env(Val *args, int nargs, int line);
Val b_system(Val *args, int nargs, int line);
Val b_tcp_connect(Val *args, int nargs, int line);
Val b_tcp_send(Val *args, int nargs, int line);
Val b_tcp_recv(Val *args, int nargs, int line);
Val b_tcp_close(Val *args, int nargs, int line);
Val b_tcp_listen(Val *args, int nargs, int line);
Val b_tcp_accept(Val *args, int nargs, int line);
Val b_http_get(Val *args, int nargs, int line);
Val b_json_parse(Val *args, int nargs, int line);
Val b_json_str(Val *args, int nargs, int line);
Val b_read_text(Val *args, int nargs, int line);
Val b_read_mem(Val *args, int nargs, int line);
Val b_write_text(Val *args, int nargs, int line);
Val b_write_bytes(Val *args, int nargs, int line);
Val b_append_text(Val *args, int nargs, int line);
Val b_exists(Val *args, int nargs, int line);
Val b_ls(Val *args, int nargs, int line);
Val b_mkdir(Val *args, int nargs, int line);
Val b_json_load(Val *args, int nargs, int line);
Val b_json_save(Val *args, int nargs, int line);
Val b_meminfo(Val *args, int nargs, int line);

// unsafe statics (used by generated unsafe code)
uint8_t *hs_alloc(int64_t n, int line);
int64_t hs_ld64(uint8_t *p, int line);
void hs_st64(uint8_t *p, int64_t v, int line);
int64_t hs_load8(uint8_t *p, int line);
int64_t hs_load32(uint8_t *p, int line);
int64_t hs_load64(uint8_t *p, int line);
int64_t hs_store8(uint8_t *p, int64_t v, int line);
int64_t hs_store32(uint8_t *p, int64_t v, int line);
int64_t hs_store64(uint8_t *p, int64_t v, int line);
int64_t hs_unbox_I64(Val v, int line);
uint64_t hs_unbox_U64(Val v, int line);
uint8_t *hs_unbox_Ptr(Val v, int line);
Val hs_box_U64(uint64_t v, int line);

// extern ffi: strict unboxers + shared-lib loading (dlsym, no prototypes needed)
int64_t hs_ffi_I64(Val v, int line);
uint64_t hs_ffi_U64(Val v, int line);
double hs_ffi_F64(Val v, int line);
const char *hs_ffi_Str(Val v, int line);
Val hs_box_Str(const char *s);
void hs_raise_val(int line, Val v);
void *hs_ffi_lib(const char *lib, int line);   // NULL = main program
void *hs_ffi_sym(void *h, const char *name, int line);

// program arguments (without argv[0])
extern int hs_argc;
extern char **hs_argv;

#define AS_STR(v) ((Str *)((v).u.p))
#define AS_LIST(v) ((List *)((v).u.p))
#define AS_DICT(v) ((Dict *)((v).u.p))
#define AS_FUNC(v) ((Func *)((v).u.p))
#define AS_FILE(v) ((File *)((v).u.p))

#endif
