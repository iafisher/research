#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

std::string parse_args(int argc, char* argv[]);
void usage_and_bail(void);
std::vector<char> read_binary_file(const std::string& filename);

struct ELF {
  bool is_64_bit;
  bool is_little_endian;
};

class ByteReader {
public:
  ByteReader(std::vector<char> bytes): bytes_(bytes) {}

  bool done() {
    return pos_ >= bytes_.size();
  }

  char next() {
    if (done()) {
      throw "ByteReader exhausted";
    }

    return bytes_[pos_++];
  }
private:
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

  return 0;
}

ELF parse_elf(ByteReader& reader) {
  char b1 = reader.next();
  char b2 = reader.next();
  char b3 = reader.next();
  char b4 = reader.next();

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

  return elf;
}

std::vector<char> read_binary_file(const std::string& filename) {
  std::ifstream file(filename, std::ios::in | std::ios::binary);
  if (!file) {
    throw "could not open file";
  }

  std::istream_iterator<char> start(file), end;
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
