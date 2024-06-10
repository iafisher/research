#ifndef RPI_OS_SYS
#define RPI_OS_SYS

#define NUM_SYSCALLS 4
#define SYS_WRITE  0
#define SYS_MALLOC 1
#define SYS_CLONE  2
#define SYS_EXIT   3

#ifndef __ASSEMBLER__

void sys_write(char* buf);
int sys_fork(void);

void call_sys_write(char* buf);
int call_sys_clone(unsigned long fn, unsigned long arg, unsigned long stack);
unsigned long call_sys_malloc(void);
void call_sys_exit(void);

#endif

#endif /* RPI_OS_SYS */
