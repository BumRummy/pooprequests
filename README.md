# pooprequests

A polished, container-ready Flask web app that authenticates with Jellyfin credentials and provides one-click media requests routed to Jellyseerr, LazyLibrarian, and Listenarr.

## Features

- Login popup (modal) on page load using Jellyfin username/password
- Large centered **Requests** heading and improved, modern glass-style UI
- Media picker: Movies, TV, Books, Audiobooks
- Live search cards with posters, year, and basic details
- One-click request routing:
  - Movies / TV -> Jellyseerr
  - Books -> LazyLibrarian
  - Audiobooks -> Listenarr
- Improved backend error handling for upstream/service failures

## Configuration

Set these environment variables when running the container:

- `JELLYFIN_URL` (default: `http://localhost:8096`)
- `TMDB_API_KEY` (required for movie/TV search)
- `JELLYSEERR_URL`, `JELLYSEERR_API_KEY`
- `LAZYLIBRARIAN_URL`, `LAZYLIBRARIAN_API_KEY`
- `LISTENARR_URL`, `LISTENARR_API_KEY`
- `LOG_LEVEL` (optional, default: `INFO`)
- `LOG_TO_FILE` (optional, default: `true`)
- `LOG_DIR` (optional, default: `/config`)
- `LOG_FILE_NAME` (optional, default: `pooprequests.log`)
- `PUID`, `PGID` (optional, default: `1000`) used to set `/config` ownership at startup when running as root

## Run with Docker

```bash
docker build -t pooprequests:latest .
docker run --rm -p 8080:8080 \
  -e JELLYFIN_URL="http://jellyfin:8096" \
  -e TMDB_API_KEY="your_tmdb_key" \
  -e JELLYSEERR_URL="http://jellyseerr:5055" \
  -e JELLYSEERR_API_KEY="your_jellyseerr_key" \
  -e LAZYLIBRARIAN_URL="http://lazylibrarian:5299" \
  -e LAZYLIBRARIAN_API_KEY="your_lazylibrarian_key" \
  -e LISTENARR_URL="http://listenarr:8787" \
  -e LISTENARR_API_KEY="your_listenarr_key" \
  pooprequests:latest
```

Then open `http://localhost:8080`.

## Run with Docker Compose (yaml)

```bash
cp .env.example .env
# edit .env with your real API keys

docker compose pull
docker compose up -d
```

This uses `docker-compose.yml` with the prebuilt image `nightnightnight/pooprequests:latest` and attaches the app to a `media-stack` network so it can reach Jellyfin and companion services by container name.

Logs are emitted to container stdout and (by default) also written to `./config/pooprequests.log` via a bind mount to `/config`.


## Build helper CLI

A small helper CLI is included at `scripts/pooprequests_cli.py` to pull/update a repo and build the image in one command.

```bash
python scripts/pooprequests_cli.py \
  --repo https://github.com/<your-user>/pooprequests.git \
  --branch main \
  --checkout-dir ~/apps/pooprequests-src \
  --image-tag pooprequests:latest
```

What it does:
- checks for `git` and `docker`
- clones the repo (or fetches + pulls if already cloned)
- builds the Docker image with your chosen tag
- prints whether branch changes were pushed to GitHub

By default it does **not** push git changes. To upload your branch:

```bash
python scripts/pooprequests_cli.py \
  --repo https://github.com/<your-user>/pooprequests.git \
  --branch main \
  --checkout-dir ~/apps/pooprequests-src \
  --image-tag pooprequests:latest \
  --push
```

Run `python scripts/pooprequests_cli.py --help` for all options.


## CasaOS / ZimaOS notes

If the app does not launch in CasaOS, verify:

- Environment entries are `KEY=value` pairs. Do **not** use invalid keys like `/config=/config`.
- Do **not** set `command: []` in CasaOS compose for this app. That overrides the image `CMD` and causes an immediate exit/restart loop.
- `JELLYSEERR_URL`, `LAZYLIBRARIAN_URL`, and `LISTENARR_URL` include full URLs with `http://` and valid ports.
- Service port mapping and `x-casaos.port_map` both point to the published host port (for example `8675`).
- `/config` is bind-mounted to a writable host path and `PUID`/`PGID` match your host user/group so `pooprequests.log` can be created.

Example env entries:

```yaml
# Leave command unset so image default CMD runs app.py
# command: []  # <-- do not set this

environment:
  - JELLYFIN_URL=http://jellyfin:8096
  - JELLYSEERR_URL=http://jellyseerr:8097
  - LAZYLIBRARIAN_URL=http://lazylibrarian:5299
  - LISTENARR_URL=http://listenarr:4545
  - LOG_TO_FILE=true
  - LOG_DIR=/config
  - LOG_FILE_NAME=pooprequests.log
  - PUID=1000
  - PGID=1000
```
