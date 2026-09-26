# -*- coding: utf-8 -*-
"""Automated overflow check for rendered Decoda PDFs (part of QC gate, section F).
Renders each page to an image and flags any page where ink appears below the
safe zone (92% of page height; the footer sits at ~95%). Overflowing text is
silently clipped by the layout, so this catches what eyes might miss.

Usage: python3 check_render.py path/to/report.pdf
Exit code 0 = clean, 1 = at least one page flagged.
"""
import sys
import pypdfium2 as pdfium

SAFE = 0.92          # ink below this fraction of page height = flagged
FOOTER_BAND = 0.97   # ignore the footer itself (sits ~94-96%)

def check(path):
    pdf = pdfium.PdfDocument(path)
    bad = []
    for i, page in enumerate(pdf):
        img = page.render(scale=1.0).to_pil().convert("L")
        W, H = img.size
        px = img.load()
        # detect page polarity: dark pages have light text, light pages dark text
        corner = sum(px[x, y] for x in range(5, 25) for y in range(5, 25)) / 400
        dark_bg = corner < 128
        def is_ink(v): return v > 160 if dark_bg else v < 120
        y0, y1 = int(H * SAFE), int(H * (FOOTER_BAND - 0.03))
        ink = sum(1 for y in range(y0, y1)
                  for x in range(int(W * 0.08), int(W * 0.92)) if is_ink(px[x, y]))
        if ink > 40:  # tolerance for grain noise
            bad.append((i + 1, ink))
    pdf.close()
    return bad

if __name__ == "__main__":
    path = sys.argv[1]
    bad = check(path)
    if bad:
        for p, ink in bad:
            print(f"OVERFLOW RISK page {p}: ink in danger zone ({ink} px)")
        sys.exit(1)
    print("render clean: no page overflows the safe zone")
