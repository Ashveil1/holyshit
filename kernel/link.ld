/* holyshit kernel link (เฟส 5a): 64-bit ELF, loaded at 1MB. */
OUTPUT_FORMAT("elf64-x86-64")
OUTPUT_ARCH(i386:x86-64)
ENTRY(_start)

SECTIONS {
    . = 0x100000;
    .boot : {
        *(.mb2) *(.mb1) *(.text) *(.text.*)
    }
    .rodata : {
        *(.rodata) *(.rodata.*)
    }
    .data : {
        *(.data) *(.data.*)
    }
    .bss : {
        *(.bss) *(.bss.*) *(COMMON)
        . = ALIGN(4096);
        hs_heap_start = .;
        . += 16M;
        hs_heap_end = .;
    }
}
