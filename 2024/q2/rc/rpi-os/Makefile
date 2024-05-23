# The prefix for GCC and related tools to cross-compile to an Arm 64-bit system
ARMGNU ?= aarch64-linux-gnu

# -nostdlib: don't link to the C standard library
# -nostartfiles: don't use the standard start-up routine
# -ffreestanding: assume a 'freestanding' environment
# -mgeneral-regs-only: only use general-purpose Arm registers
C_OPS = -Wall -nostdlib -nostartfiles -ffreestanding -Iinclude -mgeneral-regs-only
ASM_OPS = -Iinclude

BUILD_DIR = build
SRC_DIR = src
LINKER_FILE = $(SRC_DIR)/linker.ld

all: kernel8.img

.PHONY: clean
clean:
	rm -rf $(BUILD_DIR) *.img

# Makefile refresher:
#   $< is the input filename.
#   $@ is the output filename.

$(BUILD_DIR)/%_c.o: $(SRC_DIR)/%.c
	mkdir -p $(@D)
	# -MMD: create dependency files
	$(ARMGNU)-gcc $(C_OPS) -MMD -c $< -o $@

$(BUILD_DIR)/%_s.o: $(SRC_DIR)/%.S
	$(ARMGNU)-gcc $(ASM_OPS) -MMD -c $< -o $@

C_FILES = $(wildcard $(SRC_DIR)/*.c)
ASM_FILES = $(wildcard $(SRC_DIR)/*.S)
OBJ_FILES = $(C_FILES:$(SRC_DIR)/%.c=$(BUILD_DIR)/%_c.o)
OBJ_FILES += $(ASM_FILES:$(SRC_DIR)/%.S=$(BUILD_DIR)/%_s.o)

DEP_FILES = $(OBJ_FILES:%.o=%.d)
-include $(DEP_FILES)

kernel8.img: $(LINKER_FILE) $(OBJ_FILES)
	$(ARMGNU)-ld -T $(LINKER_FILE) -o $(BUILD_DIR)/kernel8.elf $(OBJ_FILES)
	$(ARMGNU)-objcopy $(BUILD_DIR)/kernel8.elf -O binary $@
