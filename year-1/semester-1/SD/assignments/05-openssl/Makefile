
.PHONY: all decrypt clean help

help:
	@echo "Makefile for encrypting and decrypting messages using OpenSSL"
	@echo "Targets:"
	@echo "  all: Encrypts the message using ChaCha20 and CMS (AES-256-CBC)"
	@echo "  decrypt: Decrypts the encrypted messages"
	@echo "  clean: Removes generated files"
	@echo "  ChaCha20 requires KEY and IV variables, e.g. make all KEY=<hex-key> IV=<hex-iv>"

all: msg.chacha20.enc msg.enc

decrypt: msg.chacha20.dec.txt msg_dec.txt

msg.chacha20.dec.txt: msg.chacha20.enc
	openssl enc -d -chacha20 -in $< -out $@ -K "$(KEY)" -iv "$(IV)"

msg_dec.txt: msg.enc key.pem
	openssl cms -binary -decrypt -in $< -inkey key.pem -out $@

msg.chacha20.enc: msg.txt
	openssl enc -chacha20 -in $< -out $@ -K "$(KEY)" -iv "$(IV)"

msg.enc: msg.txt cert.pem
	openssl cms -binary -encrypt -aes-256-cbc -in $< -out $@ cert.pem

key.pem:
	openssl genrsa -out $@ 2048

cert.pem: key.pem
	openssl req -new -x509 -key $< -out $@ -days 365 -subj "/CN=localhost"

clean:
	rm -f msg.chacha20.enc msg.enc msg.chacha20.dec.txt msg_dec.txt key.pem cert.pem