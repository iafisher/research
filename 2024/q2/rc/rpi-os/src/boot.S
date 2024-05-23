#include "mm.h"

.section ".text.boot"

.globl _start
_start:
	// check processor id and only run kernel for primary CPU
	mrs x0, mpidr_el1
	and x0, x0, #0xFF
	cbz x0, master
	b spin_forever

spin_forever:
	b spin_forever

master:
	adr x0, bss_begin
	adr x1, bss_end
	sub x1, x1, x0
	# call memzero(bss_begin, bss_end - bss_begin)
	bl memzero

	mov sp, #LOW_MEMORY
	bl kernel_main
