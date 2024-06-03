#ifndef RPI_OS_MINI_UART_H
#define RPI_OS_MINI_UART_H

void uart_init(void);
char uart_recv(void);
void uart_send(char c);
void uart_send_string(char* str);

void putc(void* p, char c);

#endif  /* RPI_OS_MINI_UART_H */
