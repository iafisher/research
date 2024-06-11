#include <stdio.h>

#include "faster.h"

int main(int argc, char* argv[]) {
  int result = ian_add(20, 22);
  printf("ian_add result: %d\n", result);

  char s[] = "hello";
  result = ian_strlen(s);
  printf("ian_strlen result: %d\n", result);

  ian_rot13(s);
  printf("ian_rot13 result: %s\n", s);

  return 0;
}
