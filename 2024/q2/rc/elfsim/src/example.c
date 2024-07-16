#include <stdio.h>

int main(int argc, char* argv[]) {
    FILE* f = fopen("hello.txt", "w");
    fputs("Hello, world!\n", f);
    fclose(f);
    return 0;
}
