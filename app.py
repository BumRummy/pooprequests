# Jellyfin Configuration
JELLYFIN_URL=http://jellyfin:8096

# TMDB API Key (required for movie/TV search)
TMDB_API_KEY=your_tmdb_api_key_here

# Radarr Configuration
RADARR_URL=http://radarr:7878
RADARR_API_KEY=your_radarr_api_key
RADARR_SEARCH_ON_ADD=true
RADARR_ROOT_FOLDER=/movies  # Optional: override root folder
RADARR_QUALITY_PROFILE_ID=1  # Optional: override quality profile ID

# Sonarr Configuration
SONARR_URL=http://sonarr:8989
SONARR_API_KEY=your_sonarr_api_key
SONARR_SEARCH_ON_ADD=true
SONARR_ROOT_FOLDER=/tv  # Optional: override root folder
SONARR_QUALITY_PROFILE_ID=1  # Optional: override quality profile ID

# LazyLibrarian Configuration (optional)
LAZYLIBRARIAN_URL=http://lazylibrarian:5299
LAZYLIBRARIAN_API_KEY=your_lazylibrarian_api_key

# Listenarr Configuration (optional)
LISTENARR_URL=http://listenarr:8686
LISTENARR_API_KEY=your_listenarr_api_key

# Logging Configuration
LOG_LEVEL=INFO
LOG_TO_FILE=true
LOG_DIR=/config
LOG_FILE_NAME=pooprequests.log

# User/Group ID for file permissions (optional)
PUID=1000
PGID=1000
