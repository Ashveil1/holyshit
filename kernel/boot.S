// holyshit kernel boot (เฟส 5a): multiboot1+2 -> 32-bit entry -> long mode.
// Machine state at _start: 32-bit protected mode, paging off, EAX=magic, EBX=info.
.code32

// ---- multiboot2 header (must be in first 32K, 8-byte aligned) ----
.section .mb2, "a", @progbits
.align 8
mb2_start:
    .long 0xE85250D6            # magic
    .long 0                     # i386 arch
    .long mb2_end - mb2_start   # header length
    .long -(0xE85250D6 + (mb2_end - mb2_start))  # checksum
    .word 0, 0                  # end tag
    .long 8
mb2_end:

// ---- multiboot1 header (first 8K, 4-byte aligned) ----
.section .mb1, "a", @progbits
.align 4
mb1_start:
    .long 0x1BADB002
    .long 0x0
    .long -(0x1BADB002 + 0x0)

.section .bss, "aw", @nobits
.align 4096
pml4:
    .skip 4096
pdpt:
    .skip 4096
pd:
    .skip 4096
stack_bottom:
    .skip 16384
stack_top:

.section .text
.code32
.globl _start
.type _start, @function
_start:
    cli
    mov $stack_top, %esp
    mov %eax, %esi              # save boot magic
    mov %ebx, %edx              # save boot info pointer

    # clear 3 page-table pages (3*1024 dwords)
    xor %eax, %eax
    mov $pml4, %edi
    mov $3072, %ecx
1:
    movl %eax, (%edi)
    add $4, %edi
    dec %ecx
    jnz 1b

    # pml4[0] = pdpt | present|writable
    mov $pdpt, %eax
    or $0x3, %eax
    mov %eax, pml4

    # pdpt[0] = pd | present|writable
    mov $pd, %eax
    or $0x3, %eax
    mov %eax, pdpt

    # pd[i] = i*2MB | present|writable|huge  (identity map 0..1GB)
    mov $pd, %edi
    mov $0x83, %eax
    mov $512, %ecx
1:
    mov %eax, (%edi)
    add $0x200000, %eax
    add $8, %edi
    dec %ecx
    jnz 1b

    # cr3 = pml4
    mov $pml4, %eax
    mov %eax, %cr3

    # CR4: PAE (bit5) + OSFXSR+OSXMMEXCPT (bits 9,10) so SSE is legal
    mov %cr4, %eax
    or $0x620, %eax
    mov %eax, %cr4

    # EFER: LME (bit8)
    mov $0xC0000080, %ecx
    rdmsr
    or $0x100, %eax
    wrmsr

    # CR0: PG (bit31) + PE (bit0)
    mov %cr0, %eax
    or $0x80000001, %eax
    mov %eax, %cr0

    lgdt gdt64_ptr
    ljmp $0x08, $long_mode

.code64
long_mode:
    mov $0x10, %ax
    mov %ax, %ds
    mov %ax, %es
    mov %ax, %fs
    mov %ax, %gs
    mov %ax, %ss
    mov $stack_top, %rsp
    mov %esi, %edi              # arg1 = boot magic (zero-extended)
    mov %edx, %esi              # arg2 = boot info (zero-extended)
    call hs_kernel_main
    cli
1:
    hlt
    jmp 1b

.section .rodata
.align 8
gdt64:
    .quad 0x0000000000000000
    .quad 0x00209A0000000000   # code: exec/read, long mode
    .quad 0x0000920000000000   # data: read/write
gdt64_ptr:
    .word gdt64_ptr - gdt64 - 1
    .quad gdt64
