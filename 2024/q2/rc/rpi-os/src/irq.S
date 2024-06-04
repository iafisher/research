.globl irq_vector_init
// void irq_vector_init(void);
irq_vector_init:
	adr x0, vectors
	msr vbar_el1, x0
	ret

.globl enable_irq
// void enable_irq(void);
enable_irq:
	msr daifclr, #2
	ret

.globl disable_irq
// void disable_irq(void);
disable_irq:
	msr daifset, #2
	ret
