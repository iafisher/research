#include <chrono>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <iterator>
#include <thread>
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

  elf::File elf;
  try {
    elf = elf::parse(reader);
  } catch (const char* e) {
    std::cerr << "error: " << e << std::endl;
    return 1;
  }

  std::cout << "Is 64 bit? " << (elf.is_64_bit ? "yes" : "no") << std::endl;
  std::cout << "Endianness? " << (elf.is_little_endian ? "little" : "big") << std::endl;
  std::cout << "ELF version? " << (int)elf.elf_version << std::endl;
  std::cout << "Object type? " << object_type_to_str(elf.object_type) << std::endl;
  std::cout << "ISA? " << elf.isa_type << std::endl;
  std::cout << "Entrypoint? 0x" << std::hex << elf.entrypoint << std::dec << std::endl;
  std::cout << "Program header? 0x" << std::hex << elf.program_header_index << std::dec << std::endl;
  std::cout << "Section header? 0x" << std::hex << elf.section_header_index << std::dec << std::endl;
  std::cout << "Program header size? " << elf.program_header_entry_size << std::endl;
  std::cout << "Program header length? " << elf.program_header_length << std::endl;
  std::cout << "Section header size? " << elf.section_header_entry_size << std::endl;
  std::cout << "Section header length? " << elf.section_header_length << std::endl;

  std::cout << std::endl;
  for (size_t i = 0; i < elf.program_headers.size(); i++) {
    elf::ProgramHeader& hdr = elf.program_headers[i];
    std::cout << "Program header " << (i + 1) << std::endl;
    std::cout << "  type:   " << elf::pheader_type_to_str(hdr.type) << std::endl;
    std::cout << "  offset: 0x" << std::hex << hdr.offset << std::dec << std::endl;
    std::cout << "  vaddr:  0x" << std::hex << hdr.vaddr << std::dec << std::endl;
    std::cout << "  filesz: 0x" << std::hex << hdr.filesz << std::dec << std::endl;
    std::cout << "  memsz:  0x" << std::hex << hdr.memsz << std::dec << std::endl;
  }

  std::cout << std::endl;
  for (size_t i = 0; i < elf.section_headers.size(); i++) {
    elf::SectionHeader& hdr = elf.section_headers[i];
    std::cout << "Section header " << (i + 1) << std::endl;
    std::cout << "  type:   " << elf::sheader_type_to_str(hdr.type) << std::endl;
    std::cout << "  offset: 0x" << std::hex << hdr.offset << std::dec << std::endl;
    std::cout << "  loadable? " << (hdr.flags & elf::SHF_ALLOC ? "yes" : "no") << std::endl;
  }

  ArmVirtualMachine vm;

  for (auto it = elf.program_headers.begin(); it != elf.program_headers.end(); it++) {
    elf::ProgramHeader& hdr = *it;
    if (hdr.type == 0x1) {
      size_t i = 0;
      for (; i < hdr.filesz; i++) {
        u8 v = bytes[hdr.offset + i];
        vm.memory.write_u8(hdr.vaddr + i, v);
      }

      for (; i < hdr.memsz; i++) {
        vm.memory.write_u8(hdr.vaddr + i, 0);
      }
    }
  }

  std::cout << std::endl << std::endl << std::endl;

  vm.ip = elf.entrypoint;
  while (1) {
    // std::cout << "vm: ip=0x" << std::hex << (int)vm.ip << std::dec << std::endl;
    u64 prev_ip = vm.ip;
    u32 inst_bytes = vm.memory.read_u32(vm.ip);
    if (inst_bytes == 0) {
      std::cout << "vm: null bytes; exiting" << std::endl;
      break;
    }

    std::unique_ptr<Instruction> inst = decode_arm_inst(inst_bytes);

    std::string label = inst->label();
    if (!label.empty()) {
      std::cout << "vm: op: ";
    }
    inst->print();

    inst->execute(vm);

    if (vm.ip == prev_ip) {
      std::cout << "vm: infinite loop; exiting" << std::endl;
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }

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
