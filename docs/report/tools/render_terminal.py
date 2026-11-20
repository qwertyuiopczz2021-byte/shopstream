
import sys, os, re
from PIL import Image, ImageDraw, ImageFont

FONT = r"C:\Windows\Fonts\consola.ttf"
FONT_B = r"C:\Windows\Fonts\consolab.ttf"

BG      = (30, 30, 30)
BG_HEAD = (45, 45, 45)
FG      = (212, 212, 212)
PROMPT  = (78, 201, 176)
DIM     = (128, 128, 128)
ERR     = (244, 135, 113)

def wrap(line, cols, indent="    "):
    if len(line) <= cols:
        return [line]
    out = []
    cur = line
    while len(cur) > cols:
        window = cur[:cols]
        cut = window.rfind(" ")
        if cut < 40:
            cut = cols
        out.append(cur[:cut].rstrip())
        cur = indent + cur[cut:].lstrip()
    out.append(cur)
    return out

def render(src, dst, cols=96, size=13, title=None):
    with open(src, encoding="utf-8") as fh:
        raw = fh.read().replace("\r\n", "\n").rstrip("\n").split("\n")

    lines = []
    for line in raw:
        for piece in wrap(line.expandtabs(8), cols):
            lines.append(piece)

    font = ImageFont.truetype(FONT, size)
    cw = font.getlength("M")
    lh = int(size * 1.55)
    pad = 18
    top = pad + (26 if title else 0)
    width = int(max(len(l) for l in lines) * cw) + pad * 2
    width = max(width, 760)
    height = top + len(lines) * lh + pad

    img = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, width - 1, height - 1], outline=(60, 60, 60))

    if title:
        d.rectangle([0, 0, width, 26], fill=BG_HEAD)
        d.ellipse([12, 8, 22, 18], fill=(255, 95, 86))
        d.ellipse([28, 8, 38, 18], fill=(255, 189, 46))
        d.ellipse([44, 8, 54, 18], fill=(39, 201, 63))
        tf = ImageFont.truetype(FONT, 11)
        d.text((66, 7), title, font=tf, fill=DIM)

    y = top
    for line in lines:
        if line.startswith("PS ") or line.startswith(">"):
            d.text((pad, y), line, font=font, fill=PROMPT)
        elif re.search(r"\b(ERROR|WARN|FAIL|error:|Exception|Unavailable|拒绝|错误)\b", line):
            d.text((pad, y), line, font=font, fill=ERR)
        elif line.startswith("    ") and re.match(r"^\s*(at |\+ )", line):
            d.text((pad, y), line, font=font, fill=DIM)
        else:
            d.text((pad, y), line, font=font, fill=FG)
        y += lh

    img.save(dst)
    return dst

if __name__ == "__main__":
    src, dst = sys.argv[1], sys.argv[2]
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 96
    title = sys.argv[4] if len(sys.argv) > 4 else None
    print(render(src, dst, cols=cols, title=title))