#include "elf.h"

using namespace elf;

const u8 ELF_ABI_SYSV = 0x00;
const u8 ELF_ABI_LINUX = 0x03;

void parse_program_headers(File& elf, ByteReader& reader);
void parse_section_headers(File& elf, ByteReader& reader);

File elf::parse(ByteReader& reader) {
  u8 b1 = reader.next();
  u8 b2 = reader.next();
  u8 b3 = reader.next();
  u8 b4 = reader.next();

  if (!(b1 == 0x7F && b2 == 0x45 && b3 == 0x4C && b4 == 0x46)) {
    throw "invalid ELF header: wrong magic number";
  }

  File elf;

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

  elf.object_type = (ObjectType)reader.next_u16();
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
  elf.program_header_index = reader.next_u64();
  elf.section_header_index = reader.next_u64();

  // skip flags
  reader.skip(4);
  // skip header size
  reader.skip(2);

  elf.program_header_entry_size = reader.next_u16();
  elf.program_header_length = reader.next_u16();
  elf.section_header_entry_size = reader.next_u16();
  elf.section_header_length = reader.next_u16();
  elf.section_names_index = reader.next_u16();

  parse_program_headers(elf, reader);
  parse_section_headers(elf, reader);

  return elf;
}

void parse_program_headers(File& elf, ByteReader& reader) {
    reader.jump_to(elf.program_header_index);
    for (size_t i = 0; i < elf.program_header_length; i++) {
        ProgramHeader hdr;
        hdr.type = reader.next_u32();
        // skip flags
        reader.skip(4);
        hdr.offset = reader.next_u64();
        hdr.vaddr = reader.next_u64();
        // skip paddr
        reader.skip(8);
        hdr.filesz = reader.next_u64();
        hdr.memsz = reader.next_u64();
        reader.skip(8);
        elf.program_headers.push_back(hdr);
    }
}

void parse_section_headers(File& elf, ByteReader& reader) {
    reader.jump_to(elf.section_header_index);
    for (size_t i = 0; i < elf.section_header_length; i++) {
        SectionHeader hdr;
        hdr.name_index = reader.next_u32();
        hdr.type = reader.next_u32();
        hdr.flags = reader.next_u64();
        hdr.addr = reader.next_u64();
        hdr.offset = reader.next_u64();
        hdr.size = reader.next_u64();
        hdr.link = reader.next_u32();
        hdr.info = reader.next_u32();
        hdr.addralign = reader.next_u64();
        hdr.entsize = reader.next_u64();
        elf.section_headers.push_back(hdr);
    }
}

const char* elf::object_type_to_str(u16 object_type) {
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

const char* elf::pheader_type_to_str(u16 header_type) {
    switch (header_type) {
    case 0x0:
        return "PT_NULL";
    case 0x1:
        return "PT_LOAD";
    case 0x2:
        return "PT_DYNAMIC";
    case 0x3:
        return "PT_INTERP";
    case 0x4:
        return "PT_NOTE";
    case 0x5:
        return "PT_SHLIB";
    case 0x6:
        return "PT_PHDR";
    case 0x7:
        return "PT_TLS";
    default:
        return "unknown";
    }
}

const char* elf::sheader_type_to_str(u16 header_type) {
    switch (header_type) {
    case 0x0:
        return "SHT_NULL";
    case 0x1:
        return "SHT_PROGBITS";
    case 0x2:
        return "SHT_SYMTAB";
    case 0x3:
        return "SHT_STRTAB";
    // TODO: more
    default:
        return "unknown";
    }
}
