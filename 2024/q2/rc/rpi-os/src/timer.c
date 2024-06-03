#include "peripherals/timer.h"
#include "printf.h"
#include "utils.h"

const unsigned int INTERVAL = 200000;
unsigned int current_value = 0;

// RPi's system timer increments a value after each clock cycle. This value is compared to a
// designated register (TIMER_C1); if they are the same, an IRQ is generated.

void timer_init() {
  // set an IRQ to occur after INTERVAL clock cycles
  current_value = get32(TIMER_CLO);
  current_value += INTERVAL;
  put32(TIMER_C1, current_value);
}

void handle_timer_irq() {
  // set the next iteration of the timer
  current_value += INTERVAL;
  put32(TIMER_C1, current_value);

  // acknowledge the interrupt
  put32(TIMER_CS, TIMER_CS_M1);

  printf("timer interrupt received\r\n");
}
