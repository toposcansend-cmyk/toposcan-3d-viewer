"""Gera PNG com logo SIMEPAR (azul, com concentric circles) para usar como textura
na lateral da pickup Amarok no modelo 3D."""
import os
from PIL import Image, ImageDraw, ImageFont

# Dimensoes proporcionais a porta lateral (~1.5m x 0.4m)
W, H = 1024, 280
BLUE = (40, 100, 175, 255)
WHITE = (255, 255, 255, 255)

img = Image.new("RGBA", (W, H), WHITE)
d = ImageDraw.Draw(img)

# Concentric circles (radar pattern) - lado esquerdo
cx, cy = 140, H // 2
for i in range(1, 5):
    r = 18 + i * 16
    d.arc([cx - r, cy - r, cx + r, cy + r],
          start=-60, end=60, fill=BLUE, width=8)
# centro solido
d.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=BLUE)

# Texto SIMEPAR
# Tentar achar fonte
font = None
font_paths = [
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeuib.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]
for fp in font_paths:
    if os.path.exists(fp):
        try:
            font = ImageFont.truetype(fp, 180)
            break
        except Exception:
            pass
if font is None:
    font = ImageFont.load_default()

text = "simepar"
text_x = 260
# centralizar verticalmente
bbox = d.textbbox((0, 0), text, font=font)
text_h = bbox[3] - bbox[1]
text_y = (H - text_h) // 2 - bbox[1]
d.text((text_x, text_y), text, font=font, fill=BLUE)

# Salvar
out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "simepar_logo.png")
img.save(out)
print(f"OK {out}  ({W}x{H})")
