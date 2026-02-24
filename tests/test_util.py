from memebase.util import normalize_tags, parse_ext, sanitize_filename


def test_normal_filename():
    assert sanitize_filename("hello.png") == "hello.png"


def test_utf8_preserved():
    assert sanitize_filename("café_mème.jpg") == "café_mème.jpg"
    assert sanitize_filename("日本語ファイル.png") == "日本語ファイル.png"


def test_forbidden_chars_replaced():
    assert sanitize_filename('he<l>lo:"world".png') == "he_l_lo__world_.png"
    assert sanitize_filename("file|name?.jpg") == "file_name_.jpg"
    assert sanitize_filename("star*file.gif") == "star_file.gif"


def test_control_chars_replaced():
    assert sanitize_filename("bad\x00\x1fname.png") == "bad__name.png"


def test_path_traversal_stripped():
    assert sanitize_filename("../../etc/passwd.png") == "passwd.png"
    assert sanitize_filename("C:\\Users\\me\\photo.jpg") == "photo.jpg"
    assert sanitize_filename("/tmp/secret/file.webp") == "file.webp"


def test_leading_trailing_dots_stripped():
    assert sanitize_filename(".hidden.png") == "hidden.png"
    assert sanitize_filename("...dots...png") == "dots.png"
    assert sanitize_filename("..png") == "unnamed.png"


def test_leading_trailing_spaces_stripped():
    assert sanitize_filename("  spaced  .jpg") == "spaced.jpg"


def test_windows_reserved_names():
    assert sanitize_filename("CON.png") == "_CON.png"
    assert sanitize_filename("con.jpg") == "_con.jpg"
    assert sanitize_filename("PRN.gif") == "_PRN.gif"
    assert sanitize_filename("AUX.webp") == "_AUX.webp"
    assert sanitize_filename("NUL.png") == "_NUL.png"
    assert sanitize_filename("COM1.jpg") == "_COM1.jpg"
    assert sanitize_filename("LPT3.png") == "_LPT3.png"


def test_reserved_name_not_false_positive():
    assert sanitize_filename("CONQUER.png") == "CONQUER.png"
    assert sanitize_filename("console.jpg") == "console.jpg"


def test_empty_stem_fallback():
    assert sanitize_filename(".png") == "unnamed.png"
    assert sanitize_filename("   .jpg") == "unnamed.jpg"


def test_completely_empty():
    assert sanitize_filename("") == "unnamed"


def test_long_filename_truncated():
    long_name = "a" * 300 + ".png"
    result = sanitize_filename(long_name)
    assert result.endswith(".png")
    assert len(result.encode("utf-8")) <= 200


def test_long_utf8_filename_truncated():
    # Each char is 3 bytes in UTF-8
    long_name = "\u4e2d" * 200 + ".png"
    result = sanitize_filename(long_name)
    assert result.endswith(".png")
    assert len(result.encode("utf-8")) <= 200


def test_mixed_separators():
    assert sanitize_filename("path/to\\file.png") == "file.png"


def test_extension_preserved():
    assert sanitize_filename("my:file.webm") == "my_file.webm"
    assert sanitize_filename("test<>.mp4") == "test__.mp4"


# ---------------------------------------------------------------------------
# parse_ext
# ---------------------------------------------------------------------------


def test_parse_ext_basic():
    assert parse_ext("photo.png") == "png"


def test_parse_ext_uppercase():
    assert parse_ext("photo.PNG") == "png"


def test_parse_ext_mixed_case():
    assert parse_ext("photo.JpEg") == "jpeg"


def test_parse_ext_no_extension():
    assert parse_ext("README") == ""


def test_parse_ext_dotfile():
    assert parse_ext(".gitignore") == ""


def test_parse_ext_multiple_dots():
    assert parse_ext("archive.tar.gz") == "gz"


def test_parse_ext_trailing_dot():
    assert parse_ext("file.") == ""


def test_parse_ext_empty_string():
    assert parse_ext("") == ""


def test_parse_ext_path_like():
    assert parse_ext("some/path/photo.WEBP") == "webp"


# ---------------------------------------------------------------------------
# normalize_tags
# ---------------------------------------------------------------------------


def test_tags_lowercase_and_strip():
    assert normalize_tags(["  Hello ", "WORLD"]) == {"hello", "world"}


def test_tags_dedup():
    assert normalize_tags(["a", "A", "a"]) == {"a"}


def test_tags_empty_filtered():
    assert normalize_tags(["", "  ", "ok"]) == {"ok"}


def test_tags_all_empty():
    assert normalize_tags(["", " "]) == set()
