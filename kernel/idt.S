// holyshit kernel traps (เฟส 5b): CPU exception stubs (0-31) + IRQ stubs.
// All handlers run in 64-bit long mode. Exceptions print + halt (no return).
// IRQs save/restore all GPRs, call C handlers, then iretq.

.macro EXC n, has_err
.globl hs_exc\n
hs_exc\n:
.if \has_err == 0
    pushq $0
.endif
    pushq $\n
    mov 16(%rsp), %rdx      # RIP
    mov 8(%rsp), %rsi       # error code
    mov (%rsp), %rdi        # vector
    add $16, %rsp
    call hs_exc_c
    cli
1:  hlt
    jmp 1b
.endm

EXC 0,0
EXC 1,0
EXC 2,0
EXC 3,0
EXC 4,0
EXC 5,0
EXC 6,0
EXC 7,0
EXC 8,1
EXC 9,0
EXC 10,1
EXC 11,1
EXC 12,1
EXC 13,1
EXC 14,1
EXC 15,0
EXC 16,0
EXC 17,1
EXC 18,0
EXC 19,0
EXC 20,0
EXC 21,1
EXC 22,0
EXC 23,0
EXC 24,0
EXC 25,0
EXC 26,0
EXC 27,0
EXC 28,0
EXC 29,1
EXC 30,0
EXC 31,0

.macro PUSH_ALL
    push %rax
    push %rcx
    push %rdx
    push %rbx
    push %rbp
    push %rsi
    push %rdi
    push %r8
    push %r9
    push %r10
    push %r11
    push %r12
    push %r13
    push %r14
    push %r15
.endm

.macro POP_ALL
    pop %r15
    pop %r14
    pop %r13
    pop %r12
    pop %r11
    pop %r10
    pop %r9
    pop %r8
    pop %rdi
    pop %rsi
    pop %rbp
    pop %rbx
    pop %rdx
    pop %rcx
    pop %rax
.endm

.globl hs_irq0_stub
hs_irq0_stub:
    PUSH_ALL
    cld
    call hs_irq0
    POP_ALL
    iretq

.globl hs_irq1_stub
hs_irq1_stub:
    PUSH_ALL
    cld
    xor %edi, %edi
    in $0x60, %al
    mov %eax, %edi
    call hs_irq1
    POP_ALL
    iretq
