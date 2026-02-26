from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest

from memebase.app import create_app
from memebase.schemas import MemeError

FAKE_MEME = {
    "uuid": "test-uuid-1234",
    "sha256": "abc123",
    "size": 100,
    "filename": "test.png",
    "ext": "png",
    "description": "",
    "favorite": 0,
    "created_at": "2024-01-01 00:00:00",
    "tags": [],
}

TEST_CONFIG = {
    "server": {"host": "0.0.0.0", "port": 5000, "max_upload_size": 100},
    "grid": {"layout": "grid", "thumbnail_size": 220, "per_page": "auto"},
    "ui": {"title": "Memebase", "theme": "midnight"},
    "thumbnails": {
        "enabled": True,
        "max_size": 440,
        "quality": 80,
        "format": "webp",
        "skip_types": ["gif"],
    },
    "ai": {
        "enabled": True,
        "model": "gpt-4o",
        "parallel": 3,
        "prompt": "Describe this meme. Tags: {tags}",
    },
    "scrape": {
        "max_files": 4,
    },
}


@pytest.fixture
def client():
    app = create_app(config=TEST_CONFIG)
    app.config["TESTING"] = True
    return app.test_client()


class TestUploadMemes:
    def test_no_files_returns_400(self, client):
        resp = client.post("/api/memes")
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "No files provided"

    def test_disallowed_extension_skipped(self, client):
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.register_meme") as mock_register,
        ):
            resp = client.post(
                "/api/memes",
                data={"files": (BytesIO(b"hello"), "test.txt")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 201
        assert resp.get_json() == []
        mock_register.assert_not_called()

    def test_successful_upload(self, client, tmp_path):
        dest = tmp_path / "test.png"
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.resolve_unique_path", return_value=(dest, "test.png")),
            patch("memebase.app.register_meme", return_value=(FAKE_MEME.copy(), False)),
        ):
            resp = client.post(
                "/api/memes",
                data={"files": (BytesIO(b"\x89PNG"), "test.png")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["uuid"] == "test-uuid-1234"
        assert dest.exists()

    def test_duplicate_marked(self, client, tmp_path):
        dest = tmp_path / "test.png"
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.resolve_unique_path", return_value=(dest, "test.png")),
            patch("memebase.app.register_meme", return_value=(FAKE_MEME.copy(), True)),
        ):
            resp = client.post(
                "/api/memes",
                data={"files": (BytesIO(b"\x89PNG"), "test.png")},
                content_type="multipart/form-data",
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["duplicate"] is True


class TestUploadFromUrl:
    def test_missing_url_returns_400(self, client):
        resp = client.post("/api/memes/url", json={})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "No URL provided"

    def test_empty_url_returns_400(self, client):
        resp = client.post("/api/memes/url", json={"url": "  "})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "No URL provided"

    def test_scrape_error_returns_400(self, client):
        with patch("memebase.app.scrape_url", side_effect=ValueError("bad url")):
            resp = client.post("/api/memes/url", json={"url": "http://example.com/x.png"})
        assert resp.status_code == 400
        assert resp.get_json()["error"] == "bad url"

    def test_new_file_returns_201(self, client, tmp_path):
        dest = tmp_path / "meme.png"
        with (
            patch("memebase.app.scrape_url", return_value=[("meme.png", b"imgdata")]),
            patch("memebase.app.resolve_unique_path", return_value=(dest, "meme.png")),
            patch("memebase.app.get_db"),
            patch("memebase.app.register_meme", return_value=(FAKE_MEME.copy(), False)),
        ):
            resp = client.post("/api/memes/url", json={"url": "http://example.com/meme.png"})
        assert resp.status_code == 201
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["uuid"] == "test-uuid-1234"
        assert dest.read_bytes() == b"imgdata"

    def test_duplicate_returns_200(self, client, tmp_path):
        dest = tmp_path / "meme.png"
        with (
            patch("memebase.app.scrape_url", return_value=[("meme.png", b"imgdata")]),
            patch("memebase.app.resolve_unique_path", return_value=(dest, "meme.png")),
            patch("memebase.app.get_db"),
            patch("memebase.app.register_meme", return_value=(FAKE_MEME.copy(), True)),
        ):
            resp = client.post("/api/memes/url", json={"url": "http://example.com/meme.png"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["duplicate"] is True


class TestUpdateMeme:
    def test_not_found_returns_404(self, client):
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=(None, None, MemeError.NOT_IN_DB),
            ),
        ):
            resp = client.put("/api/memes/unknown", json={})
        assert resp.status_code == 404

    def test_update_favorite(self, client):
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("test.png", Path("/tmp/test.png"), None),
            ),
            patch("memebase.app.update_favorite") as mock_fav,
            patch("memebase.app.get_meme", return_value={**FAKE_MEME, "favorite": 1}),
        ):
            resp = client.put("/api/memes/test-uuid-1234", json={"favorite": True})
        assert resp.status_code == 200
        mock_fav.assert_called_once()
        assert resp.get_json()["favorite"] == 1

    def test_update_description(self, client):
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("test.png", Path("/tmp/test.png"), None),
            ),
            patch("memebase.app.update_description") as mock_desc,
            patch(
                "memebase.app.get_meme", return_value={**FAKE_MEME, "description": "a funny meme"}
            ),
        ):
            resp = client.put("/api/memes/test-uuid-1234", json={"description": "a funny meme"})
        assert resp.status_code == 200
        mock_desc.assert_called_once()
        assert resp.get_json()["description"] == "a funny meme"

    def test_rename_collision_returns_409(self, client, tmp_path):
        (tmp_path / "new_name.png").write_bytes(b"existing")
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("old.png", tmp_path / "old.png", None),
            ),
            patch("memebase.app.MEMES_DIR", tmp_path),
        ):
            resp = client.put("/api/memes/test-uuid", json={"new_name": "new_name"})
        assert resp.status_code == 409
        assert "already exists" in resp.get_json()["error"]

    def test_rename_success(self, client, tmp_path):
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("old.png", tmp_path / "old.png", None),
            ),
            patch("memebase.app.rename_meme", return_value="new_name.png") as mock_rename,
            patch("memebase.app.get_meme", return_value={**FAKE_MEME, "filename": "new_name.png"}),
        ):
            resp = client.put("/api/memes/test-uuid-1234", json={"new_name": "new_name"})
        assert resp.status_code == 200
        mock_rename.assert_called_once()

    def test_update_tags(self, client):
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("test.png", Path("/tmp/test.png"), None),
            ),
            patch("memebase.app.set_tags") as mock_tags,
            patch("memebase.app.get_meme", return_value={**FAKE_MEME, "tags": ["funny", "cats"]}),
        ):
            resp = client.put("/api/memes/test-uuid-1234", json={"tags": ["funny", "cats"]})
        assert resp.status_code == 200
        mock_tags.assert_called_once()
        assert resp.get_json()["tags"] == ["funny", "cats"]


class TestDeleteMeme:
    def test_success_returns_204(self, client):
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.delete_meme", return_value="test.png"),
        ):
            resp = client.delete("/api/memes/test-uuid")
        assert resp.status_code == 204

    def test_not_found_returns_404(self, client):
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.delete_meme", side_effect=LookupError("Not found")),
        ):
            resp = client.delete("/api/memes/unknown")
        assert resp.status_code == 404

    def test_calls_delete_meme(self, client):
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.delete_meme", return_value="test.png") as mock_del,
        ):
            client.delete("/api/memes/test-uuid")
        mock_del.assert_called_once()


class TestAutoDescribe:
    def test_not_in_db_returns_404(self, client):
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=(None, None, MemeError.NOT_IN_DB),
            ),
        ):
            resp = client.post("/api/memes/unknown/auto")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "Not found"

    def test_not_on_disk_returns_404(self, client):
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("test.png", None, MemeError.NOT_ON_DISK),
            ),
        ):
            resp = client.post("/api/memes/some-uuid/auto")
        assert resp.status_code == 404
        assert resp.get_json()["error"] == "File not found on disk"

    def test_analyze_error_returns_500(self, client):
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("test.png", "/tmp/test.png", None),
            ),
            patch("memebase.app.get_all_tags", return_value=[]),
            patch("memebase.app.analyze_meme", side_effect=RuntimeError("AI broke")),
        ):
            resp = client.post("/api/memes/some-uuid/auto")
        assert resp.status_code == 500
        assert resp.get_json()["error"] == "AI broke"

    def test_success_returns_suggestion(self, client):
        suggestion = {"name": "funny-cat", "description": "A cat meme", "tags": ["cat", "funny"]}
        with (
            patch("memebase.app.get_db"),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("test.png", "/tmp/test.png", None),
            ),
            patch("memebase.app.get_all_tags", return_value=["existing"]),
            patch("memebase.app.analyze_meme", return_value=suggestion),
        ):
            resp = client.post("/api/memes/some-uuid/auto")
        assert resp.status_code == 200
        assert resp.get_json() == suggestion


class TestBulkAuto:
    def test_empty_uuids_returns_400(self, client):
        resp = client.post("/api/memes/bulk/auto", json={"uuids": []})
        assert resp.status_code == 400

    def test_success(self, client):
        suggestion = {"name": "cat", "description": "a cat", "tags": ["cat"]}
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.get_all_tags", return_value=[]),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("test.png", "/tmp/test.png", None),
            ),
            patch("memebase.app.analyze_meme", return_value=suggestion),
            patch("memebase.app.apply_ai_suggestions") as mock_apply,
        ):
            resp = client.post("/api/memes/bulk/auto", json={"uuids": ["uuid-1"]})
        assert resp.status_code == 200
        assert resp.get_json()["uuid-1"] == {"ok": True}
        mock_apply.assert_called_once()

    def test_missing_uuid_skipped(self, client):
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.get_all_tags", return_value=[]),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=(None, None, MemeError.NOT_IN_DB),
            ),
        ):
            resp = client.post("/api/memes/bulk/auto", json={"uuids": ["missing"]})
        assert resp.status_code == 200
        assert "missing" not in resp.get_json()

    def test_partial_failure(self, client):
        ok_suggestion = {"name": "ok", "description": "ok", "tags": []}
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.get_all_tags", return_value=[]),
            patch(
                "memebase.app.get_meme_file_path",
                return_value=("test.png", "/tmp/test.png", None),
            ),
            patch(
                "memebase.app.analyze_meme",
                side_effect=[RuntimeError("AI broke"), ok_suggestion],
            ),
            patch("memebase.app.apply_ai_suggestions"),
        ):
            resp = client.post("/api/memes/bulk/auto", json={"uuids": ["uuid-1", "uuid-2"]})
        data = resp.get_json()
        assert "error" in data["uuid-1"]
        assert data["uuid-2"] == {"ok": True}


class TestBulkTags:
    def test_empty_uuids_returns_400(self, client):
        resp = client.put("/api/memes/bulk/tags", json={"uuids": []})
        assert resp.status_code == 400

    def test_add_tags(self, client):
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.add_tags") as mock_add,
            patch("memebase.app.remove_tags") as mock_remove,
        ):
            resp = client.put(
                "/api/memes/bulk/tags",
                json={"uuids": ["u1", "u2"], "add": ["funny"]},
            )
        assert resp.status_code == 200
        assert resp.get_json() == {"ok": True}
        assert mock_add.call_count == 2
        mock_remove.assert_not_called()

    def test_remove_tags(self, client):
        with (
            patch("memebase.app.get_db"),
            patch("memebase.app.add_tags") as mock_add,
            patch("memebase.app.remove_tags") as mock_remove,
        ):
            resp = client.put(
                "/api/memes/bulk/tags",
                json={"uuids": ["u1"], "remove": ["old-tag"]},
            )
        assert resp.status_code == 200
        assert mock_remove.call_count == 1
        mock_add.assert_not_called()
