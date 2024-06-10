// void memcpy(void* dest, void* src, size_t n)
//
// The C compiler may insert references to `memcpy` even if the program never uses it
// explicitly, so we need to define it for linking.
.globl memcpy
memcpy:
	ldr x3, [x1], #8
	str x3, [x0], #8
	subs x2, x2, #8
	b.gt memcpy
	ret

// void memzero(unsigned long src, unsigned long n);
.globl memzero
memzero:
	str xzr, [x0], #8
	subs x1, x1, #8
	b.gt memzero
	ret
