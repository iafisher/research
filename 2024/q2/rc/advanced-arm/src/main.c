#include <stdio.h>

#include "faster.h"

void add_check_overflow_print(u64, u64);

int main(int argc, char* argv[]) {
  int result = ian_add(20, 22);
  printf("ian_add result: %d\n", result);

  char s[] = "hello";
  result = ian_strlen(s);
  printf("ian_strlen result: %d\n", result);

  ian_rot13(s);
  printf("ian_rot13 result: %s\n", s);

  /* ian_overflow(); */

  add_check_overflow_print(20, 22);
  add_check_overflow_print(0xffffffffffffffff, 1);

  return 0;
}

void add_check_overflow_print(u64 x, u64 y) {
  struct u64_or_overflow r = ian_add_check_overflow(x, y);
  if (r.v) {
    printf("%llu + %llu = overflow!\n", x, y);
  } else {
    printf("%llu + %llu = %llu\n", x, y, r.r);
  }
}
