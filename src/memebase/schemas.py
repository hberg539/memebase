from enum import StrEnum
from typing import NotRequired, TypedDict


class MemeError(StrEnum):
    NOT_IN_DB = "not_in_db"
    NOT_ON_DISK = "not_on_disk"


class GridConfig(TypedDict):
    layout: str
    thumbnail_size: int
    per_page: str | int


class AiConfig(TypedDict):
    enabled: bool
    model: str
    parallel: int
    prompt: str


class AppConfig(TypedDict):
    grid: GridConfig
    ai: AiConfig


class AiSuggestion(TypedDict, total=False):
    name: str
    description: str
    tags: list[str]


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
