from fastapi import APIRouter, Depends

from app.core.errors import AppError
from app.core.dependencies import require_admin
from app.core.config import get_settings
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import User
from app.schemas.common import ok
from app.services import nexus_sync

router = APIRouter(prefix="/integrations/nexusauth", tags=["integrations"])


@router.get("")
def nexusauth_status(_: User = Depends(require_admin)):
    """Whether employees sync from nexusAuth, and how the last sync went."""
    return ok(nexus_sync.status())


@router.post("/sync")
def nexusauth_sync_now(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    """Run the nexusAuth employee sync now."""
    if not get_settings().nexus_enabled:
        raise AppError(409, "NEXUSAUTH_NOT_CONFIGURED",
                       "nexusAuth sync is not set up. Add NEXUSAUTH_URL, NEXUSAUTH_EMAIL and NEXUSAUTH_PASSWORD to backend/.env.")
    nexus_sync.run_sync(lambda: db)
    return ok(nexus_sync.status())
