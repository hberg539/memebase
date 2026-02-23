from enum import StrEnum
from typing import NotRequired, TypedDict


class MemeError(StrEnum):
    NOT_IN_DB = "not_in_db"
    NOT_ON_DISK = "not_on_disk"


class Meme(TypedDict):
    uuid: str
    sha256: str
    size: int
    filename: str
    description: str
    copy_count: int
    favorite: int
    created_at: str
    tags: list[str]
    duplicate: NotRequired[bool]
