#ifndef RPI_OS_IRQ_H
#define RPI_OS_IRQ_H

void enable_interrupt_controller(void);
void irq_vector_init(void);
void enable_irq(void);
void disable_irq(void);

#endif  /* RPI_OS_IRQ_H */
