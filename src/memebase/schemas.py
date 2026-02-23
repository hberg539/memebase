from typing import NotRequired, TypedDict


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
