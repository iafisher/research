#include <iostream>

#include "armvm.h"

#define MEMORY_BLOCK_SIZE  4096
#define ptr_block(p)  ((p) & ~0xFFFULL)
#define ptr_index(p)  ((p) &  0xFFFULL)

void Memory::write_u8(u64 p, u8 v) {
    u64 blk = ptr_block(p);
    u64 idx = ptr_index(p);
    auto it = mapping_.find(blk);
    if (it == mapping_.end()) {
        u64 p = mem_.size();
        mapping_.insert({blk, p});
        for (int i = 0; i < MEMORY_BLOCK_SIZE; i++) {
            mem_.push_back(0);
        }
        mem_[p + idx] = v;
    } else {
        mem_[it->second + idx] = v;
    }
}

void Memory::write_u16(u64 p, u16 v) {
    write_u8(p, v & 0xFF);
    write_u8(p + 1, v & 0xFF00);
}

void Memory::write_u32(u64 p, u32 v) {
    write_u8(p, v & 0xFF);
    write_u8(p + 1, v & 0xFF00);
    write_u8(p + 2, v & 0xFF0000);
    write_u8(p + 3, v & 0xFF000000);
}

void Memory::write_u64(u64 p, u64 v) {
    write_u8(p, v & 0xFF);
    write_u8(p + 1, v & 0xFF00);
    write_u8(p + 2, v & 0xFF0000);
    write_u8(p + 3, v & 0xFF000000);
    write_u8(p + 4, v & 0xFF00000000);
    write_u8(p + 5, v & 0xFF0000000000);
    write_u8(p + 6, v & 0xFF000000000000);
    write_u8(p + 7, v & 0xFF00000000000000);
}

u8 Memory::read_u8(u64 p) {
    u64 blk = ptr_block(p);
    u64 idx = ptr_index(p);
    auto it = mapping_.find(blk);
    if (it == mapping_.end()) {
        std::cout << "mem: warning: reading uninitialized memory at 0x" << std::hex << p << std::dec << std::endl;
        return 0;
    } else {
        return mem_[it->second + idx];
    }
}

u16 Memory::read_u16(u64 p) {
    u16 b1 = read_u8(p);
    u16 b2 = read_u8(p + 1);
    return b1 + (b2 << 8);
}

u32 Memory::read_u32(u64 p) {
    u32 b1 = read_u8(p);
    u32 b2 = read_u8(p + 1);
    u32 b3 = read_u8(p + 2);
    u32 b4 = read_u8(p + 3);
    return b1 + (b2 << 8) + (b3 << 16) + (b4 << 24);
}

u64 Memory::read_u64(u64 p) {
    u64 b1 = read_u8(p);
    u64 b2 = read_u8(p + 1);
    u64 b3 = read_u8(p + 2);
    u64 b4 = read_u8(p + 3);
    u64 b5 = read_u8(p + 4);
    u64 b6 = read_u8(p + 5);
    u64 b7 = read_u8(p + 6);
    u64 b8 = read_u8(p + 7);
    return b1 + (b2 << 8) + (b3 << 16) + (b4 << 24) + (b5 << 32) + (b6 << 40) + (b7 << 48) + (b8 << 56);
}

void AddInstruction::execute(ArmVirtualMachine& vm) {
    // TODO: handle overflow and set flags
    u64 result = left_->load(vm) + right_->load(vm);
    dest_->store(vm, result);
    vm.next_ip();
}

void MovInstruction::execute(ArmVirtualMachine& vm) {
    dest_->store(vm, src_->load(vm));
    vm.next_ip();
}

void NopInstruction::execute(ArmVirtualMachine& vm) {
    vm.next_ip();
}

void UnknownInstruction::execute(ArmVirtualMachine& vm) {
    std::cout << "stupid" << std::endl;
    vm.next_ip();
}

std::unique_ptr<Instruction> decode_arm_inst(u32 bytes) {
    // b4 b3 b2 b1
    u8 b4 = bytes >> 24;
    u8 b3 = (bytes >> 16) & 0xFF;
    u8 b2 = (bytes >> 8) & 0xFF;
    u8 b1 = bytes & 0xFF;

    if (bytes == 0xd503201f) {
        return std::make_unique<NopInstruction>();
    } else if (b4 == 0xd2 && (b3 & 0b10000000) == 0b10000000) {
        // TODO: ignoring shift
        std::unique_ptr<Location> dest = std::make_unique<RegisterLocation>(b1 & 0b11111);
        std::unique_ptr<Location> src = std::make_unique<ConstantLocation>((bytes >> 5) & 0xFFFF);
        return std::make_unique<MovInstruction>(std::move(dest), std::move(src));
    } else if (b4 == 0xaa && (((b3 >> 6) & 0b11) == 0) && b2 == 0b11 && (b1 >> 5) == 0b111) {
        std::unique_ptr<Location> dest = std::make_unique<RegisterLocation>(b1 & 0b11111);
        std::unique_ptr<Location> src = std::make_unique<RegisterLocation>(b3 & 0b11111);
        return std::make_unique<MovInstruction>(std::move(dest), std::move(src));
    } else {
        // std::cout << "decode_arm: 0x" << std::hex << bytes << std::endl;
        return std::make_unique<UnknownInstruction>();
    }
}
