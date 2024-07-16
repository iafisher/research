#ifndef __IAF_ELF_H__
#define __IAF_ELF_H__

#include "bytereader.h"
#include "types.h"

namespace elf {
    enum ObjectType: u16 {
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

    struct ProgramHeader {
        u32 type;
        u64 offset;
        u64 vaddr;
        u64 filesz;
        u64 memsz;
        u64 align;
    };

    struct SectionHeader {
        u32 name_index;
        u32 type;
        u64 flags;
        u64 addr;
        u64 offset;
        u64 size;
        u32 link;
        u32 info;
        u64 addralign;
        u64 entsize;
    };

    const u64 SHF_ALLOC = 0x2;

    struct File {
        bool is_64_bit;
        bool is_little_endian;
        u8 elf_version;
        u8 target_abi;
        ObjectType object_type;
        u16 isa_type;
        u64 entrypoint;
        u64 program_header_index;
        u64 section_header_index;
        u16 program_header_entry_size;
        u16 program_header_length;
        u16 section_header_entry_size;
        u16 section_header_length;
        u16 section_names_index;
        std::vector<ProgramHeader> program_headers;
        std::vector<SectionHeader> section_headers;
    };

    File parse(ByteReader&);
    const char* object_type_to_str(u16 object_type);
    const char* pheader_type_to_str(u16 header_type);
    const char* sheader_type_to_str(u16 header_type);
}

#endif
