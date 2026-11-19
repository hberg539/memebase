import base64
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

from memebase.ai import analyze_meme, build_prompt, parse_ai_response


class TestBuildPrompt:
    def test_substitutes_tags(self):
        result = build_prompt("Use these tags: {tags}", ["funny", "cat"])
        assert result == "Use these tags: funny, cat"

    def test_empty_tags(self):
        result = build_prompt("Tags: {tags}", [])
        assert result == "Tags: "

    def test_no_placeholder(self):
        result = build_prompt("No placeholder here", ["a"])
        assert result == "No placeholder here"


class TestParseAiResponse:
    def test_plain_json(self):
        result = parse_ai_response('{"name": "test", "tags": ["a"]}')
        assert result == {"name": "test", "tags": ["a"]}

    def test_fenced_json(self):
        result = parse_ai_response('```json\n{"name": "test"}\n```')
        assert result == {"name": "test"}

    def test_fenced_no_lang(self):
        result = parse_ai_response('```\n{"name": "test"}\n```')
        assert result == {"name": "test"}

    def test_invalid_json(self):
        with pytest.raises(Exception):
            parse_ai_response("not json at all")


EXAMPLE_GIF = Path(__file__).parent / "fixtures" / "deploy.gif"


def request_content(path: Path, *, gif_frames: bool = True) -> list[dict]:
    with patch("memebase.ai.litellm.completion") as completion:
        completion.return_value.choices[0].message.content = '{"tags": ["deploy"]}'
        assert analyze_meme(
            str(path),
            ["deploy"],
            model="example",
            prompt_template="Tags: {tags}",
            gif_frames=gif_frames,
        ) == {"tags": ["deploy"]}
    (message,) = completion.call_args.kwargs["messages"]
    assert message["content"][-1] == {"type": "text", "text": "Tags: deploy"}
    return message["content"][:-1]


def test_gif_sends_composited_frames_and_delays_in_order() -> None:
    header, *parts = request_content(EXAMPLE_GIF)
    assert "3 of 3" in header["text"]
    with Image.open(EXAMPLE_GIF) as original:
        for i, (start, delay) in enumerate([(0, 600), (600, 120), (720, 1200)]):
            label, image = parts[2 * i : 2 * i + 2]
            assert label["text"] == f"Frame {i + 1}, start {start} ms, delay {delay} ms."
            prefix, data = image["image_url"]["url"].split(",", 1)
            assert prefix == "data:image/png;base64"
            with Image.open(BytesIO(base64.b64decode(data))) as rendered:
                original.seek(i)
                assert rendered.tobytes() == original.convert("RGB").tobytes()


def test_long_gif_keeps_flash_pause_and_endpoints(tmp_path: Path) -> None:
    path = tmp_path / "long.gif"
    frames = [Image.new("RGB", (24, 24), (i, i, i)) for i in range(31)]
    frames[10].paste("white", (0, 0, 24, 24))
    durations = [100] * len(frames)
    durations[10] = 20
    durations[22] = 1000
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations)
    header, *parts = request_content(path)
    assert "12 of 31" in header["text"]
    labels = [part["text"] for part in parts if part["type"] == "text"]
    numbers = [int(label.split(",")[0].split()[1]) for label in labels]
    assert len(numbers) == len(set(numbers)) == 12
    assert numbers == sorted(numbers)
    assert {1, 11, 23, 31}.issubset(numbers)


@pytest.mark.parametrize("fmt", ["PNG", "GIF"])
def test_static_image_keeps_original_bytes(tmp_path: Path, fmt: str) -> None:
    path = tmp_path / f"still.{fmt.lower()}"
    Image.new("RGB", (4, 4), "red").save(path)
    (part,) = request_content(path)
    expected = base64.b64encode(path.read_bytes()).decode("ascii")
    assert part["image_url"]["url"] == f"data:image/{fmt.lower()};base64,{expected}"


def test_gif_opt_out_sends_original_file() -> None:
    (part,) = request_content(EXAMPLE_GIF, gif_frames=False)
    expected = base64.b64encode(EXAMPLE_GIF.read_bytes()).decode("ascii")
    assert part["image_url"]["url"] == f"data:image/gif;base64,{expected}"
