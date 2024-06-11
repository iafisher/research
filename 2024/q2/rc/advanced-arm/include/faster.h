#ifndef IAN_FASTER_H
#define IAN_FASTER_H

// The `asm` directive instructs Clang not to prefix the symbol name with an underscore.
int add_together(int, int) asm("add_together");

#endif /* IAN_FASTER_H */
