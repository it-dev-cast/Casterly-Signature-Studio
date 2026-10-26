"""File storage behind a small interface so local disk can later be swapped for S3/Azure Blob."""
import io
import uuid
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


def validate_image(data: bytes) -> str:
    """Return the file extension for a valid image, otherwise raise."""
    settings = get_settings()
    if not data:
        raise AppError(400, "INVALID_IMAGE", "The uploaded file is empty.")
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise AppError(413, "FILE_TOO_LARGE", f"Images must be smaller than {settings.max_upload_mb} MB.")
    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise AppError(400, "INVALID_IMAGE", "The file is not a valid image.") from None
    if fmt not in ALLOWED_FORMATS:
        raise AppError(400, "INVALID_IMAGE", "Only PNG, JPEG, GIF and WebP images are supported.")
    return ALLOWED_FORMATS[fmt]


def save_image(data: bytes, kind: str) -> str:
    if kind not in UPLOAD_KINDS:
        raise AppError(400, "INVALID_UPLOAD_KIND", "Upload kind must be 'banner' or 'photo'.")
    ext = validate_image(data)
    key = f"{UPLOAD_KINDS[kind]}/{uuid.uuid4().hex}.{ext}"
    return get_storage().save(data, key)
