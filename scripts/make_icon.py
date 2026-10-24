"""Genera el icono de la app (``electron/resources/icon.ico`` y ``icon.png``).

Uso: python scripts/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = Path(__file__).resolve().parents[1] / "electron" / "resources"
ACCENT = (229, 50, 45)
ACCENT_DARK = (176, 30, 26)
WHITE = (255, 255, 255)
CANVAS = 1024
# Se dibuja a 1024 px y se reduce: el antialiasing de la reducción suaviza los bordes.
ICO_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def _font(size):
    for name in ("segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def draw_icon():
    image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((40, 40, 984, 984), radius=200, fill=ACCENT)

    left, top, right, bottom, fold = 270, 170, 754, 854, 150
    draw.polygon([(left, top), (right - fold, top), (right, top + fold), (right, bottom), (left, bottom)], fill=WHITE)
    draw.polygon([(right - fold, top), (right, top + fold), (right - fold, top + fold)], fill=(240, 200, 198))
    for y in (330, 400, 470):
        draw.rounded_rectangle((left + 70, y, right - 110, y + 28), radius=14, fill=(235, 235, 238))

    draw.rounded_rectangle((180, 560, 844, 790), radius=40, fill=ACCENT_DARK)
    draw.text((512, 675), "PDF", font=_font(190), fill=WHITE, anchor="mm")
    return image


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    icon = draw_icon()
    icon.resize((512, 512), Image.LANCZOS).save(OUT_DIR / "icon.png")
    icon.save(OUT_DIR / "icon.ico", sizes=ICO_SIZES)
    print(f"Icono generado en {OUT_DIR}")


if __name__ == "__main__":
    main()
