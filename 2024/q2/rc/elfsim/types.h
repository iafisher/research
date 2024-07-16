#ifndef __ELF_H__
#define __ELF_H__

#include <cstdint>

typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;

enum ELF_VERSION : u16
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

enum ELF_ISA : u16
{
    NONE = 0x00,
    ATT2100 = 0x01,
    SPARC = 0x02,
    X86 = 0x03,
    M68K = 0x04,
    M88K = 0x05,
    INTEL_MCU = 0x06,
    INTEL_80860 = 0x07,
    MIPS = 0x08,
    IBM_SYSTEM_370 = 0x09,
    MIPS_RS3000_LE = 0x0A,
    HP_PA_RICS = 0x0F,
    INTEL_80960 = 0x13,
    POWER_PC = 0x14,
    POWER_PC_64 = 0x15,
    S390 = 0x16,
    IBM_SPU = 0x17,
    NEC_V800 = 0x24,
    FUJITSU_FR20 = 0x25,
    TRW_RW = 0x26,
    MOTOROLA_RCE = 0x27,
    ARM_V7 = 0x28,
    DIGITAL_ALPHA = 0x29,
    SUPER_H = 0x2A,
    SPARC_9 = 0x2B,
    SIEMENS_TRI_CORE = 0x2C,
    ARGONAUT_RISC = 0x2D,
    HITACHI_H8_300 = 0x2E,
    HITACHI_H8_300H = 0x2F,
    HITACHI_H8S = 0x30,
    HITACHI_H8_500 = 0x31,
    IA64 = 0x32,
    STANFORD_MIPS_X = 0x33,
    MOTOROLA_COLD_FIRE = 0x34,
    MOTOROLA_M68HC12 = 0x35,
    FUJITSU_MMA = 0x36,
    SIEMENS_PCP = 0x37,
    SONY_EMBEDDED_RISC = 0x38,
    DENSO_NDR1 = 0x39,
    MOTOROLA_STAR_CORE = 0x3A,
    TOYOTA_ME16 = 0x3B,
    ST100 = 0x3C,
    ALC_TINY_J = 0x3D,
    AMD_X86_64 = 0x3E,
    SONY_DSP = 0x3F,
    PDP10 = 0x40,
    PDP11 = 0x41,
    SIEMENS_FX66 = 0x42,
    ST9_8 = 0x43,
    ST7_8 = 0x44,
    MOTOROLA_MC68HC16 = 0x45,
    MOTOROLA_MC68HC11 = 0x46,
    MOTOROLA_MC68HC08 = 0x47,
    MOTOROLA_MC68HC05 = 0x48,
    S_VX = 0x49,
    ST_19_8 = 0x4A,
    DIGITAL_VAX = 0x4B,
    AXIS_32 = 0x4C,
    INFINEON_32 = 0x4D,
    ELEMENT_14_64 = 0x4E,
    LSI_LOGIC_16 = 0x4F,
    TMS320C6000 = 0x8C,
    MCST_ELBRUS_E2K = 0xAF,
    ARM64 = 0xB7,
    ZILOG_Z80 = 0xDC,
    RISC_V = 0xF3,
    BPF = 0xF7,
    WDC_65C816 = 0x101,
    LOONG_ARCH = 0x102,
};

#endif // __ELF_H__
