#include "sched.h"

#include "irq.h"
#include "printf.h"

static struct task_struct init_task = {
  .cpu_context = {0,0,0,0,0,0,0,0,0,0,0,0,0},
  .state = 0,
  .counter = 0,
  .priority = 1,
  .preempt_count = 0,
};

struct task_struct* g_current = &(init_task);
struct task_struct* g_tasks[NTASKS] = { &(init_task), };
int g_num_running_tasks = 1;

void _schedule(void);

void preempt_disable() {
  g_current->preempt_count++;
}

void preempt_enable() {
  g_current->preempt_count--;
}

void schedule() {
  g_current->counter = 0;
  _schedule();
}

void schedule_tail() {
  preempt_enable();
}

void timer_tick() {
  g_current->counter--;
  if (g_current->counter > 0 || g_current->preempt_count > 0) {
    return;
  }

  g_current->counter = 0;

  enable_irq();
  _schedule();
  disable_irq();
}

void _schedule() {
  // note that preemption is disabled but interrupts are allowed
  preempt_disable();
  int next;
  while (1) {
    int c = -1;
    next = 0;

    // set next to the running task with the highest counter value
    for (int i = 0; i < NTASKS; i++) {
      struct task_struct* p = g_tasks[i];
      if (p && p->state == TASK_RUNNING && p->counter > c) {
        c = p->counter;
        next = i;
      }
    }

    if (c) {
      break;
    }

    // if no suitable task found, then increase each task's counter (bounded by 2*priority)
    for (int i = 0; i < NTASKS; i++) {
      struct task_struct* p = g_tasks[i];
      if (p) {
        p->counter = (p->counter >> 1) + p->priority;
      }
    }
  }

  printf("sched: switching to task %d\r\n", next);
  switch_to(g_tasks[next]);
  preempt_enable();
}

void switch_to(struct task_struct* next) {
  if (g_current == next) {
    return;
  }

  struct task_struct* prev = g_current;
  g_current = next;
  cpu_switch_to(prev, next);
}
