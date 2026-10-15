# Multiboot ELF32 wrapper around a long-mode payload and its relocations.
import asm32
import elf
BASE = 1048576
STACK = 16384
def zero(n):
  out = []
  for i in range(n):
    append(out, 0)
  return out
def put(out, off, bytes_):
  for i in range(len(bytes_)):
    out[off + i] = bytes_[i]
def align(n, a):
  return (n + a - 1) & (0 - a)
def ph(off, size, flags):
  return elf.u32(1) + elf.u32(off) + elf.u32(BASE + off) + elf.u32(BASE + off) + elf.u32(size) + elf.u32(size) + elf.u32(flags) + elf.u32(4096)
def link(p, stack_patch):
  code = p["code"][0:len(p["code"])]
  data = p["data"][0:len(p["data"])]
  labels = p["labels"]
  dl = p["data_labels"]
  mb2 = elf.u32(3897708758) + elf.u32(0) + elf.u32(48) + elf.u32(0 - 3897708758 - 48) + elf.u16(5) + elf.u16(1) + elf.u32(20) + elf.u32(640) + elf.u32(480) + elf.u32(32) + zero(4) + elf.u16(0) + elf.u16(0) + elf.u32(8)
  mb1 = elf.u32(464367618) + elf.u32(0) + elf.u32(0 - 464367618)
  mb_off = align(116, 8)
  boot_off = mb_off + len(mb2) + len(mb1)
  b = asm32.Asm32()
  b.label("_start")
  b.cli()
  b.mov_ri32_abs(4, "STACK_TOP")
  b.mov_rr(6, 0)
  b.mov_rr(2, 3)
  b.mov_mr_abs("MBMAGIC", 0)
  b.mov_mr_abs("MBINFO", 2)
  b.mov_ri32_abs(0, "PML4")
  b.mov_cr(3, 0)
  b.mov_rcr(0, 4)
  b.or_ri32(0, 1568)
  b.mov_cr(4, 0)
  b.mov_ri32(1, 3221225600)
  b.rdmsr()
  b.or_ri32(0, 257)
  b.wrmsr()
  b.mov_ri32(1, 3221225602)
  b.xor_rr(2, 2)
  b.mov_ri32_abs(0, "SYSCALL_STUB")
  b.wrmsr()
  b.mov_ri32(1, 3221225601)
  b.mov_ri32(0, 0)
  b.mov_ri32(2, 1048584)
  b.wrmsr()
  b.mov_ri32(1, 3221225604)
  b.mov_ri32(0, 512)
  b.xor_rr(2, 2)
  b.wrmsr()
  b.mov_rcr(0, 0)
  b.or_ri32(0, 2147483649)
  b.mov_cr(0, 0)
  b.lgdt_abs("GDT_PTR")
  b.ltr(40)
  b.jmp_far_abs(8, 0)
  gdt = zero(8) + [0, 0, 0, 0, 0, 154, 32, 0] + [0, 0, 0, 0, 0, 146, 0, 0] + [0, 0, 0, 0, 0, 242, 0, 0] + [0, 0, 0, 0, 0, 250, 32, 0] + zero(16)
  gdt_off = align(boot_off + len(b.code), 8)
  pay_off = gdt_off + len(gdt) + 10
  dat_off = pay_off + len(code)
  tbl_off = align(dat_off + len(data), 4096)
  stack_top = BASE + dat_off + dl["kstack_"] + STACK
  b.labels["STACK_TOP"] = stack_top - BASE
  b.labels["PML4"] = tbl_off
  b.labels["GDT_PTR"] = gdt_off + len(gdt)
  b.labels["MBINFO"] = dat_off + dl["mbinfo_"]
  b.labels["MBMAGIC"] = dat_off + dl["mbmagic_"]
  tss_base = BASE + dat_off + dl["tss_"]
  tss = [103, 0, tss_base & 255, tss_base >> 8 & 255, tss_base >> 16 & 255, 137, 15, tss_base >> 24 & 255] + elf.u64(tss_base >> 32)
  put(gdt, 40, tss)
  put(data, dl["tss_"] + 4, elf.u32(stack_top))
  put(data, dl["tss_"] + 66, elf.u16(104))
  put(data, dl["sc_swap_"], elf.u64(BASE + dat_off + dl["scstack_"] + STACK))
  b.labels["SYSCALL_STUB"] = pay_off + labels["syscall_entry"]
  boot = b.resolve(BASE)
  put(boot, len(boot) - 6, elf.u32(BASE + pay_off + labels["long_mode"]) + elf.u16(8))
  gdt_ptr = elf.u16(len(gdt) - 1) + elf.u64(BASE + gdt_off)
  tables = zero(12288)
  put(tables, 0, elf.u64((BASE + tbl_off + 4096) | 3))
  put(tables, 4096, elf.u64((BASE + tbl_off + 8192) | 3))
  for i in range(512):
    put(tables, 8192 + 8 * i, elf.u64((i * 2097152) | 131))
  for vec in range(48):
    addr = BASE + pay_off + labels["irq_stub_" + str(vec)]
    gate = elf.u16(addr & 65535) + elf.u16(8) + [0, 142] + elf.u16(addr >> 16 & 65535) + elf.u32(addr >> 32) + zero(4)
    put(data, dl["idt_"] + vec * 16, gate)
  put(data, dl["idtr_"], elf.u16(767) + elf.u64(BASE + dat_off + dl["idt_"]))
  for fix in p["fixups"]:
    if has(labels, fix[1]):
      target = BASE + pay_off + labels[fix[1]]
    elif has(dl, fix[1]):
      target = BASE + dat_off + dl[fix[1]]
    else:
      raise "undefined label " + fix[1]
    put(code, fix[0], elf.u32(target - (BASE + pay_off + fix[0] + 4)))
  image_end = BASE + tbl_off + 12288
  if stack_top > image_end:
    image_end = stack_top
  put(data, dl["imageend_"], elf.u64(image_end))
  put(code, stack_patch, elf.u64(stack_top))
  text = zero(mb_off - 116) + mb2 + mb1 + boot
  text = text + zero(gdt_off - 116 - len(text)) + gdt + gdt_ptr
  text = text + zero(pay_off - 116 - len(text)) + code
  file_data = data + zero(tbl_off - dat_off - len(data)) + tables
  header = [127, 69, 76, 70, 1, 1, 1] + zero(9) + elf.u16(2) + elf.u16(3) + elf.u32(1) + elf.u32(BASE + boot_off) + elf.u32(52) + elf.u32(0) + elf.u32(0) + elf.u16(52) + elf.u16(32) + elf.u16(2) + zero(6)
  return header + ph(0, dat_off, 5) + ph(dat_off, len(file_data), 6) + text + file_data
