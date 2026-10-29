"""Signature HTML that classic Outlook for Windows (Word rendering engine) can show correctly."""
import io
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from PIL import Image

from app import branding
from app.core.config import get_settings
from app.renderers import LAYOUTS
from app.renderers.banner import BANNER_WIDTH
from app.renderers.classic import LOGO_BOX, LOGO_GAP, PHOTO, PHOTO_GAP
from app.renderers.context import BannerView, EmployeeView, LogoView, SignatureContext, TemplateStyle
from app.renderers.html_utils import image_cell
from app.services.signature_photo import STYLE, signature_photo_path, square_photo_png
from tests.conftest import create_banner, make_employee, publish

EMPLOYEE = EmployeeView(
    name="Pia Photo", designation="Designer", department="Design", company="Casterly",
    email="pia@company.com", phone="+1 555 0100", website="https://casterly.example",
    address="1 Main Street, Springfield", photo_src="https://sig.test/uploads/photos/sig/pia-1-sq2.png",
    socials=[("LinkedIn", "https://linkedin.example/pia")],
)
BANNER = BannerView(title="Launch", image_src="https://sig.test/banner/current.png?v=1-2",
                    target_url="https://sig.test/banner/current?v=1-2", height=120)
LOGO = LogoView(src="https://sig.test/static/brand/casterly-logo.png", alt="Casterly", width=32, height=50)


def _render(layout: str, *, photo=True, logo=True, banner=True) -> str:
    emp = EMPLOYEE if photo else EmployeeView(**{**EMPLOYEE.__dict__, "photo_src": None})
    ctx = SignatureContext(employee=emp, style=TemplateStyle(layout=layout), banner=BANNER if banner else None,
                           disclaimer="Confidential.", logo=LOGO if logo else None)
    return LAYOUTS[layout].render(ctx)


def _png(size, color=(200, 30, 30), fmt="PNG") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()


def _write_upload(key: str, data: bytes) -> str:
    target = Path(get_settings().upload_dir) / key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"/uploads/{key}"


class _TopRowCells(HTMLParser):
    """The width attributes of the cells in the outer table's first row."""

    def __init__(self):
        super().__init__()
        self.depth = 0  # table nesting
        self.rows = 0
        self.widths: list[int] = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.depth += 1
        elif tag == "tr" and self.depth == 1:
            self.rows += 1
        elif tag == "td" and self.depth == 1 and self.rows == 1:
            self.widths.append(int(dict(attrs).get("width", 0)))

    def handle_endtag(self, tag):
        if tag == "table":
            self.depth -= 1


def _top_row_widths(html: str) -> list[int]:
    parser = _TopRowCells()
    parser.feed(html)
    return parser.widths


VARIANTS = [
    (layout, photo, logo, banner)
    for layout in LAYOUTS for photo in (True, False) for logo in (True, False) for banner in (True, False)
]


@pytest.mark.parametrize("layout,photo,logo,banner", VARIANTS)
def test_no_css_that_classic_outlook_ignores_or_misreads(layout, photo, logo, banner):
    html = _render(layout, photo=photo, logo=logo, banner=banner).lower()
    for forbidden in ("border-radius", "object-fit", "overflow", "display:flex", "<div", "<style", "data:", "%\""):
        assert forbidden not in html, forbidden
    # Percentages only as max-width (ignored by classic Outlook, used by web and mobile to shrink).
    assert re.findall(r"[\w-]+:\s*\d+%", html) == ["max-width:100%"] * html.count("max-width:100%")


@pytest.mark.parametrize("layout,photo,logo,banner", VARIANTS)
def test_every_image_is_sized_https_png_or_jpg(layout, photo, logo, banner):
    images = re.findall(r"<img [^>]+>", _render(layout, photo=photo, logo=logo, banner=banner))
    for img in images:
        src = re.search(r'src="([^"]+)"', img).group(1)
        assert src.startswith("https://") and re.search(r"\.(png|jpe?g)(\?|$)", src), src
        assert re.search(r' width="\d+"', img) and re.search(r' height="\d+"', img), img
        assert "display:block" in img and "border:0" in img


def test_classic_columns_add_up_to_the_banner_width():
    html = _render("classic")
    assert html.startswith(f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="{BANNER_WIDTH}"')
    assert f"width:{BANNER_WIDTH}px;max-width:100%;" in html.split(">", 1)[0]
    assert _top_row_widths(html) == [PHOTO, PHOTO_GAP, 340, LOGO_GAP, LOGO_BOX]
    assert sum(_top_row_widths(html)) == BANNER_WIDTH
    assert _top_row_widths(_render("classic", photo=False)) == [418, LOGO_GAP, LOGO_BOX]


@pytest.mark.parametrize("layout", LAYOUTS)
def test_images_are_not_clipped_by_the_line_height(layout):
    html = _render(layout)
    outer_style = re.search(r'style="([^"]*)"', html).group(1)
    assert "line-height" not in outer_style and "mso-line-height-rule" not in outer_style
    for img in re.finditer(r"<img [^>]*height=\"(\d+)\"", html):
        cell = html[html.rfind("<td ", 0, img.start()):img.start()]
        if 'src="https://sig.test/banner/' in img.group(0):
            assert "line-height" not in cell  # the banner sits in its own table with no line height
            continue
        # "At least" the image height, never "exactly": Word clips an image's top in an exact line.
        assert "mso-line-height-rule:at-least;" in cell and "exactly" not in cell
        assert int(re.search(r"line-height:(\d+)px", cell).group(1)) >= int(img.group(1))
        assert "font-size:1px;" in cell and "vertical-align:top;" in cell


def test_photo_cell_is_a_fixed_64px_image_cell():
    html = _render("classic")
    assert (f'<td valign="top" width="{PHOTO}" height="{PHOTO}" '
            f'style="padding:0;width:{PHOTO}px;{image_cell(PHOTO)}background-color:#ffffff;">'
            f'<img src="{EMPLOYEE.photo_src}" alt="Pia Photo" width="{PHOTO}" height="{PHOTO}" '
            f'style="display:block;width:{PHOTO}px;height:{PHOTO}px;border:0;outline:none;" />') in html


def test_banner_height_only_when_given():
    assert ' height="120"' in _render("classic")
    ctx = SignatureContext(employee=EMPLOYEE, style=TemplateStyle(),
                           banner=BannerView(title="x", image_src="https://sig.test/banner/current.png"), logo=LOGO)
    assert 'banner/current.png" alt="x" title="x" width="480" style=' in LAYOUTS["classic"].render(ctx)


def _photo(size, fmt="PNG") -> Image.Image:
    """A plain green photo of `size`, run through square_photo_png."""
    buf = io.BytesIO()
    Image.new("RGB", size, (0, 160, 0)).save(buf, format=fmt, **({"lossless": True} if fmt == "WEBP" else {}))
    return Image.open(io.BytesIO(square_photo_png(buf.getvalue())))


def _near(pixel, color, tolerance=3) -> bool:
    return all(abs(a - b) <= tolerance for a, b in zip(pixel, color))


GREEN, WHITE = (0, 160, 0), (255, 255, 255)


def test_wide_photo_is_fitted_whole_with_white_bars_above_and_below():
    with _photo((300, 100), fmt="WEBP") as out:  # 3:1 -> 128x43, centred
        assert out.format == "PNG" and out.size == (128, 128)
        assert out.mode == "RGB"  # no alpha channel at all, so no transparent corners
        for xy in ((0, 0), (127, 0), (0, 127), (127, 127), (64, 20), (64, 107)):
            assert out.getpixel(xy) == WHITE, xy  # white padding and square corners
        for xy in ((0, 64), (127, 64), (64, 64)):  # not cropped: reaches both side edges
            assert _near(out.getpixel(xy), GREEN), xy
        rows = [y for y in range(128) if _near(out.getpixel((64, y)), GREEN)]
        assert 41 <= len(rows) <= 45 and abs((rows[0] + rows[-1]) / 2 - 63.5) <= 1  # centred


def test_tall_photo_is_fitted_whole_with_white_bars_left_and_right():
    with _photo((90, 120), fmt="JPEG") as out:  # 3:4 -> 96x128, centred
        assert out.size == (128, 128) and out.mode == "RGB"
        assert out.getpixel((5, 64)) == WHITE and out.getpixel((122, 64)) == WHITE
        assert _near(out.getpixel((64, 0)), GREEN) and _near(out.getpixel((64, 127)), GREEN)  # top and bottom kept


def test_square_photo_fills_the_square():
    with _photo((500, 500)) as out:
        assert out.size == (128, 128) and out.getpixel((0, 0)) == GREEN and out.getpixel((127, 127)) == GREEN


def test_transparent_photo_is_flattened_onto_white():
    img = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
    img.paste((10, 20, 30, 255), (10, 10, 40, 40))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    with Image.open(io.BytesIO(square_photo_png(buf.getvalue()))) as out:
        assert out.mode == "RGB" and out.getpixel((0, 0)) == (255, 255, 255)
        assert out.getpixel((64, 64)) == (10, 20, 30)


def test_signature_photo_path_makes_one_cached_copy():
    stored = _write_upload("photos/cache-test.webp", _png((90, 120), fmt="WEBP"))
    path = signature_photo_path(stored)
    # The style suffix keeps older (round, cropped) copies from being reused or served from
    # Outlook's cache.
    assert STYLE == "sq2" and re.fullmatch(r"/uploads/photos/sig/cache-test-\d+-sq2\.png", path)
    made = Path(get_settings().upload_dir) / path.removeprefix("/uploads/")
    first_mtime = made.stat().st_mtime_ns
    assert signature_photo_path(stored) == path and made.stat().st_mtime_ns == first_mtime
    assert signature_photo_path("https://cdn.example/p.jpg") == "https://cdn.example/p.jpg"
    assert signature_photo_path("/uploads/photos/missing.png") == "/uploads/photos/missing.png"
    assert signature_photo_path(None) is None


def test_unreadable_photo_falls_back_to_the_original():
    stored = _write_upload("photos/broken.png", b"not an image")
    assert signature_photo_path(stored) == stored


def test_addin_signature_has_square_photo_and_sized_banner(client, db, admin_headers, template):
    photo = _write_upload("photos/addin-pia.jpg", _png((400, 600), fmt="JPEG"))
    make_employee(db, code="EMP-R", first="Rae", last="Round", designation="Designer",
                  email="rae@company.com", profile_photo_url=photo, with_login=False)
    html = client.get("/api/outlook/signature?email=rae@company.com").text
    assert 'width="480" height="1"' in html  # no banner published: the 1200x2 blank strip
    photo_src = re.search(r'<img src="(https://sig\.test/uploads/photos/sig/addin-pia-\d+-sq2\.png)"', html).group(1)
    r = client.get(photo_src.removeprefix("https://sig.test"))
    assert r.status_code == 200
    with Image.open(io.BytesIO(r.content)) as served:
        assert served.format == "PNG" and served.size == (128, 128) and served.mode == "RGB"

    image = _write_upload("banners/wide.png", _png((960, 240)))
    publish(client, admin_headers, create_banner(client, admin_headers, "Wide", image_url=image)["id"])
    html = client.get("/api/outlook/signature?email=rae@company.com").text
    assert re.search(r'banner/current\.png\?v=[^"]+" alt="[^"]*" title="[^"]*" width="480" height="120"', html)


def test_saved_signatures_have_no_fixed_banner_height(client, db, admin_headers, template, john):
    image = _write_upload("banners/saved.png", _png((960, 240)))
    publish(client, admin_headers, create_banner(client, admin_headers, "Saved", image_url=image)["id"])
    data = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]
    live = data.get("live_html") or ""
    assert "banner/current.png" in live and 'height="120"' not in live


def test_live_banner_is_always_png(client, admin_headers, template):
    image = _write_upload("banners/webp-banner.webp", _png((960, 240), fmt="WEBP"))
    publish(client, admin_headers, create_banner(client, admin_headers, "Webp", image_url=image)["id"])
    r = client.get("/banner/current.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    with Image.open(io.BytesIO(r.content)) as img:
        assert img.format == "PNG" and img.size == (960, 240)


# ------------------------------- company logo ------------------------------- #
@pytest.mark.parametrize("file_size,expected", [((501, 772), (32, 50)), ((300, 100), (50, 17)), ((40, 40), (50, 50))])
def test_logo_size_comes_from_the_file_with_its_aspect_ratio(tmp_path, monkeypatch, file_size, expected):
    logo = tmp_path / "logo.png"
    Image.new("RGB", file_size, (10, 10, 10)).save(logo)
    monkeypatch.setattr(branding, "LOGO_FILE", logo)
    branding.logo_display_size.cache_clear()
    try:
        w, h = branding.logo_display_size()
    finally:
        branding.logo_display_size.cache_clear()
    assert (w, h) == expected and w <= branding.LOGO_MAX_WIDTH and h <= branding.LOGO_MAX_HEIGHT
    assert abs(w / h - file_size[0] / file_size[1]) / (file_size[0] / file_size[1]) < 0.03  # rounding only


@pytest.mark.parametrize("layout", LAYOUTS)
def test_logo_is_shown_at_its_own_size_in_a_cell_that_fits_it(layout):
    html = _render(layout)
    img = re.search(r'<img src="https://sig\.test/static/brand/casterly-logo\.png"[^>]*>', html).group(0)
    assert f'width="{LOGO.width}" height="{LOGO.height}"' in img
    assert f"width:{LOGO.width}px;height:{LOGO.height}px;" in img
    assert "max-width" not in img and "auto" not in img  # nothing a client could squeeze
    at = html.index(img)
    cell = html[html.rfind("<td ", 0, at):at]
    assert int(re.search(r"line-height:(\d+)px", cell).group(1)) >= LOGO.height
    if layout == "classic":
        assert LOGO.width <= LOGO_BOX and LOGO.height <= LOGO_BOX
        assert f'width="{LOGO_BOX}" height="{LOGO_BOX}"' in cell


# ---------------------------------- banner ---------------------------------- #
BANNER_ROW = re.compile(
    r'<tr><td (?:colspan="(\d+)" )?style="padding:0;"><table [^>]*width="480" '
    r'style="border-collapse:collapse;width:480px;max-width:100%;"><tr><td style="padding:0;"><a [^>]*>'
    r'<img src="https://sig\.test/banner/'
)


@pytest.mark.parametrize("layout,photo,logo", [(lay, p, lo) for lay in LAYOUTS for p in (True, False) for lo in (True, False)])
def test_banner_has_its_own_unpadded_row_as_wide_as_the_signature(layout, photo, logo):
    html = _render(layout, photo=photo, logo=logo)
    # With a banner the signature is always banner-wide, so the banner matches the block...
    assert html.startswith(f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="{BANNER_WIDTH}"')
    assert f"width:{BANNER_WIDTH}px;max-width:100%;" in html.split(">", 1)[0]
    assert "background" not in html.split(">", 1)[0]  # nothing behind the banner from the outer table
    # ...and the banner's row has no padding or background, just the banner table.
    row = BANNER_ROW.search(html)
    assert row, html
    assert "background" not in html[row.start():html.index("</table>", row.start())]
    if layout == "classic":
        assert row.group(1) == str(len(_top_row_widths(html)))  # spans every column of the block


def test_classic_banner_left_edge_is_the_photo_left_edge():
    html = _render("classic")
    # The photo is the first cell of the first row and the banner the only cell of its row, both
    # unpadded in the same 480px table, so both start at its left edge.
    first = re.match(r'<table [^>]*><tr><td valign="top" width="64" height="64" style="padding:0;', html)
    assert first and html.index(EMPLOYEE.photo_src) < html.index("</td>")
    assert BANNER_ROW.search(html).group(1) == "5"

