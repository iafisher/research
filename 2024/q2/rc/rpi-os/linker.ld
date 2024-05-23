/* This file instructs the linker on how to lay out the OS image file.
 *
 * The RPi firmware will load the image and execute from the beginning, so we put the boot code
 * first.
 *
 * Next is the actual kernel code, plus read-only and writable data -- this is similar as to a
 * normal executable.
 *
 * Lastly we have the BSS data section, which is initialized to zero. The actual image file only
 * stores the section size for efficiency; we record `bss_begin` and `bss_end` symbols so that we
 * can initialize the section at start-up.
 */

SECTIONS
{
	.text.boot : { *(.text.boot) }
	.text : { *(.text) }
	.rodata : { *(.rodata) }
	.data : { *(.data) }
	/* Aligning the BSS section to an 8-byte boundary makes it easier to work with. */
	. = ALIGN(0x8);
	bss_begin = .;
	.bss : { *(.bss*) }
	bss_end = .;
}
