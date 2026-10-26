from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile, status

from app.core.config import get_settings
from app.core.dependencies import require_admin
from app.core.errors import AppError
from app.database.models import User
from app.schemas.common import ApiResponse, ok
from app.schemas.misc import UploadRead
from app.services import storage_service
from app.utils.urls import resolve_public_url

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=ApiResponse[UploadRead], status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    kind: Literal["banner", "photo"] = Form(...),
    _: User = Depends(require_admin),
):
    limit = get_settings().max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise AppError(413, "FILE_TOO_LARGE", f"Images must be smaller than {get_settings().max_upload_mb} MB.")
    path = storage_service.save_image(data, kind)
    return ok({"path": path, "url": resolve_public_url(path)})
