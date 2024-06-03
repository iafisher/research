#include "entry.h"
#include "mm.h"
#include "sched.h"

int copy_process(unsigned long fn, unsigned long arg) {
  preempt_disable();
  struct task_struct* p = (struct task_struct*)get_free_page();
  if (!p) {
    return 1;
  }

  p->priority = g_current->priority;
  p->state = TASK_RUNNING;
  p->counter = p->priority;
  // disable preemption until scheduled
  p->preempt_count = 1;

  p->cpu_context.x19 = fn;
  p->cpu_context.x20 = arg;
  p->cpu_context.pc = (unsigned long)ret_from_fork;
  p->cpu_context.sp = (unsigned long)p + THREAD_SIZE;

  int pid = g_num_running_tasks++;
  g_tasks[pid] = p;
  preempt_enable();

  return 0;
}
