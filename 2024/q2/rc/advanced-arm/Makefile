CC ?= clang
AS ?= as
LD ?= ld

BUILD_DIR = build
SRC_DIR = src
INCLUDE_DIR = include
MAIN = $(BUILD_DIR)/main

CC_OPS = -Wall -I$(INCLUDE_DIR) -g -O0
AS_OPS = -g -arch arm64

all: $(MAIN)

.PHONY: clean
clean:
	rm $(BUILD_DIR)/*

C_FILES = $(wildcard $(SRC_DIR)/*.c)
ASM_FILES = $(wildcard $(SRC_DIR)/*.S)
HEADER_FILES = $(wildcard $(INCLUDE_DIR)/*.h)
OBJ_FILES = $(C_FILES:$(SRC_DIR)/%.c=$(BUILD_DIR)/%_c.o)
OBJ_FILES += $(ASM_FILES:$(SRC_DIR)/%.S=$(BUILD_DIR)/%_s.o)

$(BUILD_DIR)/%_c.o: $(SRC_DIR)/%.c $(HEADER_FILES)
	$(CC) $(CC_OPS) -c $< -o $@

$(BUILD_DIR)/%_s.o: $(SRC_DIR)/%.S
	$(AS) $(AS_OPS) -o $@ $<

# Linker flags copied from this tutorial:
#   https://smist08.wordpress.com/2021/01/08/apple-m1-assembly-language-hello-world/
$(MAIN): $(OBJ_FILES)
	ld \
		-macos_version_min 13.0.0 \
		-o $@ \
		$(OBJ_FILES) \
		-lSystem \
		-L /Library/Developer/CommandLineTools/SDKs/MacOSX14.0.sdk/usr/lib \
		-syslibroot \
		`xcrun -sdk macosx --show-sdk-path` \
		-arch arm64
