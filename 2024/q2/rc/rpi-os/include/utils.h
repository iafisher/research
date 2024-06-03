#ifndef RPI_OS_UTILS_H
#define RPI_OS_UTILS_H

void delay(unsigned long);
void put32(unsigned long, unsigned int);
unsigned int get32(unsigned long);
int get_el(void);

#endif  /* RPI_OS_UTILS_H */
