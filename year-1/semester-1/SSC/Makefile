# SSC 2026-27 -- Lab reports
# Builds reports/report1.tex and reports/report2.tex with pdflatex.
# Two passes are required for the table of contents and page references.

SHELL        := /bin/sh
REPORT_DIR   := reports
LATEX        := pdflatex
LATEXFLAGS   := -interaction=nonstopmode -halt-on-error -file-line-error

REPORTS      := report1 report2 report3
PDFS         := $(addprefix $(REPORT_DIR)/,$(addsuffix .pdf,$(REPORTS)))
AUX_EXTS     := aux log out toc synctex.gz fls fdb_latexmk
AUX_FILES    := $(foreach r,$(REPORTS),$(foreach e,$(AUX_EXTS),$(REPORT_DIR)/$(r).$(e)))

.DEFAULT_GOAL := help
.PHONY: help all clean distclean $(REPORTS)

help:
	@printf 'SSC lab reports\n\n'
	@printf '  make all        build every report and remove aux files\n'
	@printf '  make report1    build %s/report1.pdf (keeps aux files)\n' '$(REPORT_DIR)'
	@printf '  make report2    build %s/report2.pdf (keeps aux files)\n' '$(REPORT_DIR)'
	@printf '  make report3    build %s/report3.pdf (keeps aux files)\n' '$(REPORT_DIR)'
	@printf '  make clean      remove LaTeX aux files\n'
	@printf '  make distclean  remove aux files and PDFs\n'

all: $(REPORTS) clean

$(REPORTS):
	@test -f $(REPORT_DIR)/$@.tex || { \
		printf 'error: %s/%s.tex not found\n' '$(REPORT_DIR)' '$@' >&2; exit 1; }
	@cd $(REPORT_DIR) && $(LATEX) $(LATEXFLAGS) $@.tex >/dev/null || { \
		printf 'error: %s failed (first pass)\n' '$@' >&2; \
		tail -n 25 $(REPORT_DIR)/$@.log >&2; exit 1; }
	@cd $(REPORT_DIR) && $(LATEX) $(LATEXFLAGS) $@.tex >/dev/null || { \
		printf 'error: %s failed (second pass)\n' '$@' >&2; \
		tail -n 25 $(REPORT_DIR)/$@.log >&2; exit 1; }
	@printf 'built %s/%s.pdf\n' '$(REPORT_DIR)' '$@'

clean:
	@rm -f $(AUX_FILES)

distclean: clean
	@rm -f $(PDFS)
	@printf 'cleaned PDFs\n'
