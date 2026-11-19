from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.config import get_settings
from app.core.dependencies import require_admin
from app.database.models import User
from app.schemas.common import ApiResponse, ok
from app.schemas.misc import UploadRead
from app.services import storage_service
from app.utils.urls import resolve_public_url

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.get("/rules")
def upload_rules(_: User = Depends(require_admin)):
    """The rules each kind of upload must meet, so the upload screens show the same ones."""
    return ok({
        kind: {
            "max_kb": rule.max_kb,
            "formats": ["jpg", "png"],
            "exact_width": rule.exact_size[0] if rule.exact_size else None,
            "exact_height": rule.exact_size[1] if rule.exact_size else None,
            "min_width": rule.min_size[0] if rule.min_size else None,
            "min_height": rule.min_size[1] if rule.min_size else None,
            "hint": rule.hint(),
        }
        for kind, rule in storage_service.UPLOAD_RULES.items()
    })


@router.post("", response_model=ApiResponse[UploadRead], status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    kind: Literal["banner", "photo"] = Form(...),
    _: User = Depends(require_admin),
):
    # MAX_UPLOAD_MB caps how much of any request is read; the per-kind limits are far lower.
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise storage_service.too_large(kind, file.size or len(data))
    path = storage_service.save_image(data, kind)
    return ok({"path": path, "url": resolve_public_url(path)})
