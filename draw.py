import zlib
import struct

import font

PAPER = (250, 246, 235)
INK = (20, 20, 20)
RED = (178, 34, 34)
GREY = (110, 108, 100)
LIGHT = (232, 228, 218)

ADVANCE = 11  # glyph advance in font units (x scale)


def _tw(s, scale):
    """Pixel width of a string, same logic as Canvas.text_width."""
    return len(s) * ADVANCE * scale


def wrap(text, scale, max_w):
    """Greedy word wrap; a word longer than max_w stays unbroken."""
    lines, cur = [], ""
    for word in text.split(" "):
        cand = word if not cur else cur + " " + word
        if _tw(cand, scale) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur or not lines:
        lines.append(cur)
    return lines


class Canvas:
    def __init__(self, w, h, bg=PAPER):
        self.w, self.h = w, h
        self.buf = bytearray(bg * (w * h))

    def px(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i:i + 3] = bytes(c)

    def line(self, x0, y0, x1, y1, c, w=1):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err, x, y = dx + dy, x0, y0
        while True:
            for ox in range(w):
                for oy in range(w):
                    self.px(x + ox, y + oy, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def rect(self, x, y, w, h, c, lw=1):
        self.line(x, y, x + w, y, c, lw)
        self.line(x, y + h, x + w, y + h, c, lw)
        self.line(x, y, x, y + h, c, lw)
        self.line(x + w, y, x + w, y + h, c, lw)

    def fill_rect(self, x, y, w, h, c):
        x0, x1 = max(0, int(x)), min(self.w, int(x + w))
        y0, y1 = max(0, int(y)), min(self.h, int(y + h))
        row = bytes(c) * (x1 - x0) * 3
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.buf[i:i + len(row)] = row

    def circle(self, cx, cy, r, c):
        x, y, d = r, 0, 1 - r
        while x >= y:
            for dx, dy in ((x, y), (y, x), (-y, x), (-x, y),
                           (-x, -y), (-y, -x), (y, -x), (x, -y)):
                self.px(cx + dx, cy + dy, c)
            y += 1
            if d < 0:
                d += 2 * y + 1
            else:
                x -= 1
                d += 2 * (y - x) + 1

    def fill_circle(self, cx, cy, r, c):
        for dy in range(-r, r + 1):
            half = int((r * r - dy * dy) ** 0.5)
            self.fill_rect(cx - half, cy + dy, half * 2, 1, c)

    def poly(self, pts, c, w=1, closed=False):
        seq = list(pts) + ([pts[0]] if closed and pts else [])
        for a, b in zip(seq, seq[1:]):
            self.line(a[0], a[1], b[0], b[1], c, w)

    def text_width(self, s, scale):
        return _tw(s, scale)

    def text(self, s, x, y, scale, c, align='l'):
        if align == 'c':
            x -= self.text_width(s, scale) / 2
        elif align == 'r':
            x -= self.text_width(s, scale)
        pen = x
        for ch in s:
            glyph = font.GLYPHS.get(ch)
            if glyph:
                for stroke in glyph:
                    pts = [(pen + px_ * scale, y + py_ * scale)
                           for px_, py_ in stroke]
                    self.poly(pts, c)
            pen += ADVANCE * scale

    def save_png(self, path):
        def chunk(tag, data):
            return (struct.pack(">I", len(data)) + tag + data +
                    struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))

        raw = bytearray()
        stride = self.w * 3
        for yy in range(self.h):
            raw.append(0)
            raw += self.buf[yy * stride:(yy + 1) * stride]

        png = (b"\x89PNG\r\n\x1a\n" +
               chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0)) +
               chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
               chunk(b"IEND", b""))
        with open(path, "wb") as f:
            f.write(png)
