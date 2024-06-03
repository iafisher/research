#include "irq.h"
#include "printf.h"
#include "mini_uart.h"
#include "timer.h"
#include "utils.h"

void kernel_main(void) {
  uart_init();
  init_printf(0, putc);
  uart_send_string("Hello, world!\n");

  int el = get_el();
  printf("Exception level: %d\r\n", el);

  irq_vector_init();
  timer_init();
  enable_interrupt_controller();
  enable_irq();

  while (1) {
    uart_send(uart_recv());
  }
}
