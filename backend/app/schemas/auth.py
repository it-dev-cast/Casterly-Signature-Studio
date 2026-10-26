from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.database.models import UserRole
from app.schemas.common import ORMModel
from app.schemas.employee import EmployeeRead


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    remember_me: bool = False


class UserRead(ORMModel):
    id: int
    email: str
    role: UserRole
    is_active: bool


class MeResponse(BaseModel):
    user: UserRead
    employee: EmployeeRead | None = None


class LoginResponse(MeResponse):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
