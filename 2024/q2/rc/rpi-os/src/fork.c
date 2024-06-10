#include "fork.h"

#include "entry.h"
#include "mm.h"
#include "printf.h"
#include "sched.h"

int copy_process(unsigned long clone_flags, unsigned long fn, unsigned long arg, unsigned long stack) {
  preempt_disable();
  struct task_struct* p = (struct task_struct*)get_free_page();
  if (!p) {
    preempt_enable();
    return 1;
  }

  struct pt_regs* child_regs = task_pt_regs(p);
  memzero((unsigned long)child_regs, sizeof(struct pt_regs));
  memzero((unsigned long)&p->cpu_context, sizeof(struct cpu_context));

  if (clone_flags & PF_KTHREAD) {
    p->cpu_context.x19 = fn;
    p->cpu_context.x20 = arg;
  } else {
    struct pt_regs* cur_regs = task_pt_regs(g_current);
    *child_regs = *cur_regs;
    child_regs->regs[0] = 0;
    child_regs->sp = stack + PAGE_SIZE;
    p->stack = stack;
  }

  p->flags = clone_flags;
  p->priority = g_current->priority;
  p->state = TASK_RUNNING;
  p->counter = p->priority;
  // disable preemption until scheduled
  p->preempt_count = 1;

  p->cpu_context.pc = (unsigned long)ret_from_fork;
  /* p->cpu_context.sp = (unsigned long)p + THREAD_SIZE; */
  p->cpu_context.sp = (unsigned long)child_regs;

  int pid = g_num_running_tasks++;
  if (pid >= NTASKS) {
    free_page((unsigned long)p);
    preempt_enable();
    return 1;
  }

  g_tasks[pid] = p;
  preempt_enable();
  return 0;
}

int move_to_user_mode(unsigned long pc) {
  printf("entering move_to_user_mode\r\n");
  struct pt_regs* regs = task_pt_regs(g_current);
  memzero((unsigned long)regs, sizeof *regs);
  regs->pc = pc;
  regs->pstate = PSR_MODE_EL0t;
  unsigned long stack = get_free_page();
  if (!stack) {
    return -1;
  }
  regs->sp = stack + PAGE_SIZE;
  g_current->stack = stack;
  printf("exiting move_to_user_mode\r\n");
  return 0;
}

struct pt_regs* task_pt_regs(struct task_struct* task) {
  unsigned long p = (unsigned long)task + THREAD_SIZE - sizeof(struct pt_regs);
  return (struct pt_regs*)p;
}
