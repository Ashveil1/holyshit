// holyshit native runtime (เฟส 3a) — tagged values + Boehm GC.
// Generated programs link against rt.c with -lgc.
#ifndef HS_RT_H
#define HS_RT_H

#include <stdint.h>

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
    T_BUILTIN
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
    char **keys;
    Val *vals;
} Dict;

typedef struct {
    Val (*fn)(Val *args, int nargs, int line);
    const char *name;
    int arity;
} Func;

typedef struct {
    void *fp;
    char *path;
    int closed;
} File;

typedef Val (*BuiltinFn)(Val *args, int nargs, int line);
typedef struct {
    BuiltinFn fn;
    const char *name;
} Builtin;

// kernel init (serial + VGA + IDT/PIC/PIT + PMM, then sti)
void hs_kinit(uint32_t mb_magic, uint32_t mb_info);

// port IO for drivers/handlers
void hs_outb(uint16_t port, uint8_t v);
uint8_t hs_inb(uint16_t port);

// error (noreturn): prints "error: <msg> at line N", then halts
void hs_err(int line, const char *fmt, ...) __attribute__((noreturn));

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
void v_setindex(Val obj, Val idx, Val v, int line);
void v_push(Val list, Val v, int line);
Val v_builtin(const char *name);
Val v_call(Val fn, Val *args, int nargs, int line);
Val v_seq(Val v, int line); // materialize iterable -> List Val

// display (also used by str())
const char *v_disp(Val v);

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
Val b_store8(Val *args, int nargs, int line);
Val b_store32(Val *args, int nargs, int line);
Val b_as_ptr(Val *args, int nargs, int line);
Val b_as_int(Val *args, int nargs, int line);
Val b_ticks(Val *args, int nargs, int line);
Val b_readkey(Val *args, int nargs, int line);
Val b_pmm_alloc(Val *args, int nargs, int line);
Val b_meminfo(Val *args, int nargs, int line);

// unsafe statics (used by generated unsafe code)
uint8_t *hs_alloc(int64_t n, int line);
int64_t hs_ld64(uint8_t *p, int line);
void hs_st64(uint8_t *p, int64_t v, int line);
int64_t hs_load8(uint8_t *p, int line);
int64_t hs_load32(uint8_t *p, int line);
int64_t hs_store8(uint8_t *p, int64_t v, int line);
int64_t hs_store32(uint8_t *p, int64_t v, int line);
int64_t hs_unbox_I64(Val v, int line);
uint64_t hs_unbox_U64(Val v, int line);
uint8_t *hs_unbox_Ptr(Val v, int line);
Val hs_box_U64(uint64_t v, int line);

#define AS_STR(v) ((Str *)((v).u.p))
#define AS_LIST(v) ((List *)((v).u.p))
#define AS_DICT(v) ((Dict *)((v).u.p))
#define AS_FUNC(v) ((Func *)((v).u.p))
#define AS_FILE(v) ((File *)((v).u.p))

#endif
