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
    title: str
    theme: str


class ScrapeConfig(TypedDict):
    max_files: int


class AppConfig(TypedDict):
    server: ServerConfig
    grid: GridConfig
    ui: UiConfig
    thumbnails: ThumbnailsConfig
    ai: AiConfig
    scrape: ScrapeConfig


class AiSuggestion(TypedDict, total=False):
    name: str
    description: str
    tags: list[str]


class Collection(TypedDict):
    id: str
    slug: str
    name: str


class SourceMeta(TypedDict):
    source_url: str
    source_site: str
    source_author: str
    source_text: str
    source_date: str | None


class FileMeta(TypedDict):
    width: int | None
    height: int | None
    duration: float | None


class Meme(TypedDict):
    id: str
    sha256: str
    size: int
    filename: str
    ext: str
    description: str
    favorite: int
    created_at: str
    tags: list[str]
    collection: str | None
    source_url: NotRequired[str | None]
    source_site: NotRequired[str | None]
    source_author: NotRequired[str | None]
    source_text: NotRequired[str | None]
    source_date: NotRequired[str | None]
    width: NotRequired[int | None]
    height: NotRequired[int | None]
    duration: NotRequired[float | None]
    duplicate: NotRequired[bool]
