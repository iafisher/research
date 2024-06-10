#include "fork.h"
#include "irq.h"
#include "printf.h"
#include "mini_uart.h"
#include "sched.h"
#include "sys.h"
#include "timer.h"
#include "utils.h"

void user_process1(char* array);
void user_process2(void);
void kernel_process(void);

void kernel_main(void) {
  uart_init();
  init_printf(0, putc);
  uart_send_string("Hello, world!\r\n");

  int el = get_el();
  printf("Exception level: %d\r\n", el);

  irq_vector_init();
  timer_init();
  enable_interrupt_controller();
  enable_irq();

  int result = copy_process(PF_KTHREAD, (unsigned long)&kernel_process, 0, 0);
  if (result != 0) {
    printf("error: failed to copy kernel process: result=%d\r\n", result);
    return;
  }

  printf("kernel main finished, invoking scheduler\r\n");
  while (1) {
    schedule();
  }
}

void kernel_process() {
  printf("Kernel process started. EL %d\r\n", get_el());
  int err = move_to_user_mode((unsigned long)&user_process2);
  printf("Kernel process: move_to_user_mode finished with result: %d.\r\n", err);
  if (err < 0) {
    printf("Error while moving process to user mode\r\n");
  }
}

void user_process1(char* array) {
  char buf[2] = {0};
  while (1) {
    for (char *p = array; *p != '\0'; p++) {
      buf[0] = *p;
      call_sys_write(buf);
      delay(100000);
    }
  }
}

void user_process2() {
  printf("User process 2 starting.\r\n");
  char buf[30] = {0};
  tfp_sprintf(buf, "User process started\r\n");
  call_sys_write(buf);

  unsigned long stack = call_sys_malloc();
  if (stack < 0) {
    printf("Error while allocating stack for process 1\r\n");
    return;
  }

  int err = call_sys_clone((unsigned long)&user_process1, (unsigned long)"12345", stack);
  if (err < 0) {
    printf("Error while cloning process 1\r\n");
    return;
  }

  stack = call_sys_malloc();
  if (stack < 0) {
    printf("Error while allocating stack for process 2\r\n");
    return;
  }

  err = call_sys_clone((unsigned long)&user_process1, (unsigned long)"abcde", stack);
  if (err < 0) {
    printf("Error while cloning process 2\r\n");
    return;
  }

  call_sys_exit();
}
