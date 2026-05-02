"""
System tray ikonu oluşturma.
Pillow ile dinamik ikon çizer, kalan süreyi piksel yazı olarak basar.
"""

from PIL import Image, ImageDraw, ImageFont
import math


# ─── Renkler ──────────────────────────────────────────────────────────────────
ACCENT    = (201, 168, 76)    # Altın
BG_DARK   = (15, 17, 23)
BG_LIGHT  = (245, 240, 232)
WHITE     = (232, 227, 216)
DIM       = (100, 96, 88)


def _make_base_icon(size=64, theme="dark") -> Image.Image:
    """Hilal + yıldız temelli temel ikon."""
    bg_color = BG_DARK if theme == "dark" else BG_LIGHT
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Arka plan dairesi
    margin = 2
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill=bg_color + (240,))

    cx, cy, r = size // 2, size // 2, size // 2 - 4

    # Hilal çiz
    draw.ellipse([cx-r+2, cy-r+2, cx+r-2, cy+r-2], fill=ACCENT)
    # Hilal içine silerek ay şekli ver
    offset = r * 0.38
    inner_r = r * 0.82
    draw.ellipse([
        cx - r + 2 + offset, cy - inner_r,
        cx - r + 2 + offset + inner_r * 2, cy + inner_r
    ], fill=bg_color + (240,))

    # Küçük yıldız
    star_x, star_y = cx + r * 0.45, cy - r * 0.35
    star_r = r * 0.12
    _draw_star(draw, star_x, star_y, star_r, star_r * 0.5, 5, ACCENT)

    return img


def _draw_star(draw, cx, cy, outer_r, inner_r, points, color):
    coords = []
    for i in range(points * 2):
        angle = math.pi * i / points - math.pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        coords.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(coords, fill=color)


def make_tray_icon(label: str = "", theme: str = "dark") -> Image.Image:
    """
    Sistem tepsisi için ikon üretir.
    label: örn. "08:42" gibi kalan süre metni
    """
    size = 64
    img = _make_base_icon(size, theme)

    if label:
        draw = ImageDraw.Draw(img)
        # Metin arkaplanı
        bar_h = 18
        bar_color = ACCENT if theme == "dark" else (139, 94, 26)
        draw.rectangle([0, size - bar_h, size, size], fill=bar_color + (230,))

        font_size = 11
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", font_size)
        except Exception:
            try:
                font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", font_size)
            except Exception:
                font = ImageFont.load_default()

        text_color = BG_DARK if theme == "dark" else (255, 255, 255)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        tx = (size - tw) // 2
        ty = size - bar_h + 3
        draw.text((tx, ty), label, fill=text_color, font=font)

    return img


def make_loading_icon(theme: str = "dark") -> Image.Image:
    """Yükleniyor ikonu - saat animasyonu simülasyonu."""
    size = 64
    bg_color = BG_DARK if theme == "dark" else BG_LIGHT
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 2
    draw.ellipse([margin, margin, size-margin, size-margin],
                 fill=bg_color + (240,))

    cx, cy = size // 2, size // 2
    draw.ellipse([cx-20, cy-20, cx+20, cy+20], outline=ACCENT, width=2)

    # Saat ibresi
    import math
    draw.line([cx, cy, cx + 14, cy - 8], fill=ACCENT, width=2)
    draw.line([cx, cy, cx + 5, cy + 12], fill=WHITE, width=2)

    return img
