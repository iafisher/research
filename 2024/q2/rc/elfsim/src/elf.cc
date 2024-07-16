#include "elf.h"

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
  if (elf.target_abi != ELF_ABI_SYSV && elf.target_abi != ELF_ABI_LINUX) {
    throw "non-Linux ABI not supported";
  }

  // ignore ABI version
  b1 = reader.next();

  // skip padding bytes
  reader.skip(7);

  elf.object_type = (ElfObjectType)reader.next_u16();
  elf.isa_type = reader.next_u16();

  if (elf.isa_type != ARM64)
  {
    throw "non-ARM processor not supported";
  }

  u32 w1 = reader.next_u32();
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

  elf.program_header_entry_size = reader.next_u16();
  elf.program_header_length = reader.next_u16();
  elf.section_header_entry_size = reader.next_u16();
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
