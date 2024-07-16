#ifndef __IAF_ARMVM_H__
#define __IAF_ARMVM_H__

#include <iostream>
#include <map>
#include <memory>

#include "types.h"

class Memory {
public:
    void write_u8(u64 p, u8 v);
    void write_u16(u64 p, u16 v);
    void write_u32(u64 p, u32 v);
    void write_u64(u64 p, u64 v);

    u8 read_u8(u64 p);
    u16 read_u16(u64 p);
    u32 read_u32(u64 p);
    u64 read_u64(u64 p);

private:
    std::map<u64, u64> mapping_;
    std::vector<u8> mem_;
};

struct ArmVirtualMachine {
    u8 registers[31];
    u64 ip;
    Memory memory;

    void next_ip() {
        ip += 4;
    }
};

class Instruction {
public:
    virtual ~Instruction() = default;

    virtual void execute(ArmVirtualMachine& vm) = 0;
    virtual std::string label() = 0;
    virtual void print() = 0;
};

class Location {
public:
    virtual ~Location() = default;

    virtual u64 load(const ArmVirtualMachine& vm) = 0;
    virtual void store(ArmVirtualMachine& vm, u64 value) = 0;
    virtual void print() = 0;
};

class RegisterLocation: public Location {
public:
    RegisterLocation(u8 index): index_(index) {}

    u64 load(const ArmVirtualMachine& vm) {
        return vm.registers[index_];
    }

    void store(ArmVirtualMachine& vm, u64 value) {
        vm.registers[index_] = value;
    }

    void print() {
        std::cout << "x" << (int)index_;
    }

private:
    u8 index_;
};

class ConstantLocation: public Location {
public:
    ConstantLocation(u64 value): value_(value) {}

    u64 load(const ArmVirtualMachine& vm) {
        return value_;
    }

    void store(ArmVirtualMachine& vm, u64 value) {
        throw "attempted to store to a constant location";
    }

    void print() {
        std::cout << "#0x" << std::hex << value_ << std::dec;
    }

private:
    u64 value_;
};

class NopInstruction: public Instruction {
public:
    void execute(ArmVirtualMachine& vm);
    std::string label() { return "nop"; }
    void print() {
        std::cout << "nop" << std::endl;
    }
};

class UnknownInstruction: public Instruction {
public:
    void execute(ArmVirtualMachine& vm);
    std::string label() { return ""; }
    void print() {
        std::cout << "stupid" << std::endl;
    }
};

class BinaryInstruction: public Instruction {
public:
    BinaryInstruction(std::unique_ptr<Location> dest, std::unique_ptr<Location> src):
        dest_(std::move(dest)), src_(std::move(src)) {}

protected:
    std::unique_ptr<Location> dest_, src_;
};

class TernaryInstruction: public Instruction {
public:
    TernaryInstruction(std::unique_ptr<Location> dest, std::unique_ptr<Location> left, std::unique_ptr<Location> right):
        dest_(std::move(dest)), left_(std::move(left)), right_(std::move(right)) {}

protected:
    std::unique_ptr<Location> dest_, left_, right_;
};

class AddInstruction: public TernaryInstruction {
public:
    void execute(ArmVirtualMachine& vm);
    std::string label() { return "add"; }
    void print() {
        std::cout << "add ";
        dest_->print();
        std::cout << ", ";
        left_->print();
        std::cout << ", ";
        right_->print();
        std::cout << std::endl;
    }
};

class MovInstruction: public BinaryInstruction {
public:
    MovInstruction(std::unique_ptr<Location> dest, std::unique_ptr<Location> src):
        BinaryInstruction(std::move(dest), std::move(src)) {}

    void execute(ArmVirtualMachine& vm);
    std::string label() { return "mov"; }
    void print() {
        std::cout << "mov ";
        dest_->print();
        std::cout << ", ";
        src_->print();
        std::cout << std::endl;
    }
};

std::unique_ptr<Instruction> decode_arm_inst(u32);

#endif
