#ifndef RPI_OS_SCHED_H
#define RPI_OS_SCHED_H

// offset of cpu_context in task_struct
#define THREAD_CPU_CONTEXT 0

#ifndef __ASSEMBLER__

#define THREAD_SIZE 4096
#define NTASKS 64
#define TASK_RUNNING 0

extern struct task_struct* g_current;
extern struct task_struct* g_tasks[NTASKS];
extern int g_num_running_tasks;

struct cpu_context {
    /* on ARM registers x19-x30 are callee-save */
    unsigned long x19;
    unsigned long x20;
    unsigned long x21;
    unsigned long x22;
    unsigned long x23;
    unsigned long x24;
    unsigned long x25;
    unsigned long x26;
    unsigned long x27;
    unsigned long x28;
    unsigned long fp;
    unsigned long sp;
    unsigned long pc;
};

struct task_struct {
  struct cpu_context cpu_context;
  /* TASK_RUNNING, etc. */
  long state;
  /* how long has the current task been running */
  long counter;
  /* task's base priority */
  long priority;
  /* if non-zero, task is doing something critical and should not be preempted */
  long preempt_count;
};

void sched_init(void);
void schedule(void);
void timer_tick(void);
void preempt_disable(void);
void preempt_enable(void);
void switch_to(struct task_struct* next);
void cpu_switch_to(struct task_struct* prev, struct task_struct* next);

#endif
#endif  /* RPI_OS_SCHED_H */
