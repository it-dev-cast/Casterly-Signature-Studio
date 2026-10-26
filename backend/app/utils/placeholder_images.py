"""Generate simple PNG placeholders (used by the seed script) so the demo works offline."""
import io

from PIL import Image, ImageDraw, ImageFont


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def _hex(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def banner_png(title: str, subtitle: str, bg: str = "#1F2A44", accent: str = "#3B82F6") -> bytes:
    """1200x240 banner (rendered at 600x120 in email for crisp retina display)."""
    w, h = 1200, 240
    img = Image.new("RGB", (w, h), _hex(bg))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, 18, h], fill=_hex(accent))
    draw.ellipse([w - 300, -120, w + 120, 300], fill=_hex(accent))
    draw.text((70, 62), title, font=_font(58), fill=(255, 255, 255))
    draw.text((72, 150), subtitle, font=_font(30), fill=(203, 213, 225))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def avatar_png(initials: str, bg: str = "#2563EB") -> bytes:
    size = 176
    img = Image.new("RGB", (size, size), _hex(bg))
    draw = ImageDraw.Draw(img)
    font = _font(72)
    box = draw.textbbox((0, 0), initials, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(((size - tw) / 2 - box[0], (size - th) / 2 - box[1]), initials, font=font, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
