#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

#include "types.h"

std::string parse_args(int argc, char* argv[]);
void usage_and_bail(void);
std::vector<char> read_binary_file(const std::string& filename);
const char* object_type_to_str(u16 object_type);

struct ELF {
  bool is_64_bit;
  bool is_little_endian;
  u8 elf_version;
  u8 target_abi;
  u16 object_type;
  u16 isa_type;
  u64 entrypoint;
  u64 program_header;
  u64 section_header;
  u16 program_header_entry_size;
  u16 program_header_length;
  u16 section_header_entry_size;
  u16 section_header_length;
  u16 section_names_index;
};

class ByteReader {
public:
  ByteReader(std::vector<char> bytes): bytes_(bytes) {}

  bool done() {
    return pos_ >= bytes_.size();
  }

  u8 next() {
    if (done()) {
      throw "ByteReader exhausted";
    }

    u8 r = bytes_[pos_];
    std::cout << "reader: index " << std::hex << "0x" << pos_ << "  0x" << (int)r << std::dec << std::endl;
    pos_++;
    return r;
  }

  void skip(size_t n) {
    std::cout << "reader: skip " << n << std::endl;
    setpos_(pos_ + n);
  }

  void jump_to(size_t i) {
    setpos_(i);
  }

  u16 next_u16() {
    std::cout << "next_u16: start: " << std::hex << "0x" << pos_ << std::dec << std::endl;
    u16 b1 = next();
    u16 b2 = next();
    std::cout << "next_u16: end: " << std::hex << "0x" << pos_ << std::dec << std::endl;
    u16 r = b1 + (b2 << 8);
    std::cout << "next_u16: b1: " << std::hex << "0x" << b1 << std::dec << std::endl;
    std::cout << "next_u16: b2: " << std::hex << "0x" << b2 << std::dec << std::endl;
    std::cout << "next_u16: result: " << std::hex << "0x" << r << std::dec << std::endl;
    return r;
  }

  u32 next_u32() {
    u32 b1 = next();
    u32 b2 = next();
    u32 b3 = next();
    u32 b4 = next();
    return b1 + (b2 << 8) + (b3 << 16) + (b4 << 24);
  }

  u64 next_u64() {
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
private:
  void setpos_(size_t i) {
    pos_ = i > bytes_.size() ? bytes_.size() : i;
  }

  std::vector<char> bytes_;
  size_t pos_ = 0;
};

ELF parse_elf(ByteReader&);

int main(int argc, char* argv[]) {
  std::string filename = parse_args(argc, argv);

  std::vector<char> bytes = read_binary_file(filename);
  std::cout << "Bytes: " << bytes.size() << std::endl;

  ByteReader reader(bytes);

  ELF elf;
  try {
    elf = parse_elf(reader);
  } catch (const char* e) {
    std::cerr << "error: " << e << std::endl;
    return 1;
  }

  std::cout << "Is 64 bit? " << (elf.is_64_bit ? "yes" : "no") << std::endl;
  std::cout << "Endianness? " << (elf.is_little_endian ? "little" : "big") << std::endl;
  std::cout << "ELF version? " << (int)elf.elf_version << std::endl;
  std::cout << "Object type? " << object_type_to_str(elf.object_type) << std::endl;
  std::cout << "ISA? " << elf.isa_type << std::endl;
  std::cout << "Entrypoint? " << elf.entrypoint << std::endl;
  std::cout << "Program header? " << elf.program_header << std::endl;
  std::cout << "Section header? " << elf.section_header << std::endl;
  std::cout << "Program header size? " << elf.program_header_entry_size << std::endl;
  std::cout << "Program header length? " << elf.program_header_length << std::endl;
  std::cout << "Section header size? " << elf.section_header_entry_size << std::endl;
  std::cout << "Section header length? " << elf.section_header_length << std::endl;
  return 0;
}

const u8 ELF_ABI_SYSV = 0x00;
const u8 ELF_ABI_LINUX = 0x03;

ELF parse_elf(ByteReader& reader) {
  u8 b1 = reader.next();
  u8 b2 = reader.next();
  u8 b3 = reader.next();
  u8 b4 = reader.next();

  if (!(b1 == 0x7F && b2 == 0x45 && b3 == 0x4C && b4 == 0x46)) {
    throw "invalid ELF header: wrong magic number";
  }

  ELF elf;

  b1 = reader.next();
  if (b1 == 1) {
    elf.is_64_bit = false;
  } else if (b1 == 2) {
    elf.is_64_bit = true;
  } else {
    throw "invalid ELF header: expected EI_CLASS to be 1 or 2";
  }

  b1 = reader.next();
  if (b1 == 1) {
    elf.is_little_endian = true;
  } else if (b1 == 2) {
    elf.is_little_endian = false;
  } else {
    throw "invalid ELF header: expected EI_DATA to be 1 or 2";
  }

  b1 = reader.next();
  if (b1 == 1) {
    elf.elf_version = 1;
  } else {
    throw "invalid ELF header: expected EI_VERSION to be 1";
  }

  b1 = reader.next();
  elf.target_abi = b1;
  std::cout << "abi: " << (int)elf.target_abi << std::endl;
  if (elf.target_abi != ELF_ABI_SYSV && elf.target_abi != ELF_ABI_LINUX) {
    throw "non-Linux ABI not supported";
  }

  // ignore ABI version
  b1 = reader.next();

  // skip padding bytes
  reader.skip(7);

  elf.object_type = reader.next_u16();
  elf.isa_type = reader.next_u16();

  std::cout << "ISA type: " << elf.isa_type << std::endl;
  if (elf.isa_type != ARM64)
  {
    throw "non-ARM processor not supported";
  }

  u32 w1 = reader.next_u32();
  std::cout << "EI_VERSION2: " << w1 << std::endl;
  if (w1 != 1) {
    throw "invalid ELF header: expected second EI_VERSION to be 1";
  }

  elf.entrypoint = reader.next_u64();
  elf.program_header = reader.next_u64();
  elf.section_header = reader.next_u64();

  // skip flags
  reader.skip(4);
  // skip header size
  reader.skip(2);

  std::cout << "elf: program_header_entry_size" << std::endl;
  elf.program_header_entry_size = reader.next_u16();
  std::cout << "elf: program_header_length" << std::endl;
  elf.program_header_length = reader.next_u16();
  std::cout << "elf: section_header_entry_size" << std::endl;
  elf.section_header_entry_size = reader.next_u16();
  std::cout << "elf: section_header_length" << std::endl;
  elf.section_header_length = reader.next_u16();
  elf.section_names_index = reader.next_u16();

  return elf;
}

const char* object_type_to_str(u16 object_type) {
  switch (object_type) {
    case ET_NONE:
      return "unknown";
    case ET_REL:
      return "relocatable file";
    case ET_EXEC:
      return "executable file";
    case ET_DYN:
      return "shared object";
    case ET_CORE:
      return "core file";
    case ET_LOOS:
      return "ET_LOOS";
    case ET_HIOS:
      return "ET_HIOS";
    case ET_LOPROC:
      return "ET_LOPROC";
    case ET_HIPROC:
      return "ET_HIPROC";
    default:
      return "unknown";
  }
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

std::string parse_args(int argc, char* argv[]) {
  if (argc != 2) {
    usage_and_bail();
  }

  std::string arg(argv[1]);
  if (arg.size() == 0 || arg[0] == '-') {
    usage_and_bail();
  }

  return arg;
}

void usage_and_bail(void) {
  std::cerr << "usage: elfsim <file>" << std::endl;
  std::exit(1);
}
