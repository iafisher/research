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
