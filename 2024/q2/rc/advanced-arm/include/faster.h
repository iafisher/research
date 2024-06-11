#ifndef IAN_FASTER_H
#define IAN_FASTER_H

#include <stdint.h>

typedef uint64_t u64;

// The `asm` directive instructs Clang not to prefix the symbol name with an underscore.
int ian_add(int, int) asm("ian_add");
int ian_strlen(const char*) asm("ian_strlen");
void ian_rot13(char*) asm("ian_rot13");
void ian_overflow(void) asm("ian_overflow");

struct u64_or_overflow {
  u64 r;
  int v;
};

struct u64_or_overflow ian_add_check_overflow(u64, u64) asm("ian_add_check_overflow");

#endif /* IAN_FASTER_H */
