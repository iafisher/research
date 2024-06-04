#include "mm.h"

static unsigned short mem_map[PAGING_PAGES] = {0};

#define MEM_TO_IDX(p) (((p) - LOW_MEMORY) / PAGE_SIZE)
#define IDX_TO_MEM(i) (LOW_MEMORY + (i)*PAGE_SIZE)

unsigned long get_free_page() {
  for (int i = 0; i < PAGING_PAGES; i++) {
    if (mem_map[i] == 0) {
      mem_map[i] = 1;
      return IDX_TO_MEM(i);
    }
  }

  return 0;
}

void free_page(unsigned long p) {
  mem_map[MEM_TO_IDX(p)] = 0;
}
