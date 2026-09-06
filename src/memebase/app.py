import re
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
)
from werkzeug.exceptions import NotFound

from memebase.ai import analyze_meme
from memebase.common import (
    ALLOWED_EXTENSIONS,
    CACHE_MAX_AGE,
    DEFAULT_THEME,
    MEMES_DIR,
    ROOT_DIR,
    THEMES_DIR,
)
from memebase.config import load_version
from memebase.db import (
    add_tags,
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
)
from memebase.log import get_logger
from memebase.schemas import MemeError
from memebase.scrape import scrape_url
from memebase.service import (
    apply_ai_suggestions,
    delete_meme,
    get_meme_file_path,
    register_meme,
    rename_meme,
    resolve_unique_path,
)
from memebase.thumbnails import get_or_create_thumbnail
from memebase.util import generate_placeholder_image, sanitize_filename

log = get_logger(__name__)

_THEME_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _safe_theme_name(name: str) -> str:
    if _THEME_RE.match(name):
        return name
    return DEFAULT_THEME


def _not_found_image():
    return Response(generate_placeholder_image(), status=404, content_type="image/png")


def create_app(config=None):
    VERSION = load_version()

    app = Flask(
        __name__,
        template_folder=str(ROOT_DIR / "templates"),
        static_folder=str(ROOT_DIR / "static"),
    )
    if config is not None:
        server_cfg = config.get("server", {})
        max_upload = server_cfg.get("max_upload_size")
        if max_upload:
            app.config["MAX_CONTENT_LENGTH"] = max_upload * 1024 * 1024
    init_app(app)

    BUILTIN_THEMES_DIR = Path(app.static_folder) / "css" / "themes"

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
        theme = request.args.get("theme", "").strip() or config["ui"]["theme"]
        theme = _safe_theme_name(theme)
        return render_template(
            "index.html",
            title=config["ui"]["title"],
            version=VERSION,
            theme=theme,
            grid_layout=config["grid"]["layout"],
            grid_thumbnail_size=config["grid"]["thumbnail_size"],
            grid_per_page=config["grid"]["per_page"],
            ai_parallel=config["ai"]["parallel"],
            ai_enabled=config["ai"]["enabled"],
            thumbnails_enabled=config["thumbnails"]["enabled"],
            thumbnails_skip_types=config["thumbnails"]["skip_types"],
            thumbnails_format=config["thumbnails"]["format"],
        )

    @app.route("/memes/<meme_id>/<path:filename>")
    def serve_meme(meme_id, filename):
        with get_db() as conn:
            result = get_meme_for_serving(conn, meme_id)
        if not result:
            return _not_found_image()
        real_filename, sha256 = result
        etag = f'"{sha256}"'
        if request.headers.get("If-None-Match") == etag:
            return "", 304
        try:
            resp = make_response(send_from_directory(MEMES_DIR, real_filename))
        except NotFound:
            return _not_found_image()
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = f"max-age={CACHE_MAX_AGE}"
        return resp

    @app.route("/thumbnails/<meme_id>.<ext>")
    def serve_thumbnail(meme_id, ext):
        with get_db() as conn:
            result = get_meme_for_serving(conn, meme_id)
        if not result:
            return _not_found_image()
        real_filename, sha256 = result

        source_path = MEMES_DIR / real_filename
        thumb_path = get_or_create_thumbnail(meme_id, source_path, config["thumbnails"])

        if thumb_path and thumb_path.exists():
            etag = f'"{sha256}-thumb"'
            if request.headers.get("If-None-Match") == etag:
                return "", 304
            try:
                resp = make_response(send_from_directory(thumb_path.parent, thumb_path.name))
            except NotFound:
                return _not_found_image()
            resp.headers["ETag"] = etag
            resp.headers["Cache-Control"] = f"max-age={CACHE_MAX_AGE}"
            return resp

        # Fallback: serve original file
        etag = f'"{sha256}"'
        if request.headers.get("If-None-Match") == etag:
            return "", 304
        try:
            resp = make_response(send_from_directory(MEMES_DIR, real_filename))
        except NotFound:
            return _not_found_image()
        resp.headers["ETag"] = etag
        resp.headers["Cache-Control"] = f"max-age={CACHE_MAX_AGE}"
        return resp

    @app.route("/themes/<name>.css")
    def serve_theme(name):
        name = _safe_theme_name(name)
        filename = f"{name}.css"
        # Custom theme in data/ takes priority
        if (THEMES_DIR / filename).is_file():
            return send_from_directory(THEMES_DIR, filename)
        # Fall back to built-in, then to midnight if the file doesn't exist
        if (BUILTIN_THEMES_DIR / filename).is_file():
            return send_from_directory(BUILTIN_THEMES_DIR, filename)
        return send_from_directory(BUILTIN_THEMES_DIR, f"{DEFAULT_THEME}.css")

    @app.route("/api/memes")
    def list_memes():
        try:
            per_page = int(request.args.get("per_page", config["grid"]["per_page"]))
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
                    log.info("upload skipped (duplicate): filename=%s id=%s", basename, meme["id"])
                else:
                    log.info(
                        "upload: filename=%s id=%s size=%d", basename, meme["id"], meme["size"]
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
            downloads = scrape_url(url, max_files=config["scrape"]["max_files"])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        results = []
        has_new = False
        with get_db() as conn:
            for basename, content, source in downloads:
                dest, basename = resolve_unique_path(MEMES_DIR, basename)
                with open(dest, "wb") as f:
                    f.write(content)

                meme, is_dup = register_meme(conn, dest, source=source)
                if is_dup:
                    meme["duplicate"] = True
                    log.info("url upload skipped (duplicate): url=%s id=%s", url, meme["id"])
                else:
                    has_new = True
                    log.info(
                        "url upload: url=%s filename=%s id=%s size=%d",
                        url,
                        basename,
                        meme["id"],
                        meme["size"],
                    )
                results.append(meme)

        return jsonify(results), 201 if has_new else 200

    @app.route("/api/memes/<meme_id>")
    def get_meme_route(meme_id):
        with get_db() as conn:
            meme = get_meme(conn, meme_id)
        if meme is None:
            return jsonify({"error": "Not found"}), 404
        return jsonify(meme)

    @app.route("/api/memes/<meme_id>", methods=["PUT"])
    def update_meme_route(meme_id):
        with get_db() as conn:
            filename, _, reason = get_meme_file_path(conn, meme_id, MEMES_DIR)
            if reason == MemeError.NOT_IN_DB:
                return jsonify({"error": "Not found"}), 404

            data = request.get_json()

            # Update favorite
            favorite = data.get("favorite")
            if favorite is not None:
                update_favorite(conn, meme_id, favorite)
                log.info(
                    "favorite updated: id=%s filename=%s favorite=%s", meme_id, filename, favorite
                )

            # Update description
            description = data.get("description")
            if description is not None:
                update_description(conn, meme_id, description)
                log.info(
                    "description updated: id=%s filename=%s length=%d",
                    meme_id,
                    filename,
                    len(description),
                )

            # Rename (new_name is just the stem, extension stays)
            new_name_stem = data.get("new_name")
            if new_name_stem is not None:
                try:
                    new_filename = rename_meme(conn, meme_id, filename, new_name_stem, MEMES_DIR)
                    log.info("rename: id=%s old=%s new=%s", meme_id, filename, new_filename)
                except FileExistsError:
                    return jsonify({"error": "A file with that name already exists"}), 409
                except ValueError:
                    pass

            # Update tags
            tags = data.get("tags")
            if tags is not None:
                set_tags(conn, meme_id, tags)
                log.info("tags updated: id=%s filename=%s tags=%s", meme_id, filename, tags)

            result = get_meme(conn, meme_id)
        return jsonify(result)

    @app.route("/api/tags")
    def list_tags():
        with get_db() as conn:
            tags = get_all_tags(conn)
        return jsonify(tags)

    @app.route("/api/memes/<meme_id>/auto", methods=["POST"])
    def auto_describe(meme_id):
        with get_db() as conn:
            filename, path, reason = get_meme_file_path(conn, meme_id, MEMES_DIR)
            if reason == MemeError.NOT_IN_DB:
                return jsonify({"error": "Not found"}), 404
            if reason == MemeError.NOT_ON_DISK:
                return jsonify({"error": "File not found on disk"}), 404

            tags = get_all_tags(conn)

        ai_cfg = config["ai"]
        log.info("auto-detect started: id=%s filename=%s", meme_id, filename)
        try:
            result = analyze_meme(
                path, tags, model=ai_cfg["model"], prompt_template=ai_cfg["prompt"]
            )
        except Exception as e:
            log.exception("auto-detect failed: id=%s filename=%s", meme_id, filename)
            return jsonify({"error": str(e)}), 500

        log.info(
            "auto-detect completed: id=%s filename=%s suggested_name=%s",
            meme_id,
            filename,
            result.get("name", "?"),
        )
        return jsonify(result)

    @app.route("/api/memes/bulk/auto", methods=["POST"])
    def bulk_auto():
        data = request.get_json()
        ids = data.get("ids", [])
        fields = data.get("fields", ["name", "description", "tags"])
        if not ids:
            return jsonify({"error": "No ids provided"}), 400

        ai_cfg = config["ai"]
        log.info("bulk auto-detect started: count=%d fields=%s", len(ids), fields)
        with get_db() as conn:
            all_tags = get_all_tags(conn)
            results = {}
            for meme_id in ids:
                filename, path, reason = get_meme_file_path(conn, meme_id, MEMES_DIR)
                if reason:
                    continue

                try:
                    suggestion = analyze_meme(
                        path, all_tags, model=ai_cfg["model"], prompt_template=ai_cfg["prompt"]
                    )
                except Exception as e:
                    log.error(
                        "bulk auto-detect failed: id=%s filename=%s error=%s",
                        meme_id,
                        filename,
                        e,
                    )
                    results[meme_id] = {"error": str(e)}
                    continue

                apply_ai_suggestions(conn, meme_id, filename, suggestion, fields, MEMES_DIR)

                results[meme_id] = {"ok": True}
                log.debug("bulk auto-detect completed: id=%s filename=%s", meme_id, filename)

        log.info(
            "bulk auto-detect finished: succeeded=%d total=%d",
            sum(1 for r in results.values() if r.get("ok")),
            len(ids),
        )
        return jsonify(results)

    @app.route("/api/memes/bulk/tags", methods=["PUT"])
    def bulk_update_tags():
        data = request.get_json()
        ids = data.get("ids", [])
        tags_to_add = data.get("add", [])
        tags_to_remove = data.get("remove", [])
        if not ids:
            return jsonify({"error": "No ids provided"}), 400

        log.info(
            "bulk tags updated: count=%d add=%s remove=%s",
            len(ids),
            tags_to_add,
            tags_to_remove,
        )
        with get_db() as conn:
            for meme_id in ids:
                if tags_to_add:
                    add_tags(conn, meme_id, tags_to_add)
                if tags_to_remove:
                    remove_tags(conn, meme_id, tags_to_remove)
        return jsonify({"ok": True})

    @app.route("/api/memes/<meme_id>", methods=["DELETE"])
    def delete_meme_route(meme_id):
        try:
            with get_db() as conn:
                filename = delete_meme(conn, meme_id, MEMES_DIR)
        except LookupError:
            return jsonify({"error": "Not found"}), 404
        log.info("delete: id=%s filename=%s", meme_id, filename)
        return "", 204

    return app
