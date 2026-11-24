import os
import sys

_here = os.path.dirname(os.path.abspath(__file__)) or os.environ.get("MAKEFUN_BOT_DIR", "")
if _here and _here not in sys.path:
    sys.path.insert(0, _here)

import draw
import font
from draw import Canvas, PAPER, INK, RED, GREY, LIGHT, wrap

# font.GLYPHS has no entries for these characters; add stroke glyphs at runtime
# (font.py itself is left untouched). Cell is 11 wide x 15 tall, y down.
font.GLYPHS.setdefault("·", [[(4, 7), (7, 7)]])
font.GLYPHS.setdefault("'", [[(7, 1), (7, 5)]])
font.GLYPHS.setdefault("—", [[(1, 7), (10, 7)]])

# draw.line()'s Bresenham loop only terminates on exact endpoint equality, so
# float coordinates (e.g. from Canvas.text at fractional scales) hang forever.
# Round endpoints to ints before delegating; draw.py itself is left untouched.
_orig_line = Canvas.line


def _safe_line(self, x0, y0, x1, y1, c, w=1, lw=None):
    _orig_line(self, int(round(x0)), int(round(y0)),
               int(round(x1)), int(round(y1)), c, w if lw is None else lw)


Canvas.line = _safe_line

W = H = 1024
OUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"

LEFT = 40
RIGHT = 984
BODY_W = 920  # full lead text width


def build(cv):
    # Every text block's vertical extent is computed before/while drawing and
    # recorded in `blocks` (name, x0, x1, y0, y1); blocks are laid out
    # top-to-bottom and side-by-side columns never intersect.
    blocks = []

    def rec(name, x0, x1, y0, y1):
        blocks.append((name, x0, x1, round(y0, 1), round(y1, 1)))

    def glyph_h(scale, mixed=True):
        # caps/digits/punct ink spans font units 0..14; mixed case adds
        # descenders down to ~17.
        return (18 if mixed else 15) * scale + 1

    def draw_lines(name, lines, x, y, scale, lead, color=INK,
                   align="l", mixed=True, x1=None):
        """Draw wrapped lines; record extent [y, last_top + glyph height]."""
        for i, ln in enumerate(lines):
            cv.text(ln, x, y + i * lead, scale, color, align=align)
        y1 = y + (len(lines) - 1) * lead + glyph_h(scale, mixed)
        if x1 is None:
            x1 = x + (max((cv.text_width(ln, scale) for ln in lines),
                          default=0.0) if align == "l" else 0)
        if name is not None:
            rec(name, x, x1, y, y1)
        return y1

    # --- outer border: double rule ---
    cv.rect(8, 8, W - 16, H - 16, INK, lw=3)
    cv.rect(16, 16, W - 32, H - 32, INK, lw=1)

    # --- masthead ---
    title_s = 3.6
    cv.text("THE TUESDAY LEDGER", W // 2, 22, title_s, INK, align="c")
    rec("masthead-title", 0, W, 22, 22 + glyph_h(title_s, mixed=False))
    cv.line(LEFT, 82, RIGHT, 82, INK, lw=1)
    date_s = 1.8
    cv.text("TUESDAY, 24 NOVEMBER 2026", LEFT, 90, date_s, INK)
    cv.text("No. 328  ·  LONDON", RIGHT, 90, date_s, INK, align="r")
    rec("date-band", 0, W, 90, 90 + glyph_h(date_s, mixed=False))
    cv.line(LEFT, 126, RIGHT, 126, RED, lw=2)

    # --- LEAD STORY ---
    # kicker
    kick_s = 1.9
    cv.text("NVIDIA  ·  SILICON VALLEY", LEFT, 134, kick_s, RED)
    rec("kicker", LEFT, RIGHT, 134, 134 + glyph_h(kick_s, mixed=False))

    # headline, three lines (scale chosen so the longest line fits the width)
    hl_scale = 4.0
    hl_lines = ["HUANG IS BACK", "AS NVIDIA BOARD", "REINSTATES ITS CHIEF"]
    hl_lead = 54
    hl_y = 166
    for i, ln in enumerate(hl_lines):
        cv.text(ln, LEFT, hl_y + i * hl_lead, hl_scale, INK)
    rec("headline", LEFT, RIGHT,
        hl_y, hl_y + (len(hl_lines) - 1) * hl_lead +
        glyph_h(hl_scale, mixed=False))
    hl_bottom = hl_y + (len(hl_lines) - 1) * hl_lead + \
        glyph_h(hl_scale, mixed=False)

    # subhead, wrapped to full lead width (tightened wording, all facts kept)
    sub = ("Trump and Vance pressed the board over the weekend; shares "
           "recovered much of a 30% slide and the S&P 500 jumped 4.7%, a "
           "record one-day market-cap gain.")
    sub_scale = 1.6
    sub_lead = 21
    sub_lines = wrap(sub, sub_scale, BODY_W)
    y = draw_lines("subhead", sub_lines, LEFT, hl_bottom + 8,
                   sub_scale, sub_lead, INK, x1=RIGHT)

    # body columns + chart row
    body_top = y + 6
    chart_x0, chart_x1 = 652, 972
    col_x, col_w = LEFT, 580

    paras = [
        "Nvidia's board voted unanimously on Monday to reinstate Jensen Huang "
        "as chief executive, eleven days after he resigned over affairs "
        "including one with a woman suspected of Chinese intelligence ties.",
        "The attorney general said there is no Justice Department investigation "
        "and no evidence of law-breaking; the board had faced weekend "
        "pressure from President Trump and Vice-President Vance.",
        "Investors cheered: Nvidia shares reclaimed much of their slide and "
        "the S&P 500 roared back.",
    ]
    body_scale = 1.0
    body_lead = 12
    para_gap = 2
    y = body_top
    body_bottom = body_top
    for i, p in enumerate(paras):
        lines = wrap(p, body_scale, col_w)
        y1 = draw_lines("body-p%d" % i, lines, col_x, y, body_scale,
                        body_lead, INK, mixed=True, x1=col_x + col_w)
        body_bottom = y1
        y = y1 + para_gap

    # --- lead visual: S&P 500 line chart, right side ---
    ch_x = (chart_x0 + chart_x1) // 2
    ch_top = body_top
    cv.text("S&P 500  ·  +4.7%", ch_x, ch_top, 1.8, INK, align="c")

    # plot area
    px0, px1 = chart_x0 + 14, chart_x1 - 8
    py0, py1 = body_top + 34, body_top + 116   # top..bottom of plot
    cv.line(px0, py1, px1, py1, INK, lw=1)     # x axis
    cv.line(px0, py0, px0, py1, INK, lw=1)     # y axis

    # jagged line: dip then steep rise to new high
    # NOTE: draw.line() requires integer endpoints (float coords loop forever)
    n = 9
    vals = [0.55, 0.45, 0.60, 0.40, 0.35, 0.58, 0.76, 0.90, 0.98]
    pts = []
    for i, v in enumerate(vals):
        x = int(round(px0 + (px1 - px0) * i / (n - 1)))
        yy = int(round(py1 - v * (py1 - py0)))
        pts.append((x, yy))
    cv.poly(pts, INK, w=2)

    # red arrowhead at the end
    ex, ey = pts[-1]
    cv.poly([(ex - 14, ey - 6), (ex, ey), (ex - 14, ey + 6), (ex - 8, ey)],
            RED, w=2, closed=True)

    # red percentage label inside plot, top-left (line peaks at top-right)
    cv.text("+4.7% IN A DAY", px0 + 8, py0 + 6, 1.5, RED)

    # caption below chart
    cap = "Wall Street's best day since the sell-off began."
    cap_scale = 1.0
    cap_lead = 12
    cap_lines = wrap(cap, cap_scale, chart_x1 - chart_x0)
    cy = py1 + 6
    cap_bottom = draw_lines(None, cap_lines, ch_x, cy, cap_scale,
                            cap_lead, GREY, align="c", mixed=True,
                            x1=chart_x1)
    rec("chart", chart_x0, chart_x1, ch_top, cap_bottom)

    # --- PANELS (2 x 2) ---
    panels_top = max(body_bottom, cap_bottom) + 8

    def panel(px, py, pw, name, kicker, hlines, body):
        tx, tw = px + 10, pw - 20
        yy = py + 3
        cv.text(kicker, tx, yy, 1.2, RED)
        yy += 17
        for part in hlines:
            for ln in wrap(part, 1.8, tw):
                cv.text(ln, tx, yy, 1.8, INK)
                yy += 21.5
        yy += 4
        pbody_s = 1.05
        pbody_lead = 12
        for ln in wrap(body, pbody_s, tw):
            cv.text(ln, tx, yy, pbody_s, INK)
            yy += pbody_lead
        bottom = yy - pbody_lead + glyph_h(pbody_s, mixed=True)
        rec(name, px, px + pw, py, bottom)
        return bottom

    LC_X, LC_W = 24, 484
    RC_X, RC_W = 516, 484
    row1_top = panels_top
    row1_bottom = max(
        panel(LC_X, row1_top, LC_W, "panel-ulleung", "ULLEUNG SCARE",
              ["RUSSIAN JETS SPARK", "AIR-RAID ALARM"],
              "Russian jets entered Korea's Ulleung air-defence zone; "
              "jets scrambled, warning lifted after five minutes. "
              "No sovereign airspace violated."),
        panel(RC_X, row1_top, RC_W, "panel-estonia", "ESTONIA",
              ["MOSCOW WARNS TALLINN", "OF 'OPEN WAR'"],
              "Tallinn says it will close the land border from "
              "1 December after Moscow's 'open war' warning."),
    )
    row2_top = row1_bottom + 6
    row2_bottom = max(
        panel(LC_X, row2_top, LC_W, "panel-russia", "RUSSIA",
              ["WAR DEAD NEAR", "500,000, DATA SHOW"],
              "Hacked records count at least 470,000 Russian war dead "
              "to end-September; true toll may reach 700,000."),
        panel(RC_X, row2_top, RC_W, "panel-gomez", "WASHINGTON",
              ["GOMEZ RESIGNS", "AFTER ETHICS FINDING"],
              "Democratic Rep. Jimmy Gomez resigns after the Ethics "
              "panel finds substantial evidence of sexual misconduct."),
    )

    # --- THE DAY IN NUMBERS ---
    num_top = row2_bottom + 8
    num_h = 78
    cv.fill_rect(24, num_top, 976, num_h, LIGHT)
    cv.rect(24, num_top, 976, num_h, INK, lw=1)
    cv.text("THE DAY IN NUMBERS", 512, num_top + 3, 1.3, INK, align="c")
    nums = [
        ("500,000", "RUSSIAN WAR DEAD"),
        ("+4.7%", "S&P 500"),
        ("11 DAYS", "HUANG WAS OUT"),
        ("5 MINUTES", "ULLEUNG WARNING"),
        ("810,000", "HONDA CARS RECALLED"),
    ]
    num_s = 1.8
    lab_s = 0.85
    num_y = num_top + 25
    for i, (num, lab) in enumerate(nums):
        cx = 24 + 976 * (i + 0.5) / 5
        cv.text(num, cx, num_y, num_s, RED, align="c")
        lab_lines = wrap(lab, lab_s, 190)
        ly = num_y + 36
        for j, ln in enumerate(lab_lines):
            cv.text(ln, cx, ly + j * 11, lab_s, INK, align="c")
    rec("numbers", 24, 1000, num_top, num_top + num_h)

    # --- IN BRIEF ---
    brief_top = num_top + num_h + 6
    cv.text("IN BRIEF", 40, brief_top, 1.15, RED)
    rec("briefs-kicker", LEFT, RIGHT, brief_top,
        brief_top + glyph_h(1.15, mixed=False))
    briefs = ("2031 Women's World Cup to the US, Mexico, Costa Rica and "
              "Jamaica; UK gets 2035.  ·  States sue Musk firms over Grok "
              "sexualised images.  ·  Amtrak derails in Louisiana; five "
              "hurt.  ·  Fire engulfs six Zanzibar hotels; 180 tourists "
              "evacuated.  ·  Pakistan quake, magnitude 4.1.  ·  World "
              "chess title: Gukesh v Sindarov opens in Cologny.  ·  UN "
              "food chief warns wars jeopardise aid for 7.3m more "
              "people.")
    brief_s = 1.0
    brief_lead = 10
    brief_lines = wrap(briefs, brief_s, 920)
    draw_lines("briefs", brief_lines, 40, brief_top + 20, brief_s,
               brief_lead, INK, mixed=True, x1=RIGHT)

    # --- footer ---
    foot_s = 0.85
    foot_y = 994
    cv.text("THE TUESDAY LEDGER  ·  TUESDAY 24 NOVEMBER 2026  ·  ALL "
            "STORIES REPORTED ON THE DAY", 512, foot_y, foot_s, GREY,
            align="c")
    rec("footer", 0, W, foot_y, foot_y + glyph_h(foot_s, mixed=False))

    # DEBUG: verify every block extent is inside the inner border and that
    # blocks sharing x-range never intersect in y.
    blocks.sort(key=lambda b: (b[3], b[1]))
    prev = None
    for name, x0, x1, y0, y1 in blocks:
        flag = ""
        if y0 < 16 or y1 > 1008:
            flag += " OUT-OF-BOUNDS"
        if prev and y0 < prev[4] - 0.01 and x0 < prev[2] and x1 > prev[1]:
            flag += " OVERLAP(%s)" % prev[0]
        print("BLOCK %-16s x%4.0f..%4.0f  %7.1f .. %7.1f%s"
              % (name, x0, x1, y0, y1, flag))
        prev = (name, x0, x1, y0, y1)


def main():
    cv = Canvas(W, H, PAPER)
    build(cv)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "entry.png")
    cv.save_png(out)
    print("wrote " + out)


if __name__ == "__main__":
    main()
