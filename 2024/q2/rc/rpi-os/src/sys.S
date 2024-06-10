#include "sys.h"


.globl call_sys_write
call_sys_write:
	mov w8, #SYS_WRITE
	svc #0
	ret


.globl call_sys_malloc
call_sys_malloc:
	mov w8, #SYS_MALLOC
	svc #0
	ret


.globl call_sys_clone
call_sys_clone:
	mov x10, x0
	mov x11, x1
	mov x12, x2

	mov x0, x2
	mov w8, #SYS_CLONE
	svc #0

	cmp x0, #0
	beq thread_start
	ret

thread_start:
	mov x29, 0
	mov x0, x11
	blr x10
	mov w8, #SYS_EXIT
	svc #0


.globl call_sys_exit
call_sys_exit:
	mov w8, #SYS_EXIT
	svc #0
	ret
