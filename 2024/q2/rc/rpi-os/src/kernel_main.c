#include "fork.h"
#include "irq.h"
#include "printf.h"
#include "mini_uart.h"
#include "sched.h"
#include "timer.h"
#include "utils.h"

void example_process(char* array);

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

  int result = copy_process((unsigned long)&example_process, (unsigned long)"12345");
  if (result != 0) {
    printf("error: failed to start example process 1: result=%d\r\n", result);
    return;
  }

  result = copy_process((unsigned long)&example_process, (unsigned long)"abcde");
  if (result != 0) {
    printf("error: failed to start example process 2: result=%d\r\n", result);
    return;
  }

  while (1) {
    schedule();
    /* uart_send(uart_recv()); */
  }
}

void example_process(char* array) {
  while (1) {
    for (char* p = array; *p != '\0'; p++) {
      uart_send(*p);
      delay(100000);
    }
    uart_send('\r');
    uart_send('\n');
  }
}
