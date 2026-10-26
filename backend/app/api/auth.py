from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import AuthContext, get_auth_context, get_current_user
from app.database.database import get_db
from app.database.models import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.schemas.common import ApiResponse, ok
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _me(user: User) -> dict:
    return {"user": user, "employee": user.employee}


@router.post("/login", response_model=ApiResponse[LoginResponse])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user, token, expires = auth_service.authenticate(db, body.email, body.password, body.remember_me)
    return ok({**_me(user), "access_token": token, "token_type": "bearer", "expires_at": expires})


@router.get("/me", response_model=ApiResponse[MeResponse])
def me(user: User = Depends(get_current_user)):
    return ok(_me(user))


@router.post("/logout", response_model=ApiResponse[dict])
def logout(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    auth_service.logout(db, ctx.user, ctx.jti, ctx.expires_at)
    return ok({"message": "Signed out."})
