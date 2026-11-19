"""File storage behind a small interface so local disk can later be swapped for S3/Azure Blob."""
import io
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from PIL import Image, UnidentifiedImageError

from app.core.config import get_settings
from app.core.errors import AppError

ALLOWED_FORMATS = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}
UPLOAD_KINDS = {"banner": "banners", "photo": "photos"}


class Storage(Protocol):
    def save(self, data: bytes, key: str) -> str:
        """Persist bytes and return the public path/URL that should be stored in the DB."""

    def local_file(self, public_path: str) -> Path | None:
        """The file behind a stored '/uploads/...' path, if this storage holds it locally."""


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root)

    def local_file(self, public_path: str) -> Path | None:
        if not public_path.startswith("/uploads/"):
            return None
        target = (self.root / public_path.removeprefix("/uploads/")).resolve()
        if self.root.resolve() not in target.parents or not target.is_file():
            return None
        return target

    def save(self, data: bytes, key: str) -> str:
        target = (self.root / key).resolve()
        if self.root.resolve() not in target.parents:
            raise AppError(400, "INVALID_PATH", "Invalid upload path.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        return f"/uploads/{key}"


def get_storage() -> Storage:
    return LocalStorage(get_settings().upload_dir)


def _open_image(data: bytes) -> tuple[str, tuple[int, int]]:
    """(Pillow format, (width, height)) of a valid image, otherwise raise."""
    if not data:
        raise AppError(400, "INVALID_IMAGE", "The uploaded file is empty.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt, size = img.format, img.size
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise AppError(400, "INVALID_IMAGE", "The file is not a valid image.") from None
    return fmt, size


def validate_image(data: bytes) -> str:
    """Return the file extension for a valid image, otherwise raise.

    The general check, without the per-kind upload rules: used for photos copied from nexusAuth,
    which is the source of truth for them.
    """
    settings = get_settings()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(413, "FILE_TOO_LARGE", f"Images must be smaller than {settings.max_upload_mb} MB.")
    fmt, _ = _open_image(data)
    if fmt not in ALLOWED_FORMATS:
        raise AppError(400, "INVALID_IMAGE", "Only PNG, JPEG, GIF and WebP images are supported.")
    return ALLOWED_FORMATS[fmt]


# ------------------------------------------------------------- upload rules --
# Every new or changed photo and banner must meet these. Images stored before the rules
# existed keep working: they are only checked when they are replaced.
@dataclass(frozen=True)
class UploadRule:
    label: str
    max_kb: int
    exact_size: tuple[int, int] | None = None
    min_size: tuple[int, int] | None = None
    formats: tuple[str, ...] = ("JPEG", "PNG")

    def hint(self) -> str:
        if self.exact_size:
            size = f"Must be exactly {self.exact_size[0]} x {self.exact_size[1]} px."
        else:
            size = f"At least {self.min_size[0]} x {self.min_size[1]} px."
        return f"{size} JPG or PNG, max {self.max_kb} KB."


BANNER_SIZE = (960, 240)  # shown at 480 x 120 in signatures: sharp on high-DPI screens
UPLOAD_RULES = {
    "photo": UploadRule("Photo", max_kb=300, min_size=(256, 256)),
    "banner": UploadRule("Banner", max_kb=500, exact_size=BANNER_SIZE),
}
_FORMAT_NAMES = {"JPEG": "JPG", "PNG": "PNG", "GIF": "GIF", "WEBP": "WebP"}


def _kb(size_bytes: int) -> int:
    return -(-size_bytes // 1024)  # rounded up, so a file over the limit never reads as "500 KB"


def too_large(kind: str, size_bytes: int) -> AppError:
    rule = UPLOAD_RULES[kind]
    return AppError(413, "FILE_TOO_LARGE",
                    f"{rule.label} must be {rule.max_kb} KB or smaller. Your file is {_kb(size_bytes)} KB.")


def check_upload(data: bytes, kind: str) -> str:
    """Apply UPLOAD_RULES[kind]; return the file extension, otherwise raise with a clear message."""
    if kind not in UPLOAD_RULES:
        raise AppError(400, "INVALID_UPLOAD_KIND", "Upload kind must be 'banner' or 'photo'.")
    rule = UPLOAD_RULES[kind]
    if len(data) > rule.max_kb * 1024:
        raise too_large(kind, len(data))
    fmt, (w, h) = _open_image(data)
    if fmt not in rule.formats:
        raise AppError(400, "INVALID_IMAGE_TYPE",
                       f"{rule.label} must be a JPG or PNG image. Your file is {_FORMAT_NAMES.get(fmt, fmt)}.")
    if rule.exact_size and (w, h) != rule.exact_size:
        need_w, need_h = rule.exact_size
        raise AppError(400, "INVALID_IMAGE_SIZE",
                       f"{rule.label} must be exactly {need_w} x {need_h} px. Your image is {w} x {h} px.")
    if rule.min_size and (w < rule.min_size[0] or h < rule.min_size[1]):
        need_w, need_h = rule.min_size
        raise AppError(400, "INVALID_IMAGE_SIZE",
                       f"{rule.label} must be at least {need_w} x {need_h} px. Your image is {w} x {h} px.")
    return ALLOWED_FORMATS[fmt]


def save_image(data: bytes, kind: str) -> str:
    ext = check_upload(data, kind)
    key = f"{UPLOAD_KINDS[kind]}/{uuid.uuid4().hex}.{ext}"
    return get_storage().save(data, key)


def check_new_image_ref(ref: str, kind: str) -> None:
    """A photo or banner being set or changed must be a file uploaded here that meets the rules.

    Links to images on other websites are no longer accepted for new images (existing ones
    keep working), and an older stored file can't be reused to get around the rules.
    """
    label = UPLOAD_RULES[kind].label
    if not ref.startswith(f"/uploads/{UPLOAD_KINDS[kind]}/"):
        raise AppError(400, "IMAGE_UPLOAD_REQUIRED",
                       f"Upload the {label.lower()} image. Links to images on other websites aren't accepted.")
    local = get_storage().local_file(ref)
    if local is None:
        raise AppError(400, "IMAGE_NOT_FOUND", f"The {label.lower()} image wasn't found. Upload it again.")
    check_upload(local.read_bytes(), kind)


@lru_cache(maxsize=512)
def _file_size(path: Path, mtime_ns: int) -> tuple[int, int] | None:
    try:
        with Image.open(path) as img:
            return img.size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        return None


def image_size(ref: str | None) -> tuple[int, int] | None:
    """(width, height) of a stored '/uploads/...' image; None if hosted elsewhere or unreadable.

    Cached per file version (path + modification time), as it is read for every signature.
    """
    local = get_storage().local_file(ref) if ref else None
    if local is None:
        return None
    return _file_size(local, local.stat().st_mtime_ns)
