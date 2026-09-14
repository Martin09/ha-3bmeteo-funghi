"""Generate our original mushroom icon (not the 3BMeteo logo)."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((32, 32, 992, 992), radius=224, fill="#183f32")
draw.rounded_rectangle((420, 440, 604, 850), radius=70, fill="#fff0d2")
draw.pieslice((180, 180, 844, 820), start=180, end=360, fill="#e6a64b")
draw.rounded_rectangle((180, 460, 844, 548), radius=40, fill="#e6a64b")
for x, y, radius in [(350, 380, 44), (512, 280, 50), (675, 395, 40)]:
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill="#fff0d2")
image.resize((256, 256), Image.Resampling.LANCZOS).save(
    ROOT / "custom_components/3bmeteo_funghi/brand/icon.png", optimize=True
)
