#include "arm/sysregs.h"
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
	// set some system registers to values defined in sysregs.h
	ldr x0, =SCTLR_VALUE_MMU_DISABLED
	msr sctlr_el1, x0

	ldr x0, =HCR_VALUE
	msr hcr_el2, x0

	ldr x0, =SCR_VALUE
	msr scr_el3, x0

	ldr x0, =SPSR_VALUE
	msr spsr_el3, x0

	// jump to el1_entry at end of exception handler
	adr x0, el1_entry
	msr elr_el3, x0

	eret

el1_entry:
	adr x0, bss_begin
	adr x1, bss_end
	sub x1, x1, x0
	# call memzero(bss_begin, bss_end - bss_begin)
	bl memzero

	mov sp, #LOW_MEMORY
	bl kernel_main
