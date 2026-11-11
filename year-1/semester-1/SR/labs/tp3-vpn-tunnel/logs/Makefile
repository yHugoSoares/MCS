# TP3 - 2.c / 2.d
#   make          -> imagens + PDF
#   make capture  -> volta a correr as experiencias na VM e actualiza os transcritos
#   make img      -> so re-renderiza os PNGs a partir dos transcritos

ROOT    := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/..)
VM      ?= seed@192.168.153.137
VM_PASS ?= dees
FIGS    := 2c_ping 2c_eth0 2d_reply 2d_garbage

.PHONY: all pdf img capture shots clean

all: pdf

pdf: img
	typst compile $(ROOT)/report.typ $(ROOT)/report.pdf

img:
	@mkdir -p img
	@for n in $(FIGS); do python3 tools/mkimg.py transcritos/$$n.txt img/$$n.png; done

capture:
	sshpass -p $(VM_PASS) scp scripts/shots.sh $(VM):/tmp/shots.sh
	sshpass -p $(VM_PASS) ssh $(VM) 'bash /tmp/shots.sh'
	@mkdir -p transcritos
	sshpass -p $(VM_PASS) scp "$(VM):/tmp/out/*.txt" transcritos/

shots: capture img pdf

clean:
	rm -f img/*.png $(ROOT)/report.pdf
