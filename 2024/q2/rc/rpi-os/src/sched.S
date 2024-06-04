#include "sched.h"

.globl cpu_switch_to
// void cpu_switch_to(struct task_struct* prev, struct task_struct* next);
cpu_switch_to:
    // x8 := &(prev_task->cpu_context)
    mov    x10, #THREAD_CPU_CONTEXT
    add    x8, x0, x10
    mov    x9, sp
    // store callee-saved registers
    // NOTE: the #16 suffix adds 16 to x8 after storing
    stp    x19, x20, [x8], #16
    stp    x21, x22, [x8], #16
    stp    x23, x24, [x8], #16
    stp    x25, x26, [x8], #16
    stp    x27, x28, [x8], #16
    stp    x29, x9, [x8], #16
    str    x30, [x8]
    // x9 := &(next_task->cpu_context)
    add    x8, x1, x10
    // restore callee-saved registers
    ldp    x19, x20, [x8], #16
    ldp    x21, x22, [x8], #16
    ldp    x23, x24, [x8], #16
    ldp    x25, x26, [x8], #16
    ldp    x27, x28, [x8], #16
    ldp    x29, x9, [x8], #16
    // load into link register (either ret_from_fork or the previous location in the task's
    // execution)
    ldr    x30, [x8]
    mov    sp, x9
    ret
