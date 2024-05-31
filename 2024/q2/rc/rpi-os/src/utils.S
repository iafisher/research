// void put32(unsigned long, unsigned int);
.globl put32
put32:
	str w1, [x0]
	ret

// unsigned int get32(unsigned long);
.globl get32
get32:
	ldr w0, [x0]
	ret

// void delay(unsigned long);
.globl delay
delay:
	subs x0, x0, #1
	bne delay
	ret

// int get_el(void);
.globl get_el
get_el:
	mrs x0, CurrentEl
	lsr x0, x0, #2
	ret
