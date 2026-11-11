#!/usr/bin/env python3
"""Renderiza transcritos de terminal (.txt) em PNGs para o relatorio.

Uso: python3 mkimg.py transcrito.txt saida.png ["titulo"]
"""
import sys
from PIL import Image, ImageDraw, ImageFont

BG      = (13, 17, 23)
FG      = (201, 209, 217)
PROMPT  = (126, 231, 135)
CMD     = (240, 246, 252)
BORDER  = (48, 54, 61)
SIZE    = 22
PAD     = 24
LH      = int(SIZE * 1.55)
FONT    = "/System/Library/Fonts/Menlo.ttc"


def font(index=0):
    return ImageFont.truetype(FONT, SIZE, index=index)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    f = font()
    lines = [l.rstrip("\n").replace("\t", "    ") for l in open(src, encoding="utf-8")]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()

    widths = [f.getlength(l) for l in lines] or [0]
    w = int(max(widths)) + 2 * PAD
    h = LH * len(lines) + 2 * PAD

    img = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w - 1, h - 1], outline=BORDER)

    y = PAD
    for line in lines:
        if line.startswith("seedvm:~$ "):
            d.text((PAD, y), "seedvm:~$", font=f, fill=PROMPT)
            x = PAD + f.getlength("seedvm:~$ ")
            d.text((x, y), line[len("seedvm:~$ "):], font=f, fill=CMD)
        else:
            d.text((PAD, y), line, font=f, fill=FG)
        y += LH

    img.save(dst)
    print(dst, img.size)


if __name__ == "__main__":
    main()
