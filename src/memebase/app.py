import logging
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
)

from memebase.ai import analyze_meme
from memebase.common import ALLOWED_EXTENSIONS, CACHE_MAX_AGE, MEMES_DIR, ROOT_DIR
from memebase.config import load_config, load_version
from memebase.db import (
    add_tags,
    delete_meme_row,
    get_all_tags,
    get_db,
    get_meme,
    get_meme_for_serving,
    init_app,
    query_memes,
    remove_tags,
    set_tags,
    update_description,
    update_favorite,
    update_filename,
)
from memebase.schemas import MemeError
from memebase.service import (
    apply_ai_suggestions,
    download_from_url,
    get_meme_file_path,
    register_meme,
    resolve_unique_path,
)
from memebase.thumbnails import delete_thumbnails, get_or_create_thumbnail
from memebase.util import sanitize_filename

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

VERSION = load_version()

app = Flask(
    __name__,
    template_folder=str(ROOT_DIR / "templates"),
    static_folder=str(ROOT_DIR / "static"),
)
_server_cfg = load_config()["server"]
if _server_cfg["max_upload_size"]:
    app.config["MAX_CONTENT_LENGTH"] = _server_cfg["max_upload_size"] * 1024 * 1024
init_app(app)


@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON for any uncaught exception on API routes."""
    if request.path.startswith("/api/"):
        status = getattr(e, "code", 500)
        if status >= 500:
            log.exception("unhandled error: method=%s path=%s", request.method, request.path)
        return jsonify({"error": str(e) or "Internal server error"}), status
    raise e


@app.route("/")
def index():
    cfg = load_config()
    return render_template(
        "index.html",
        version=VERSION,
        grid_layout=cfg["grid"]["layout"],
        grid_thumbnail_size=cfg["grid"]["thumbnail_size"],
        grid_per_page=cfg["grid"]["per_page"],
        ai_parallel=cfg["ai"]["parallel"],
        ai_enabled=cfg["ai"]["enabled"],
        thumbnails_enabled=cfg["thumbnails"]["enabled"],
        thumbnails_skip_types=cfg["thumbnails"]["skip_types"],
        thumbnails_format=cfg["thumbnails"]["format"],
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
    resp.headers["Cache-Control"] = f"max-age={CACHE_MAX_AGE}"
    return resp


@app.route("/thumbnails/<uuid>.<ext>")
def serve_thumbnail(uuid, ext):
    with get_db() as conn:
        result = get_meme_for_serving(conn, uuid)
    if not result:
        return "Not found", 404
    real_filename, sha256 = result

    source_path = MEMES_DIR / real_filename
    thumb_path = get_or_create_thumbnail(uuid, source_path)

    if thumb_path and thumb_path.exists():
        etag = f'"{sha256}-thumb"'
        if request.headers.get("If-None-Match") == etag:
            return "", 304
        resp = make_response(send_from_directory(thumb_path.parent, thumb_path.name))
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = f"max-age={CACHE_MAX_AGE}"
        return resp

    # Fallback: serve original file
    etag = f'"{sha256}"'
    if request.headers.get("If-None-Match") == etag:
        return "", 304
    resp = make_response(send_from_directory(MEMES_DIR, real_filename))
    resp.headers["ETag"] = etag
    resp.headers["Cache-Control"] = f"max-age={CACHE_MAX_AGE}"
    return resp


@app.route("/api/memes")
def list_memes():
    cfg = load_config()
    try:
        per_page = int(request.args.get("per_page", cfg["grid"]["per_page"]))
    except (ValueError, TypeError):
        per_page = 50
    per_page = max(1, per_page)

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
            page_size=per_page,
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
            "per_page": per_page,
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
                log.info("upload skipped (duplicate): filename=%s uuid=%s", basename, meme["uuid"])
            else:
                log.info(
                    "upload: filename=%s uuid=%s size=%d", basename, meme["uuid"], meme["size"]
                )
            results.append(meme)

    return jsonify(results), 201


@app.route("/api/memes/url", methods=["POST"])
def upload_from_url():
    data = request.get_json()
    url = (data or {}).get("url", "").strip()
    if not url:
        return jsonify({"error": "No URL provided"}), 400

    try:
        basename, content = download_from_url(url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    dest, basename = resolve_unique_path(MEMES_DIR, basename)
    with open(dest, "wb") as f:
        f.write(content)

    with get_db() as conn:
        meme, is_dup = register_meme(conn, dest)
        if is_dup:
            log.info("url upload skipped (duplicate): url=%s uuid=%s", url, meme["uuid"])
            return jsonify(meme), 200
        log.info(
            "url upload: url=%s filename=%s uuid=%s size=%d",
            url,
            basename,
            meme["uuid"],
            meme["size"],
        )
        return jsonify(meme), 201


@app.route("/api/memes/<uuid>", methods=["PUT"])
def update_meme_route(uuid):
    with get_db() as conn:
        filename, _, reason = get_meme_file_path(conn, uuid, MEMES_DIR)
        if reason == MemeError.NOT_IN_DB:
            return jsonify({"error": "Not found"}), 404

        data = request.get_json()

        # Update favorite
        favorite = data.get("favorite")
        if favorite is not None:
            update_favorite(conn, uuid, favorite)
            log.info("favorite updated: uuid=%s filename=%s favorite=%s", uuid, filename, favorite)

        # Update description
        description = data.get("description")
        if description is not None:
            update_description(conn, uuid, description)
            log.info(
                "description updated: uuid=%s filename=%s length=%d",
                uuid,
                filename,
                len(description),
            )

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
                log.info("rename: uuid=%s old=%s new=%s", uuid, filename, new_filename)

        # Update tags
        tags = data.get("tags")
        if tags is not None:
            set_tags(conn, uuid, tags)
            log.info("tags updated: uuid=%s filename=%s tags=%s", uuid, filename, tags)

        result = get_meme(conn, uuid)
    return jsonify(result)


@app.route("/api/tags")
def list_tags():
    with get_db() as conn:
        tags = get_all_tags(conn)
    return jsonify(tags)


@app.route("/api/memes/<uuid>/auto", methods=["POST"])
def auto_describe(uuid):
    with get_db() as conn:
        filename, path, reason = get_meme_file_path(conn, uuid, MEMES_DIR)
        if reason == MemeError.NOT_IN_DB:
            return jsonify({"error": "Not found"}), 404
        if reason == MemeError.NOT_ON_DISK:
            return jsonify({"error": "File not found on disk"}), 404

        tags = get_all_tags(conn)

    cfg = load_config()["ai"]
    log.info("auto-detect started: uuid=%s filename=%s", uuid, filename)
    try:
        result = analyze_meme(path, tags, model=cfg["model"], prompt_template=cfg["prompt"])
    except Exception as e:
        log.exception("auto-detect failed: uuid=%s filename=%s", uuid, filename)
        return jsonify({"error": str(e)}), 500

    log.info(
        "auto-detect completed: uuid=%s filename=%s suggested_name=%s",
        uuid,
        filename,
        result.get("name", "?"),
    )
    return jsonify(result)


@app.route("/api/memes/bulk/auto", methods=["POST"])
def bulk_auto():
    data = request.get_json()
    uuids = data.get("uuids", [])
    fields = data.get("fields", ["name", "description", "tags"])
    if not uuids:
        return jsonify({"error": "No uuids provided"}), 400

    cfg = load_config()["ai"]
    log.info("bulk auto-detect started: count=%d fields=%s", len(uuids), fields)
    with get_db() as conn:
        all_tags = get_all_tags(conn)
        results = {}
        for u in uuids:
            filename, path, reason = get_meme_file_path(conn, u, MEMES_DIR)
            if reason:
                continue

            try:
                suggestion = analyze_meme(
                    path, all_tags, model=cfg["model"], prompt_template=cfg["prompt"]
                )
            except Exception as e:
                log.error("bulk auto-detect failed: uuid=%s filename=%s error=%s", u, filename, e)
                results[u] = {"error": str(e)}
                continue

            apply_ai_suggestions(conn, u, filename, suggestion, fields, MEMES_DIR)

            results[u] = {"ok": True}
            log.debug("bulk auto-detect completed: uuid=%s filename=%s", u, filename)

    log.info(
        "bulk auto-detect finished: succeeded=%d total=%d",
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
        "bulk tags updated: count=%d add=%s remove=%s",
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


@app.route("/api/memes/<uuid>", methods=["DELETE"])
def delete_meme(uuid):
    with get_db() as conn:
        filename = delete_meme_row(conn, uuid)
        if not filename:
            return jsonify({"error": "Not found"}), 404
        path = MEMES_DIR / filename
        if path.exists():
            path.unlink()
        delete_thumbnails(uuid)
    log.info("delete: uuid=%s filename=%s", uuid, filename)
    return "", 204
