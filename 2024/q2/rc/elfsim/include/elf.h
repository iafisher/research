#ifndef __IAF_ELF_H__
#define __IAF_ELF_H__

#include "bytereader.h"
#include "types.h"

enum ElfObjectType: u16
{
    ET_NONE = 0x00,
    ET_REL = 0x01,
    ET_EXEC = 0x02,
    ET_DYN = 0x03,
    ET_CORE = 0x04,
    ET_LOOS = 0xFE00,
    ET_HIOS = 0xFEF,
    ET_LOPROC = 0xFF00,
    ET_HIPROC = 0xFFF
};

struct ELF {
  bool is_64_bit;
  bool is_little_endian;
  u8 elf_version;
  u8 target_abi;
  ElfObjectType object_type;
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

ELF parse_elf(ByteReader&);
const char* object_type_to_str(u16 object_type);

#endif
