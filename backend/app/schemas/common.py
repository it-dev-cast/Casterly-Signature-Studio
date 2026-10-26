from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def ok(data) -> dict:
    return {"success": True, "data": data}
