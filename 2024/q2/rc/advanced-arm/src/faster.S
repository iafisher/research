// int ian_add(int, int)
.globl ian_add
ian_add:
	add x0, x0, x1
	ret

// int ian_strlen(const char*)
.globl ian_strlen
ian_strlen:
	eor x2, x2, x2
ian_strlen_loop:
	ldrb w1, [x0, x2]
	cbz x1, ian_strlen_done
	add x2, x2, #1
	b ian_strlen_loop
ian_strlen_done:
	mov x0, x2
	ret

// void ian_rot13(char*)
.globl ian_rot13
ian_rot13:
ian_rot13_loop:
	ldrb w1, [x0]
	cbz w1, ian_rot13_end
	sub w1, w1, 97
	add w1, w1, 13
	cmp w1, 26
	b.lt ian_rot13_no_mod
	sub w1, w1, 13
ian_rot13_no_mod:
	add w1, w1, 97
	strb w1, [x0], #1
	b ian_rot13_loop
ian_rot13_end:
	ret

// void ian_overflow(void)
.globl ian_overflow
ian_overflow:
	mov x8, 0xffffffffffffffff
	mov x9, 0xffffffffffffffff
	add x10, x8, x9
	ret

// struct { u64, int } ian_add_check_overflow(u64, u64)
.globl ian_add_check_overflow
ian_add_check_overflow:
	adds x0, x0, x1
	cset x1, cs
	ret
