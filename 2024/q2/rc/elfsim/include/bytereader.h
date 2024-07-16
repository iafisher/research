#ifndef __IAF_BYTE_READER_H__
#define __IAF_BYTE_READER_H__

#include <vector>

#include "types.h"

class ByteReader {
public:
  ByteReader(std::vector<char> bytes): bytes_(bytes) {}

  bool done();
  u8 next();
  void skip(size_t n);
  void jump_to(size_t i);
  u16 next_u16();
  u32 next_u32();
  u64 next_u64();
private:
  void setpos_(size_t i);

  std::vector<char> bytes_;
  size_t pos_ = 0;
};

std::vector<char> read_binary_file(const std::string& filename);

#endif
