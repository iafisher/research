#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <vector>

#include "armvm.h"
#include "elf.h"
#include "types.h"

std::string parse_args(int argc, char* argv[]);
void usage_and_bail(void);

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

  ArmVirtualMachine vm;

  return 0;
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
