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
    """A banner of the required upload size (BANNER_SIZE), so seed data meets the upload rules."""
    from app.services.storage_service import BANNER_SIZE

    w, h = BANNER_SIZE
    u = h / 240  # the design is drawn for a 240px tall banner, scaled to the required size
    img = Image.new("RGB", (w, h), _hex(bg))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, round(14 * u), h], fill=_hex(accent))
    draw.ellipse([w - h, round(-96 * u), w + round(96 * u), h], fill=_hex(accent))
    draw.text((round(56 * u), round(58 * u)), title, font=_font(round(46 * u)), fill=(255, 255, 255))
    draw.text((round(58 * u), round(140 * u)), subtitle, font=_font(round(24 * u)), fill=(203, 213, 225))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def avatar_png(initials: str, bg: str = "#2563EB") -> bytes:
    size = 256  # the minimum photo size
    img = Image.new("RGB", (size, size), _hex(bg))
    draw = ImageDraw.Draw(img)
    font = _font(104)
    box = draw.textbbox((0, 0), initials, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    draw.text(((size - tw) / 2 - box[0], (size - th) / 2 - box[1]), initials, font=font, fill=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
