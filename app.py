import os
from typing import Any

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

load_dotenv()

app = Flask(__name__)

JELLYFIN_URL = os.getenv("JELLYFIN_URL", "http://localhost:8096").rstrip("/")
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
GOOGLE_BOOKS_ENDPOINT = "https://www.googleapis.com/books/v1/volumes"
OPENLIBRARY_ENDPOINT = "https://openlibrary.org/search.json"

JELLYSEERR_URL = os.getenv("JELLYSEERR_URL", "").rstrip("/")
JELLYSEERR_API_KEY = os.getenv("JELLYSEERR_API_KEY", "")
LAZYLIBRARIAN_URL = os.getenv("LAZYLIBRARIAN_URL", "").rstrip("/")
LAZYLIBRARIAN_API_KEY = os.getenv("LAZYLIBRARIAN_API_KEY", "")
LISTENARR_URL = os.getenv("LISTENARR_URL", "").rstrip("/")
LISTENARR_API_KEY = os.getenv("LISTENARR_API_KEY", "")
RADARR_URL = os.getenv("RADARR_URL", "").rstrip("/")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
RADARR_QUALITY_PROFILE_ID = os.getenv("RADARR_QUALITY_PROFILE_ID", "")
RADARR_ROOT_FOLDER_PATH = os.getenv("RADARR_ROOT_FOLDER_PATH", "")
SONARR_URL = os.getenv("SONARR_URL", "").rstrip("/")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")
SONARR_QUALITY_PROFILE_ID = os.getenv("SONARR_QUALITY_PROFILE_ID", "")
SONARR_ROOT_FOLDER_PATH = os.getenv("SONARR_ROOT_FOLDER_PATH", "")
SONARR_LANGUAGE_PROFILE_ID = os.getenv("SONARR_LANGUAGE_PROFILE_ID", "")


def api_error(message: str, status: int = 400, details: str | None = None) -> tuple[Any, int]:
    payload = {"error": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.post("/api/login")
def login() -> Any:
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "").strip()
    password = payload.get("password", "")

    if not username or not password:
        return api_error("Username and password are required.", 400)

    headers = {
        "Content-Type": "application/json",
@@ -199,87 +208,220 @@ def search_audiobooks(query: str) -> list[dict[str, Any]]:
        return []

    items = []
    for row in response.json().get("items", [])[:20]:
        info = row.get("volumeInfo", {})
        items.append(
            {
                "id": row.get("id"),
                "title": info.get("title", "Unknown title"),
                "overview": info.get("description", "No description available."),
                "year": str(info.get("publishedDate", ""))[:4],
                "poster": info.get("imageLinks", {}).get("thumbnail", ""),
                "provider": "googlebooks",
                "mediaType": "audiobooks",
            }
        )

    return items


@app.post("/api/request")
def request_item() -> Any:
    payload = request.get_json(silent=True) or {}
    media_type = payload.get("mediaType")

    if media_type in {"movies", "tv"}:
        return send_to_jellyseerr(payload)
    if media_type == "movies":
        if JELLYSEERR_URL and JELLYSEERR_API_KEY:
            return send_to_jellyseerr(payload)
        return send_to_radarr(payload)
    if media_type == "tv":
        if JELLYSEERR_URL and JELLYSEERR_API_KEY:
            return send_to_jellyseerr(payload)
        return send_to_sonarr(payload)
    if media_type == "books":
        return send_to_lazylibrarian(payload)
    if media_type == "audiobooks":
        return send_to_listenarr(payload)

    return api_error("Unsupported media type", 400)


def send_to_jellyseerr(item: dict[str, Any]) -> Any:
    if not JELLYSEERR_URL or not JELLYSEERR_API_KEY:
        return api_error("Jellyseerr is not configured", 400)

    media_type = "movie" if item.get("mediaType") == "movies" else "tv"
    payload = {
        "mediaType": media_type,
        "mediaId": item.get("id"),
        "seasons": "all" if media_type == "tv" else None,
    }

    try:
        response = requests.post(
            f"{JELLYSEERR_URL}/api/v1/request",
            json=payload,
            headers={"X-Api-Key": JELLYSEERR_API_KEY},
            timeout=12,
        )
    except requests.RequestException as exc:
        return api_error("Jellyseerr request failed", 502, str(exc))

    if response.status_code not in {200, 201}:
        return api_error("Jellyseerr request failed", 400, response.text)

    return jsonify({"ok": True, "target": "jellyseerr"})


def _arr_base_url(url: str) -> str:
    cleaned = url.rstrip("/")
    if cleaned.endswith("/api/v3"):
        return cleaned[: -len("/api/v3")]
    if cleaned.endswith("/api"):
        return cleaned[: -len("/api")]
    return cleaned


def _arr_headers(api_key: str) -> dict[str, str]:
    return {"X-Api-Key": api_key, "Content-Type": "application/json"}


def _int_or_none(raw: str) -> int | None:
    raw = str(raw or "").strip()
    return int(raw) if raw.isdigit() else None


def send_to_radarr(item: dict[str, Any]) -> Any:
    if not RADARR_URL or not RADARR_API_KEY:
        return api_error("Radarr is not configured", 400)

    base_url = _arr_base_url(RADARR_URL)
    headers = _arr_headers(RADARR_API_KEY)

    quality_profile_id = _int_or_none(RADARR_QUALITY_PROFILE_ID)
    root_folder_path = RADARR_ROOT_FOLDER_PATH.strip()

    try:
        if quality_profile_id is None:
            qp_response = requests.get(f"{base_url}/api/v3/qualityprofile", headers=headers, timeout=12)
            if qp_response.status_code == 200 and qp_response.json():
                quality_profile_id = qp_response.json()[0].get("id")

        if not root_folder_path:
            folder_response = requests.get(f"{base_url}/api/v3/rootfolder", headers=headers, timeout=12)
            if folder_response.status_code == 200 and folder_response.json():
                root_folder_path = folder_response.json()[0].get("path", "")

        if quality_profile_id is None or not root_folder_path:
            return api_error(
                "Radarr request failed",
                400,
                "Could not determine Radarr quality profile or root folder. "
                "Set RADARR_QUALITY_PROFILE_ID and RADARR_ROOT_FOLDER_PATH.",
            )

        response = requests.post(
            f"{base_url}/api/v3/movie",
            json={
                "tmdbId": item.get("id"),
                "qualityProfileId": quality_profile_id,
                "rootFolderPath": root_folder_path,
                "title": item.get("title"),
                "monitored": True,
                "addOptions": {"searchForMovie": True},
            },
            headers=headers,
            timeout=12,
        )
    except requests.RequestException as exc:
        return api_error("Radarr request failed", 502, str(exc))

    if response.status_code not in {200, 201}:
        return api_error("Radarr request failed", 400, response.text)

    return jsonify({"ok": True, "target": "radarr"})


def send_to_sonarr(item: dict[str, Any]) -> Any:
    if not SONARR_URL or not SONARR_API_KEY:
        return api_error("Sonarr is not configured", 400)

    base_url = _arr_base_url(SONARR_URL)
    headers = _arr_headers(SONARR_API_KEY)

    quality_profile_id = _int_or_none(SONARR_QUALITY_PROFILE_ID)
    language_profile_id = _int_or_none(SONARR_LANGUAGE_PROFILE_ID)
    root_folder_path = SONARR_ROOT_FOLDER_PATH.strip()

    try:
        if quality_profile_id is None:
            qp_response = requests.get(f"{base_url}/api/v3/qualityprofile", headers=headers, timeout=12)
            if qp_response.status_code == 200 and qp_response.json():
                quality_profile_id = qp_response.json()[0].get("id")

        if language_profile_id is None:
            lp_response = requests.get(f"{base_url}/api/v3/languageprofile", headers=headers, timeout=12)
            if lp_response.status_code == 200 and lp_response.json():
                language_profile_id = lp_response.json()[0].get("id")

        if not root_folder_path:
            folder_response = requests.get(f"{base_url}/api/v3/rootfolder", headers=headers, timeout=12)
            if folder_response.status_code == 200 and folder_response.json():
                root_folder_path = folder_response.json()[0].get("path", "")

        if quality_profile_id is None or language_profile_id is None or not root_folder_path:
            return api_error(
                "Sonarr request failed",
                400,
                "Could not determine Sonarr profiles or root folder. "
                "Set SONARR_QUALITY_PROFILE_ID, SONARR_LANGUAGE_PROFILE_ID, and SONARR_ROOT_FOLDER_PATH.",
            )

        response = requests.post(
            f"{base_url}/api/v3/series",
            json={
                "tmdbId": item.get("id"),
                "qualityProfileId": quality_profile_id,
                "languageProfileId": language_profile_id,
                "rootFolderPath": root_folder_path,
                "title": item.get("title"),
                "monitored": True,
                "addOptions": {"searchForMissingEpisodes": True},
            },
            headers=headers,
            timeout=12,
        )
    except requests.RequestException as exc:
        return api_error("Sonarr request failed", 502, str(exc))

    if response.status_code not in {200, 201}:
        return api_error("Sonarr request failed", 400, response.text)

    return jsonify({"ok": True, "target": "sonarr"})


def send_to_lazylibrarian(item: dict[str, Any]) -> Any:
    if not LAZYLIBRARIAN_URL or not LAZYLIBRARIAN_API_KEY:
        return api_error("LazyLibrarian is not configured", 400)

    try:
        response = requests.get(
            f"{LAZYLIBRARIAN_URL}/api",
            params={
                "cmd": "addBook",
                "apikey": LAZYLIBRARIAN_API_KEY,
                "id": item.get("id"),
                "title": item.get("title"),
            },
            timeout=12,
        )
    except requests.RequestException as exc:
        return api_error("LazyLibrarian request failed", 502, str(exc))

    if response.status_code != 200:
        return api_error("LazyLibrarian request failed", 400, response.text)

    return jsonify({"ok": True, "target": "lazylibrarian"})


def send_to_listenarr(item: dict[str, Any]) -> Any:
