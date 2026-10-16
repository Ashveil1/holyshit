#!/usr/bin/env python3
"""Run every holyshit suite: python3 tests/run_all.py [--quick]

--quick skips test_xkernel.py (needs qemu-system-x86_64 and boots 24 kernels).

Suites:
  test.py         51  interpreter (reference semantics)
  test_native.py  52  gcc native backend, byte-identical to interp
  test_fmt.py      4  formatter canonical + idempotent + same behavior
  test_x64.py    102  x86-64 backend, static ELF, no gcc
  test_ir.py     141  IR: build/verify/exec byte-identical to interp
  test_irx64.py   44  IR->x64 ELF agrees with AST-path ELF
  test_xkernel.py 291 freestanding kernel booting on QEMU
  test_examples.py 17  every examples/*.holy still runs (interp + native)
  test_lsp.py     25  language server over stdio
  test_docs.py    41  doc examples really run, links + api.json stay in sync
  test_selfhost.py 808 self-hosted lexer/parser/formatter (hs) match the Python ones on every repo .holy
  test_run.py     45  `hs run` backend choice, fallback, overrides
  test_asm.py      1  selfhost/asm.holy (assembler in hs) == x64.py byte for byte (17.8k instrs)
  test_elf.py      1  selfhost/elf.holy (ELF writer in hs) == x64.py pack() byte for byte
  test_irlib.py    1  selfhost/irlib.holy (IR loader in hs) == ir.parse_module on every lowerable repo program
  test_gcrt.py     1  selfhost/gcrt.holy (allocator/GC emitter in hs) == gcrt.py byte for byte
  test_be.py      58  selfhost/be (irx64 + x64gen runtime translated to hs) == irx64.py images
  test_cc.py      79  selfhost/cc.holy (compiler written in hs) emits ELFs equal to interp
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SUITES = [
    ("test_holy_native.py", "x64/native hosted .holy import bridge"),
    ("test.py", "interpreter"),
    ("test_native_strings.py", "UTF-8 literals and embedded-NUL display/key bytes"),
    ("test_native.py", "native (gcc)"),
    ("test_fmt_controls.py", "formatter preserves every ASCII control byte"),
    ("test_fmt.py", "formatter"),
    ("test_x64.py", "x64 backend"),
    ("test_holy_bridge.py", "reference/GCC/LSP .holy compatibility stage"),
    ("test_ir_profile.py", "bounded opt-in IR execution profiling, not JIT"),
    ("test_ir.py", "IR (build/verify/exec)"),
    ("test_write_bytes_x64.py", "x64 write_bytes matches interp output and validation"),
    ("test_irx64.py", "IR->x64 differential"),
    ("test_xkernel.py", "kernel on QEMU"),
    ("test_keyboard_queue.py", "deterministic keyboard FIFO/overflow/IF/readkey on QEMU"),
    ("test_timer_irq.py", "deterministic timer IRQ GPR preservation"),
    ("test_kernel_ir.py", "retained AST kernel reference on QEMU"),
    ("test_kernel_default.py", "public kernel IR selection"),
    ("test_font.py", "bitmap label font independent pixel oracle"),

    ("test_lineedit.py", "bounded ASCII state and actual keyboard edits"),

    ("test_gfx.py", "software RGB surface pixel oracle and QEMU execution"),

    ("test_fbinfo.py", "strict direct RGB framebuffer tag decoding"),
    ("test_kfont.py", "direct framebuffer font guarded RGB24/32 QEMU oracle"),
    ("test_console_state.py", "bounded display-only multi-line transcript model"),
    ("test_console_session.py", "GRUB multi-submission transcript and text pixels"),
    ("test_console_kernel.py", "GRUB keyboard console actual text pixels"),
    ("test_framebuffer_kernel.py", "GRUB framebuffer native image and guest pixels"),
    ("test_examples.py", "examples"),
    ("test_lsp.py", "language server"),
    ("test_docs.py", "docs"),
    ("test_selfhost.py", "self-hosted lexer/parser/fmt vs Python"),
    ("test_run.py", "hs run backend selection"),
    ("test_klink.py", "multiboot linker in hs vs Python kernel ELF"),
    ("test_asm32.py", "boot assembler in hs vs x64.Asm32"),
    ("test_asm.py", "assembler written in hs vs x64.py"),
    ("test_elf.py", "ELF writer written in hs vs x64.py"),
    ("test_irlib.py", "IR loader written in hs vs ir.py"),
    ("test_gcrt.py", "allocator/GC emitter written in hs vs gcrt.py"),
    ("test_normalize.py", "normalized parser AST in hs vs interp.py"),
    ("test_pipeline.py", "source-to-optimized-CFG pipeline in hs vs Python"),
    ("test_iropt_hs.py", "CFG optimizer in hs vs iropt.py (interp + x64)"),
    ("test_verify_hs.py", "CFG verifier in hs vs ir.py (valid + malformed modules)"),
    ("test_irbuild.py", "AST-to-IR builder in hs vs ir.py (interp + x64)"),
    ("test_ffi_variadic.py", "typed C variadic declaration and promoted ABI arguments"),
    ("test_ffi_u64.py", "negative U64 extern conversion before C side effect"),
    ("test_ffi_stack.py", "SysV stack arguments beyond integer and float registers"),
    ("test_ffi_registers.py", "independent SysV mixed FFI register banks"),
    ("test_call0.py", "unsafe zero-argument C ABI entry invocation"),
    ("test_native_jit_command.py", "Python-free eager JIT command"),
    ("test_jitsections.py", "unpacked JIT sections relink to identical ELF"),
    ("test_jitextern.py", "eager in-process dynamic symbol binding"),
    ("test_jit_sequence.py", "sequential independent native runtime/error teardown"),
    ("test_jit_status.py", "isolated native exception outcome and post-error heap teardown"),
    ("test_jit_owned.py", "normal-return target heap mapping destruction"),
    ("test_jit_return.py", "one-shot native module return, not mixed tiers"),
    ("test_jitrun.py", "experimental eager in-process hs JIT"),
    ("test_jitimage.py", "relocated RX code and RW data in hs"),
    ("test_jitmem.py", "executable-memory groundwork, W^X and generated code"),
    ("test_native_bundle.py", "relocated native directory without checkout/Python/gcc"),
    ("test_native_run.py", "one-command native source runner without Python/gcc"),
    ("test_hosted_seed.py", "verified seed + Python-free bootstrap"),
    ("test_native_kernel.py", "native kernel compiler complete ELF images"),
    ("test_native_kernel_ir.py", "native IR kernel compiler complete ELF images"),
    ("test_native_kernel_command.py", "Python-free native IR kernel command"),
    ("test_native_compiler.py", "native hs compiler image equality + full hosted fixed point"),
    ("test_compile_hs.py", "source-to-ELF compiler in hs vs Python backend"),
    ("test_be.py", "x64 backend written in hs vs irx64.py"),
    ("test_cc_holy.py", "small cc .holy bridge and self-repeat"),
    ("test_cc.py", "compiler written in hs (selfhost/cc.holy)"),
]


def main(argv):
    quick = "--quick" in argv
    failed = []
    for script, label in SUITES:
        if quick and script in ("test_xkernel.py", "test_kernel_ir.py", "test_timer_irq.py", "test_keyboard_queue.py", "test_kfont.py"):
            print(f"skip {script:18s} ({label}) -- quick mode")
            continue
        p = subprocess.run([sys.executable, os.path.join(HERE, script)],
                           capture_output=True, text=True)
        last = [ln for ln in p.stdout.strip().split("\n") if ln][-1:]
        summary = last[0] if last else f"exit {p.returncode}"
        mark = "ok  " if p.returncode == 0 else "FAIL"
        print(f"{mark} {script:18s} ({label}): {summary}")
        if p.returncode != 0:
            failed.append(script)
            # failure lines first: the tail of a long suite can hide them
            fl = [ln for ln in p.stdout.split("\n") if ln.startswith("FAIL")]
            if fl:
                print("\n".join(x[:1500] for x in fl[:30]))
            print(p.stdout[-4000:])
            print(p.stderr[-2000:])
    if failed:
        print(f"\n{len(failed)} suite(s) failed: {', '.join(failed)}")
        return 1
    print("\nall suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
