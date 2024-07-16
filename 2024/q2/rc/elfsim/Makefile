CC ?= clang
CPPC ?= clang++
CFLAGS = -Wall -Werror -std=c99
CPPFLAGS = -Wall -Werror

OUTDIR = out

# make sure the build directory exists
$(shell mkdir -p $(OUTDIR) >/dev/null)

all: $(OUTDIR)/example $(OUTDIR)/elfsim

$(OUTDIR)/example: example.c
	$(CC) $(CFLAGS) -g -o $@ $<


$(OUTDIR)/elfsim: elfsim.cc
	$(CPPC) $(CPPFLAGS) -o $@ $<


.PHONY: clean
clean:
	rm -rf $(OUTDIR)/*
