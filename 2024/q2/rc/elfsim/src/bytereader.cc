#include <fstream>
#include <iterator>

#include "bytereader.h"

bool ByteReader::done() {
    return pos_ >= bytes_.size();
}

u8 ByteReader::next() {
    if (done()) {
        throw "ByteReader exhausted";
    }

    u8 r = bytes_[pos_];
    pos_++;
    return r;
}

void ByteReader::skip(size_t n) {
    setpos_(pos_ + n);
}

void ByteReader::jump_to(size_t i) {
    setpos_(i);
}

u16 ByteReader::next_u16() {
    u16 b1 = next();
    u16 b2 = next();
    return b1 + (b2 << 8);
}

u32 ByteReader::next_u32() {
    u32 b1 = next();
    u32 b2 = next();
    u32 b3 = next();
    u32 b4 = next();
    return b1 + (b2 << 8) + (b3 << 16) + (b4 << 24);
}

u64 ByteReader::next_u64() {
    u64 b1 = next();
    u64 b2 = next();
    u64 b3 = next();
    u64 b4 = next();
    u64 b5 = next();
    u64 b6 = next();
    u64 b7 = next();
    u64 b8 = next();
    return b1 + (b2 << 8) + (b3 << 16) + (b4 << 24) + (b5 << 32) + (b6 << 40) + (b7 << 48) + (b8 << 56);
}

void ByteReader::setpos_(size_t i) {
    pos_ = i > bytes_.size() ? bytes_.size() : i;
}

std::vector<char> read_binary_file(const std::string& filename) {
  std::ifstream file(filename, std::ios::in | std::ios::binary);
  if (!file) {
    throw "could not open file";
  }

  std::istreambuf_iterator<char> start(file), end;
  std::vector<char> bytes(start, end);
  return bytes;
}
