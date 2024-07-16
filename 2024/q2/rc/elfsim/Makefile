CC ?= gcc
CPPC ?= g++
CFLAGS = -Wall -Werror -std=c99
CPPFLAGS = -Wall -Werror -std=c++14 -Iinclude

OUTDIR = out

# make sure the build directory exists
$(shell mkdir -p $(OUTDIR) >/dev/null)

all: $(OUTDIR)/example $(OUTDIR)/elfsim

$(OUTDIR)/example: src/example.c
	$(CC) $(CFLAGS) -g -o $@ $<


$(OUTDIR)/elfsim: src/*.cc
	$(CPPC) $(CPPFLAGS) -o $@ $^


.PHONY: clean
clean:
	rm -rf $(OUTDIR)/*
