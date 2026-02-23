import logging
from pathlib import Path

from flask import (
    Flask,
    render_template,
    send_from_directory,
    request,
    jsonify,
    make_response,
)
from memebase.common import (
    ROOT_DIR,
    MEMES_DIR,
    ALLOWED_EXTENSIONS,
    CONTENT_TYPE_TO_EXT,
    USER_AGENT,
)
from memebase.db import (
    get_db,
    get_meme,
    get_meme_for_serving,
    update_favorite,
    update_description,
    update_filename,
    set_tags,
    add_tags,
    remove_tags,
    get_all_tags,
    increment_copy_count,
    delete_meme_row,
    query_memes,
)
from memebase.service import resolve_unique_path, register_meme, get_meme_file_path
from memebase.config import load_config
from memebase.util import sanitize_filename

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

try:
    with open(ROOT_DIR / "pyproject.toml", "rb") as _f:
        VERSION = tomllib.load(_f)["project"]["version"]
except Exception:
    VERSION = ""

app = Flask(
    __name__,
    template_folder=str(ROOT_DIR / "templates"),
    static_folder=str(ROOT_DIR / "static"),
)


@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON for any uncaught exception on API routes."""
    if request.path.startswith("/api/"):
        log.exception("Unhandled error on %s %s", request.method, request.path)
        status = getattr(e, "code", 500)
        return jsonify({"error": str(e) or "Internal server error"}), status
    raise e


@app.route("/")
def index():
    cfg = load_config()
    return render_template(
        "index.html",
        version=VERSION,
        grid_thumbnail_size=cfg["grid"]["thumbnail_size"],
        grid_page_size=cfg["grid"]["page_size"],
        ai_parallel=cfg["ai"]["parallel"],
        ai_enabled=cfg["ai"]["enabled"],
    )


@app.route("/memes/<uuid>/<path:filename>")
def serve_meme(uuid, filename):
    with get_db() as conn:
        result = get_meme_for_serving(conn, uuid)
    if not result:
        return "Not found", 404
    real_filename, sha256 = result
    etag = f'"{sha256}"'
    if request.headers.get("If-None-Match") == etag:
        return "", 304
    resp = make_response(send_from_directory(MEMES_DIR, real_filename))
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = "max-age=31536000"
    return resp


@app.route("/api/memes")
def list_memes():
    cfg = load_config()
    page_size = cfg["grid"]["page_size"]

    q = request.args.get("q", "").strip()
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        page = 1
    ext_filter = request.args.get("ext", "").strip().lower() or None
    tag_filters = [t.strip().lower() for t in request.args.getlist("tag") if t.strip()]
    fav_filter = request.args.get("fav", "").strip() == "1"
    sort = request.args.get("sort", "")

    with get_db() as conn:
        result = query_memes(
            conn,
            q=q,
            page=page,
            page_size=page_size,
            ext_filter=ext_filter,
            tag_filters=tag_filters,
            fav_filter=fav_filter,
            sort=sort,
        )

    return jsonify(
        {
            "memes": result["memes"],
            "total": result["total"],
            "page": page,
            "page_size": page_size,
            "filters": result["filters"],
        }
    )


@app.route("/api/memes", methods=["POST"])
def upload_memes():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "No files provided"}), 400

    results = []
    with get_db() as conn:
        for f in files:
            ext = Path(f.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue

            basename = sanitize_filename(f.filename)
            dest, basename = resolve_unique_path(MEMES_DIR, basename)
            f.save(dest)

            meme, is_dup = register_meme(conn, dest)
            if is_dup:
                meme["duplicate"] = True
                log.info("Upload skipped (duplicate): %s -> %s", basename, meme["uuid"])
            else:
                log.info("Uploaded: %s (%s, %d bytes)", basename, meme["uuid"], meme["size"])
            results.append(meme)

    return jsonify(results), 201


@app.route("/api/memes/url", methods=["POST"])
def upload_from_url():
    import urllib.request
    import urllib.parse

    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return jsonify({"error": "Only http and https URLs are supported"}), 400

    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as resp:
            # Try Content-Disposition for filename
            cd = resp.headers.get("Content-Disposition", "")
            filename = None
            if "filename=" in cd:
                filename = cd.split("filename=")[-1].strip().strip('"').strip("'")

            if not filename:
                path_part = urllib.parse.urlparse(url).path
                filename = Path(path_part).name or "download"

            # Ensure it has an allowed extension
            fp = Path(filename)
            ext = fp.suffix.lower()
            if not ext:
                ct = resp.headers.get("Content-Type", "")
                ext = CONTENT_TYPE_TO_EXT.get(ct.split(";")[0].strip(), "")
                filename += ext

            if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
                return jsonify({"error": f"Unsupported file type: {ext or 'unknown'}"}), 400

            content = resp.read()
    except Exception as e:
        return jsonify({"error": f"Failed to download: {e}"}), 400

    basename = sanitize_filename(filename)
    dest, basename = resolve_unique_path(MEMES_DIR, basename)

    with open(dest, "wb") as f:
        f.write(content)

    with get_db() as conn:
        meme, is_dup = register_meme(conn, dest)
        if is_dup:
            log.info("URL upload skipped (duplicate): %s -> %s", url, meme["uuid"])
            return jsonify(meme), 200
        log.info(
            "Uploaded from URL: %s -> %s (%s, %d bytes)", url, basename, meme["uuid"], meme["size"]
        )
        return jsonify(meme), 201


@app.route("/api/memes/<uuid>", methods=["PUT"])
def update_meme_route(uuid):
    with get_db() as conn:
        filename, _, reason = get_meme_file_path(conn, uuid, MEMES_DIR)
        if reason == "not_in_db":
            return jsonify({"error": "Not found"}), 404

        data = request.get_json()

        # Update favorite
        favorite = data.get("favorite")
        if favorite is not None:
            update_favorite(conn, uuid, favorite)
            log.info("Favorite %s: %s", "set" if favorite else "unset", uuid)

        # Update description
        description = data.get("description")
        if description is not None:
            update_description(conn, uuid, description)
            log.info("Description updated: %s", uuid)

        # Rename (new_name is just the stem, extension stays)
        new_name_stem = data.get("new_name")
        if new_name_stem is not None:
            orig = Path(filename)
            new_filename = sanitize_filename(new_name_stem + orig.suffix)
            new_stem = Path(new_filename).stem

            if new_stem and new_stem != orig.stem:
                new_path = MEMES_DIR / new_filename
                if new_path.exists():
                    return jsonify({"error": "A file with that name already exists"}), 409

                old_path = MEMES_DIR / filename
                old_path.rename(new_path)
                update_filename(conn, uuid, new_filename)
                log.info("Renamed: %s -> %s (%s)", filename, new_filename, uuid)

        # Update tags
        tags = data.get("tags")
        if tags is not None:
            set_tags(conn, uuid, tags)
            log.info("Tags updated: %s -> %s", uuid, tags)

        result = get_meme(conn, uuid)
    return jsonify(result)


@app.route("/api/tags")
def list_tags():
    with get_db() as conn:
        tags = get_all_tags(conn)
    return jsonify(tags)


@app.route("/api/memes/<uuid>/auto", methods=["POST"])
def auto_describe(uuid):
    from memebase.ai import analyze_meme

    with get_db() as conn:
        filename, path, reason = get_meme_file_path(conn, uuid, MEMES_DIR)
        if reason == "not_in_db":
            return jsonify({"error": "Not found"}), 404
        if reason == "not_on_disk":
            return jsonify({"error": "File not found on disk"}), 404

        tags = get_all_tags(conn)

    log.info("Auto-detect started: %s (%s)", filename, uuid)
    try:
        result = analyze_meme(path, tags)
    except Exception as e:
        log.error("Auto-detect failed: %s (%s): %s", filename, uuid, e)
        return jsonify({"error": str(e)}), 500

    log.info("Auto-detect completed: %s (%s) -> %s", filename, uuid, result.get("name", "?"))
    return jsonify(result)


@app.route("/api/memes/bulk/auto", methods=["POST"])
def bulk_auto():
    from memebase.ai import analyze_meme

    data = request.get_json()
    uuids = data.get("uuids", [])
    fields = data.get("fields", ["name", "description", "tags"])
    if not uuids:
        return jsonify({"error": "No uuids provided"}), 400

    log.info("Bulk auto-detect started: %d memes, fields=%s", len(uuids), fields)
    with get_db() as conn:
        all_tags = get_all_tags(conn)
        results = {}
        for u in uuids:
            filename, path, reason = get_meme_file_path(conn, u, MEMES_DIR)
            if reason:
                continue

            try:
                suggestion = analyze_meme(path, all_tags)
            except Exception as e:
                log.error("Bulk auto-detect failed: %s (%s): %s", filename, u, e)
                results[u] = {"error": str(e)}
                continue

            # Apply requested fields
            if "name" in fields and suggestion.get("name"):
                orig_ext = Path(filename).suffix
                new_filename = sanitize_filename(suggestion["name"].strip() + orig_ext)
                new_path = MEMES_DIR / new_filename
                if not new_path.exists() or new_filename == filename:
                    old_path = MEMES_DIR / filename
                    if new_filename != filename:
                        old_path.rename(new_path)
                    update_filename(conn, u, new_filename)

            if "description" in fields and suggestion.get("description"):
                update_description(conn, u, suggestion["description"])

            if "tags" in fields and suggestion.get("tags"):
                add_tags(conn, u, suggestion["tags"])

            results[u] = {"ok": True}
            log.info("Bulk auto-detect completed: %s (%s)", filename, u)

    log.info(
        "Bulk auto-detect finished: %d/%d succeeded",
        sum(1 for r in results.values() if r.get("ok")),
        len(uuids),
    )
    return jsonify(results)


@app.route("/api/memes/bulk/tags", methods=["PUT"])
def bulk_update_tags():
    data = request.get_json()
    uuids = data.get("uuids", [])
    tags_to_add = data.get("add", [])
    tags_to_remove = data.get("remove", [])
    if not uuids:
        return jsonify({"error": "No uuids provided"}), 400

    log.info(
        "Bulk tags: %d memes, add=%s, remove=%s",
        len(uuids),
        tags_to_add,
        tags_to_remove,
    )
    with get_db() as conn:
        for u in uuids:
            if tags_to_add:
                add_tags(conn, u, tags_to_add)
            if tags_to_remove:
                remove_tags(conn, u, tags_to_remove)
    return jsonify({"ok": True})


@app.route("/api/memes/<uuid>/copy", methods=["POST"])
def increment_copy(uuid):
    with get_db() as conn:
        new_count = increment_copy_count(conn, uuid)
        if new_count is None:
            return jsonify({"error": "Not found"}), 404
    return jsonify({"copy_count": new_count})


@app.route("/api/memes/<uuid>", methods=["DELETE"])
def delete_meme(uuid):
    with get_db() as conn:
        filename = delete_meme_row(conn, uuid)
        if not filename:
            return jsonify({"error": "Not found"}), 404
        path = MEMES_DIR / filename
        if path.exists():
            path.unlink()
    log.info("Deleted: %s (%s)", filename, uuid)
    return "", 204
