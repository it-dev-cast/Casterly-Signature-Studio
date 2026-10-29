"""Signature HTML that classic Outlook for Windows (Word rendering engine) can show correctly."""
import io
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest
from PIL import Image

from app.core.config import get_settings
from app.renderers import LAYOUTS
from app.renderers.banner import BANNER_WIDTH
from app.renderers.classic import LOGO_BOX, LOGO_GAP, PHOTO, PHOTO_GAP
from app.renderers.context import BannerView, EmployeeView, LogoView, SignatureContext, TemplateStyle
from app.services.signature_photo import round_photo_png, signature_photo_path
from tests.conftest import create_banner, make_employee, publish

EMPLOYEE = EmployeeView(
    name="Pia Photo", designation="Designer", department="Design", company="Casterly",
    email="pia@company.com", phone="+1 555 0100", website="https://casterly.example",
    address="1 Main Street, Springfield", photo_src="https://sig.test/uploads/photos/sig/pia-1.png",
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
def test_images_are_not_clipped_by_an_inherited_exact_line_height(layout):
    html = _render(layout)
    outer_style = re.search(r'style="([^"]*)"', html).group(1)
    assert "line-height" not in outer_style and "mso-line-height-rule" not in outer_style
    for img in re.finditer(r"<img [^>]*height=\"(\d+)\"", html):
        cell = html.rfind("<td ", 0, img.start())
        if 'src="https://sig.test/banner/' in img.group(0):
            continue  # the banner sits in its own table with no line height
        assert f"line-height:{img.group(1)}px;mso-line-height-rule:exactly;" in html[cell:img.start()]


def test_banner_height_only_when_given():
    assert ' height="120"' in _render("classic")
    ctx = SignatureContext(employee=EMPLOYEE, style=TemplateStyle(),
                           banner=BannerView(title="x", image_src="https://sig.test/banner/current.png"), logo=LOGO)
    assert 'banner/current.png" alt="x" title="x" width="480" style=' in LAYOUTS["classic"].render(ctx)


def test_round_photo_is_a_centre_cropped_circle_png():
    wide = Image.new("RGB", (300, 100), (255, 0, 0))
    wide.paste((0, 160, 0), (100, 0, 200, 100))  # green middle third
    buf = io.BytesIO()
    wide.save(buf, format="WEBP", lossless=True)
    with Image.open(io.BytesIO(round_photo_png(buf.getvalue()))) as out:
        assert out.format == "PNG" and out.size == (128, 128) and out.mode == "RGBA"
        assert out.getpixel((0, 0))[3] == 0 and out.getpixel((127, 127))[3] == 0  # transparent corners
        assert out.getpixel((64, 64)) == (0, 160, 0, 255)  # the centre, opaque
        assert out.getpixel((64, 2))[3] == 255 and out.getpixel((2, 64))[3] == 255  # circle reaches the edges


def test_signature_photo_path_makes_one_cached_copy():
    stored = _write_upload("photos/cache-test.webp", _png((90, 120), fmt="WEBP"))
    path = signature_photo_path(stored)
    assert re.fullmatch(r"/uploads/photos/sig/cache-test-\d+\.png", path)
    made = Path(get_settings().upload_dir) / path.removeprefix("/uploads/")
    first_mtime = made.stat().st_mtime_ns
    assert signature_photo_path(stored) == path and made.stat().st_mtime_ns == first_mtime
    assert signature_photo_path("https://cdn.example/p.jpg") == "https://cdn.example/p.jpg"
    assert signature_photo_path("/uploads/photos/missing.png") == "/uploads/photos/missing.png"
    assert signature_photo_path(None) is None


def test_unreadable_photo_falls_back_to_the_original():
    stored = _write_upload("photos/broken.png", b"not an image")
    assert signature_photo_path(stored) == stored


def test_addin_signature_has_round_photo_and_sized_banner(client, db, admin_headers, template):
    photo = _write_upload("photos/addin-pia.jpg", _png((400, 600), fmt="JPEG"))
    make_employee(db, code="EMP-R", first="Rae", last="Round", designation="Designer",
                  email="rae@company.com", profile_photo_url=photo, with_login=False)
    html = client.get("/api/outlook/signature?email=rae@company.com").text
    assert 'width="480" height="1"' in html  # no banner published: the 1200x2 blank strip
    photo_src = re.search(r'<img src="(https://sig\.test/uploads/photos/sig/addin-pia-\d+\.png)"', html).group(1)
    assert client.get(photo_src.removeprefix("https://sig.test")).status_code == 200

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
