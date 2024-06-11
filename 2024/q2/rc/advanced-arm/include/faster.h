#ifndef IAN_FASTER_H
#define IAN_FASTER_H

// The `asm` directive instructs Clang not to prefix the symbol name with an underscore.
int ian_add(int, int) asm("ian_add");
int ian_strlen(const char*) asm("ian_strlen");

#endif /* IAN_FASTER_H */
