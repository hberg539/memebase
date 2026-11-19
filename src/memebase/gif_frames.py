"""Build the visual input for auto-detect on animated GIFs."""

from base64 import b64encode
from bisect import bisect_right
from io import BytesIO

from PIL import Image, ImageChops, ImageSequence

MAX_FRAMES = 12


def _thumbnail(frame: Image.Image, size: int) -> Image.Image:
    rgba = frame.convert("RGBA")
    rgba.thumbnail((size, size), Image.Resampling.LANCZOS)
    result = Image.new("RGB", rgba.size, "white")
    result.paste(rgba, mask=rgba.getchannel("A"))
    return result


def _sample(starts: list[int], durations: list[int], changes: list[int], end: int) -> list[int]:
    count = len(starts)
    if count <= MAX_FRAMES:
        return list(range(count))

    # Keep the ending and longest pause. Spread anchors across playback time.
    selected = {0, count - 1, max(range(count), key=durations.__getitem__)}
    for step in range(1, 6):
        selected.add(bisect_right(starts, end * step / 6) - 1)

    def priority(i: int) -> tuple[int, int]:
        return changes[i], min(abs(starts[i] - starts[j]) for j in selected)

    while len(selected) < MAX_FRAMES:
        selected.add(max((i for i in range(count) if i not in selected), key=priority))
    return sorted(selected)


def gif_content(gif: Image.Image) -> list[dict]:
    """Sample composited frames, keeping only small previews between iterations."""
    starts: list[int] = []
    durations: list[int] = []
    changes: list[int] = []
    previous = None
    elapsed = 0
    for frame in ImageSequence.Iterator(gif):
        duration = frame.info.get("duration", 0)
        starts.append(elapsed)
        durations.append(duration)
        elapsed += duration or 100

        preview = _thumbnail(frame, 64)
        change = 0
        if previous is not None:
            # Score the most changed tile so a small, brief reaction can win a slot.
            tiles = ImageChops.difference(preview, previous).resize((8, 8), Image.Resampling.BOX)
            change = max(high for _, high in tiles.getextrema())
        changes.append(change)
        previous = preview

    indices = _sample(starts, durations, changes, elapsed)
    header = f"Animated GIF: showing {len(indices)} of {len(starts)} frames in playback order."
    if 0 in durations:
        header += " Start times assume 100 ms for frames without a positive delay."
    parts = [{"type": "text", "text": header}]
    for i in indices:
        gif.seek(i)
        buffer = BytesIO()
        _thumbnail(gif, 512).save(buffer, format="PNG")
        data = b64encode(buffer.getvalue()).decode("ascii")
        delay = f"{durations[i]} ms" if durations[i] else "unspecified"
        label = f"Frame {i + 1}, start {starts[i]} ms, delay {delay}."
        parts.append({"type": "text", "text": label})
        parts.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{data}"}})
    return parts
