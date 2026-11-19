"""Upload rules: photo (JPG/PNG, max 300 KB, at least 256 x 256 px), banner (JPG/PNG, max 500 KB,
exactly 960 x 240 px) and the built-in logo (PNG, at least 200 px tall, max 200 KB).

New or changed images must meet them; images stored before the rules keep working.
"""
import io

import pytest
from PIL import Image
from PIL.PngImagePlugin import PngInfo

from app import branding
from tests.conftest import (
    banner_payload, create_banner, image_bytes, legacy_banner, make_employee, publish, stored_image,
)
from tests.test_employees import PAYLOAD


def png_of_exact_bytes(size: tuple[int, int], total: int) -> bytes:
    """A valid PNG of `size` px that is exactly `total` bytes (padded with a text chunk)."""
    def build(pad: int) -> bytes:
        info = PngInfo()
        info.add_text("pad", "x" * pad)
        buf = io.BytesIO()
        Image.new("RGB", size, (30, 58, 138)).save(buf, format="PNG", pnginfo=info)
        return buf.getvalue()

    data = build(total - len(build(0)))
    assert len(data) == total
    return data


def upload(client, headers, kind, data, name="image.png", content_type="image/png"):
    return client.post("/api/uploads", data={"kind": kind}, files={"file": (name, data, content_type)}, headers=headers)


def error(r) -> tuple[int, str, str]:
    body = r.json()["error"]
    return r.status_code, body["code"], body["message"]


# ------------------------------------------------------------------- rules --
def test_rules_endpoint_matches_what_is_enforced(client, admin_headers, john_headers):
    rules = client.get("/api/uploads/rules", headers=admin_headers).json()["data"]
    assert rules["photo"] == {"max_kb": 300, "formats": ["jpg", "png"], "exact_width": None, "exact_height": None,
                              "min_width": 256, "min_height": 256,
                              "hint": "At least 256 x 256 px. JPG or PNG, max 300 KB."}
    assert rules["banner"] == {"max_kb": 500, "formats": ["jpg", "png"], "exact_width": 960, "exact_height": 240,
                               "min_width": None, "min_height": None,
                               "hint": "Must be exactly 960 x 240 px. JPG or PNG, max 500 KB."}
    assert client.get("/api/uploads/rules", headers=john_headers).status_code == 403


# ------------------------------------------------------------------- photo --
@pytest.mark.parametrize("size", [(256, 256), (600, 400), (1024, 1024)])
def test_photo_at_least_256_px_is_accepted(client, admin_headers, size):
    r = upload(client, admin_headers, "photo", image_bytes(size, "JPEG"), "p.jpg", "image/jpeg")
    assert r.status_code == 201, r.text
    assert r.json()["data"]["path"].startswith("/uploads/photos/") and r.json()["data"]["path"].endswith(".jpg")


@pytest.mark.parametrize("size", [(255, 256), (256, 255), (176, 176)])
def test_photo_smaller_than_256_px_is_rejected(client, admin_headers, size):
    r = upload(client, admin_headers, "photo", image_bytes(size))
    assert error(r) == (400, "INVALID_IMAGE_SIZE",
                        f"Photo must be at least 256 x 256 px. Your image is {size[0]} x {size[1]} px.")


def test_photo_max_300_kb(client, admin_headers):
    assert upload(client, admin_headers, "photo", png_of_exact_bytes((256, 256), 300 * 1024)).status_code == 201
    r = upload(client, admin_headers, "photo", png_of_exact_bytes((256, 256), 300 * 1024 + 1))
    assert error(r) == (413, "FILE_TOO_LARGE", "Photo must be 300 KB or smaller. Your file is 301 KB.")


@pytest.mark.parametrize("fmt,name", [("GIF", "GIF"), ("WEBP", "WebP")])
def test_photo_must_be_jpg_or_png(client, admin_headers, fmt, name):
    r = upload(client, admin_headers, "photo", image_bytes((256, 256), fmt), "p.img", "image/png")
    assert error(r) == (400, "INVALID_IMAGE_TYPE", f"Photo must be a JPG or PNG image. Your file is {name}.")


# ------------------------------------------------------------------ banner --
@pytest.mark.parametrize("fmt", ["PNG", "JPEG"])
def test_banner_of_exactly_960_by_240_is_accepted(client, admin_headers, fmt):
    r = upload(client, admin_headers, "banner", image_bytes((960, 240), fmt))
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("size", [(961, 240), (960, 241), (1920, 480), (1200, 240), (480, 120)])
def test_banner_of_any_other_size_is_rejected_with_the_required_size(client, admin_headers, size):
    r = upload(client, admin_headers, "banner", image_bytes(size))
    assert error(r) == (400, "INVALID_IMAGE_SIZE",
                        f"Banner must be exactly 960 x 240 px. Your image is {size[0]} x {size[1]} px.")


def test_banner_max_500_kb(client, admin_headers):
    assert upload(client, admin_headers, "banner", png_of_exact_bytes((960, 240), 500 * 1024)).status_code == 201
    r = upload(client, admin_headers, "banner", png_of_exact_bytes((960, 240), 742 * 1024))
    assert error(r) == (413, "FILE_TOO_LARGE", "Banner must be 500 KB or smaller. Your file is 742 KB.")


def test_file_over_the_request_cap_gets_the_same_kb_message(client, admin_headers):
    r = upload(client, admin_headers, "banner", b"\0" * (6 * 1024 * 1024))  # over MAX_UPLOAD_MB (5)
    assert error(r) == (413, "FILE_TOO_LARGE", "Banner must be 500 KB or smaller. Your file is 6144 KB.")


@pytest.mark.parametrize("fmt,name", [("GIF", "GIF"), ("WEBP", "WebP")])
def test_banner_must_be_jpg_or_png(client, admin_headers, fmt, name):
    r = upload(client, admin_headers, "banner", image_bytes((960, 240), fmt))
    assert error(r) == (400, "INVALID_IMAGE_TYPE", f"Banner must be a JPG or PNG image. Your file is {name}.")


# ------------------------------------------- new vs. existing banner images --
def test_new_banner_must_use_an_uploaded_image_meeting_the_rules(client, admin_headers):
    def create(image_url):
        return client.post("/api/banners", json=banner_payload("New", image_url=image_url), headers=admin_headers)

    assert error(create("https://cdn.example.com/banner.png"))[1] == "IMAGE_UPLOAD_REQUIRED"
    assert error(create("/uploads/banners/missing.png"))[1] == "IMAGE_NOT_FOUND"
    assert error(create(stored_image("photos/wide.png", (960, 240))))[1] == "IMAGE_UPLOAD_REQUIRED"  # not a banner
    # An older stored file can't be reused to get around the rules.
    status, code, message = error(create(stored_image("banners/old-wide.png", (1200, 300))))
    assert (status, code) == (400, "INVALID_IMAGE_SIZE") and "960 x 240" in message
    assert create(stored_image("banners/ok.png", (960, 240))).status_code == 201


def test_existing_banner_that_breaks_the_rules_keeps_working(client, db, admin, admin_headers, template, john):
    old = legacy_banner(db, admin, "Old", stored_image("banners/old.png", (1200, 300)))
    # Edited without changing the image, published and shown in signatures.
    r = client.put(f"/api/banners/{old.id}", json=banner_payload("Old renamed", image_url=old.image_url),
                   headers=admin_headers)
    assert r.status_code == 200, r.text
    assert publish(client, admin_headers, old.id).status_code == 200
    html = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]["html"]
    assert "https://sig.test/uploads/banners/old.png" in html
    assert client.get("/banner/current.png").status_code == 200
    # Replacing its image is a new image, so the rules apply.
    r = client.put(f"/api/banners/{old.id}", json=banner_payload("Old", image_url="https://cdn.example.com/x.png"),
                   headers=admin_headers)
    assert error(r)[1] == "IMAGE_UPLOAD_REQUIRED"


def test_existing_external_banner_keeps_working(client, db, admin, admin_headers, template, john):
    ext = legacy_banner(db, admin, "Ext", "https://cdn.example.com/banner.png")
    r = client.put(f"/api/banners/{ext.id}", json=banner_payload("Ext", image_url=ext.image_url,
                                                                  target_url="https://example.com/new"),
                   headers=admin_headers)
    assert r.status_code == 200, r.text
    publish(client, admin_headers, ext.id)
    html = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]["html"]
    assert "https://cdn.example.com/banner.png" in html


def test_banner_list_flags_images_that_are_not_960_by_240(client, db, admin, admin_headers):
    ok = create_banner(client, admin_headers, "Ok")
    legacy_banner(db, admin, "Old", stored_image("banners/old.png", (1200, 300)))
    legacy_banner(db, admin, "Ext", "https://cdn.example.com/banner.png")
    rows = {b["name"]: b for b in client.get("/api/banners", headers=admin_headers).json()["data"]}
    assert rows["Ok"]["meets_size_rule"] is True and ok["meets_size_rule"] is True
    assert rows["Old"]["meets_size_rule"] is False
    assert rows["Ext"]["meets_size_rule"] is None  # hosted elsewhere: size unknown


# ------------------------------------------------------- fixed banner height --
def _img_tag(html: str, src_part: str) -> str:
    """The <img ...> tag whose src contains src_part."""
    at = html.index(f'src="{src_part}')
    return html[html.rindex("<img", 0, at):html.index("/>", at)]


def test_960_by_240_banner_has_a_fixed_height_of_120_where_the_banner_is_known(client, admin_headers, template, john):
    a = create_banner(client, admin_headers, "Known")
    publish(client, admin_headers, a["id"])
    data = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]
    assert 'width="480" height="120"' in _img_tag(data["html"], "https://sig.test/uploads/banners/known.png")
    addin = client.get("/api/outlook/signature?email=john@company.com").text  # built fresh for every email
    assert 'height="120"' in _img_tag(addin, "https://sig.test/banner/current.png?v=")
    # Saved signatures (installer, setup page) point at whatever is published later: automatic height.
    assert "height=" not in _img_tag(data["live_html"], "https://sig.test/banner/current.png")


def test_older_banner_of_another_size_is_never_given_the_fixed_height(client, db, admin, admin_headers, template, john):
    old = legacy_banner(db, admin, "Old", stored_image("banners/old.png", (1200, 300)))
    publish(client, admin_headers, old.id)
    html = client.get(f"/api/signatures/{john.id}", headers=admin_headers).json()["data"]["html"]
    assert "height=" not in _img_tag(html, "https://sig.test/uploads/banners/old.png")


# ------------------------------------------------------------ employee photo --
def _employee(client, headers, **extra):
    return client.post("/api/employees", json={**PAYLOAD, **extra}, headers=headers)


def test_new_employee_photo_must_be_an_upload_meeting_the_rules(client, admin_headers):
    assert error(_employee(client, admin_headers, profile_photo_url="https://cdn.example.com/me.jpg"))[1] \
        == "IMAGE_UPLOAD_REQUIRED"
    status, code, message = error(_employee(client, admin_headers,
                                            profile_photo_url=stored_image("photos/small.png", (200, 200))))
    assert (status, code) == (400, "INVALID_IMAGE_SIZE") and "at least 256 x 256 px" in message
    r = _employee(client, admin_headers, profile_photo_url=stored_image("photos/ok.jpg", (256, 256), "JPEG"))
    assert r.status_code == 201, r.text
    assert _employee(client, admin_headers, employee_code="EMP-NOPHOTO", email="nophoto@company.com").status_code == 201


@pytest.mark.parametrize("old_photo", ["https://cdn.example.com/old.jpg", "small"])
def test_existing_employee_photo_that_breaks_the_rules_keeps_working(client, db, admin_headers, template, old_photo):
    if old_photo == "small":
        old_photo = stored_image("photos/old-small.png", (176, 176))
    emp = make_employee(db, code="EMP-OLD", first="Old", last="Photo", designation="Analyst",
                        email="old@company.com", with_login=False, profile_photo_url=old_photo)
    body = {**PAYLOAD, "employee_code": "EMP-OLD", "first_name": "Old", "last_name": "Photo",
            "email": "old@company.com", "designation": "Senior Analyst", "profile_photo_url": old_photo}
    r = client.put(f"/api/employees/{emp.id}", json=body, headers=admin_headers)
    assert r.status_code == 200, r.text
    assert client.get(f"/api/signatures/{emp.id}", headers=admin_headers).status_code == 200
    # A new photo must meet the rules; removing the photo is always allowed.
    r = client.put(f"/api/employees/{emp.id}", headers=admin_headers,
                   json={**body, "profile_photo_url": stored_image("photos/new-small.png", (100, 100))})
    assert error(r)[1] == "INVALID_IMAGE_SIZE"
    assert client.put(f"/api/employees/{emp.id}", json={**body, "profile_photo_url": None},
                      headers=admin_headers).status_code == 200


def test_photos_from_nexusauth_are_exempt(db, tmp_path, monkeypatch):
    from app.core.config import get_settings
    from app.services.nexus_sync import sync_employees
    from tests.test_nexus_sync import FakeNexus, employee_by_email, nexus_employee

    monkeypatch.setattr(get_settings(), "upload_dir", str(tmp_path))
    ref = "/uploads/employee_photos/tiny.webp"
    fake = FakeNexus([nexus_employee(1, "ravi@casterly.com", photo_reference=ref)],
                     files={ref: image_bytes((64, 64), "WEBP")})  # WebP and far below 256 px
    assert sync_employees(db, fake.client()).ok
    assert employee_by_email(db, "ravi@casterly.com").profile_photo_url.startswith("/uploads/photos/nexus-")


# ------------------------------------------------------------- company logo --
def test_built_in_logo_meets_the_logo_rule():
    """The logo is built into the app (no upload): PNG, at least 200 px tall, max 200 KB."""
    data = branding.LOGO_FILE.read_bytes()
    assert len(data) <= 200 * 1024, f"logo is {len(data) // 1024} KB"
    with Image.open(io.BytesIO(data)) as img:
        assert img.format == "PNG"
        assert img.height >= 200, f"logo is {img.height} px tall"
