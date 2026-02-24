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


class ThumbnailsConfig(TypedDict):
    enabled: bool
    max_size: int
    quality: int
    format: str
    skip_types: list[str]


class ServerConfig(TypedDict):
    host: str
    port: int
    max_upload_size: int


class UiConfig(TypedDict):
    theme: str


class AppConfig(TypedDict):
    server: ServerConfig
    grid: GridConfig
    ui: UiConfig
    thumbnails: ThumbnailsConfig
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
    ext: str
    description: str
    favorite: int
    created_at: str
    tags: list[str]
    duplicate: NotRequired[bool]
