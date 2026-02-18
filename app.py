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
        "X-Emby-Authorization": (
            'MediaBrowser Client="PoopRequests", '
            'Device="Web", DeviceId="pooprequests-web", Version="1.1.0"'
        ),
    }

    try:
        response = requests.post(
            f"{JELLYFIN_URL}/Users/AuthenticateByName",
            json={"Username": username, "Pw": password},
            headers=headers,
            timeout=12,
        )
    except requests.RequestException as exc:
        return api_error("Unable to reach Jellyfin.", 502, str(exc))

    if response.status_code != 200:
        return api_error("Invalid login", 401)

    data = response.json()
    return jsonify(
        {
            "token": data.get("AccessToken"),
            "user": data.get("User", {}).get("Name", username),
            "userId": data.get("User", {}).get("Id", ""),
        }
    )


@app.get("/api/users")
def users() -> Any:
    token = request.headers.get("X-Jellyfin-Token", "")
    if not token:
        return api_error("Missing token", 401)

    try:
        response = requests.get(
            f"{JELLYFIN_URL}/Users",
            headers={"X-Emby-Token": token},
            timeout=12,
        )
    except requests.RequestException as exc:
        return api_error("Unable to fetch users", 502, str(exc))

    if response.status_code != 200:
        return api_error("Unable to fetch users", 400)

    users_payload = [
        {
            "id": user.get("Id"),
            "name": user.get("Name"),
            "isAdmin": user.get("Policy", {}).get("IsAdministrator", False),
        }
        for user in response.json()
    ]
    return jsonify(users_payload)


@app.get("/api/search")
def search_media() -> Any:
    query = request.args.get("q", "").strip()
    media_type = request.args.get("type", "movies")

    if len(query) < 2:
        return jsonify([])

    if media_type in {"movies", "tv"}:
        return jsonify(search_tmdb(query, media_type))
    if media_type == "books":
        return jsonify(search_books(query))
    if media_type == "audiobooks":
        return jsonify(search_audiobooks(query))

    return jsonify([])


def search_tmdb(query: str, media_type: str) -> list[dict[str, Any]]:
    if not TMDB_API_KEY:
        return []

    endpoint = "movie" if media_type == "movies" else "tv"

    try:
        response = requests.get(
            f"https://api.themoviedb.org/3/search/{endpoint}",
            params={"api_key": TMDB_API_KEY, "query": query, "include_adult": "false"},
            timeout=12,
        )
    except requests.RequestException:
        return []

    if response.status_code != 200:
        return []

    items = []
    for row in response.json().get("results", [])[:20]:
        items.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or row.get("name"),
                "overview": row.get("overview", "No description available."),
                "year": (row.get("release_date") or row.get("first_air_date") or "")[:4],
                "poster": (
                    f"https://image.tmdb.org/t/p/w342{row['poster_path']}"
                    if row.get("poster_path")
                    else ""
                ),
                "provider": "tmdb",
                "mediaType": media_type,
            }
        )
    return items


def search_books(query: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(OPENLIBRARY_ENDPOINT, params={"q": query, "limit": 20}, timeout=12)
    except requests.RequestException:
        return []

    if response.status_code != 200:
        return []

    items = []
    for row in response.json().get("docs", [])[:20]:
        cover_id = row.get("cover_i")
        items.append(
            {
                "id": row.get("key", "").replace("/works/", ""),
                "title": row.get("title", "Unknown title"),
                "overview": ", ".join(row.get("author_name", [])[:2]) or "Unknown author",
                "year": str(row.get("first_publish_year", "")),
                "poster": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else "",
                "provider": "openlibrary",
                "mediaType": "books",
            }
        )
    return items


def search_audiobooks(query: str) -> list[dict[str, Any]]:
    try:
        response = requests.get(
            GOOGLE_BOOKS_ENDPOINT,
            params={"q": f"{query} audiobook", "maxResults": 20},
            timeout=12,
        )
    except requests.RequestException:
        return []

    if response.status_code != 200:
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
    if not LISTENARR_URL or not LISTENARR_API_KEY:
        return api_error("Listenarr is not configured", 400)

    try:
        response = requests.post(
            f"{LISTENARR_URL}/api/v1/wanted",
            json={"foreignId": item.get("id"), "title": item.get("title")},
            headers={"X-Api-Key": LISTENARR_API_KEY},
            timeout=12,
        )
    except requests.RequestException as exc:
        return api_error("Listenarr request failed", 502, str(exc))

    if response.status_code not in {200, 201, 202}:
        return api_error("Listenarr request failed", 400, response.text)

    return jsonify({"ok": True, "target": "listenarr"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
