"""Application constants."""

from uuid import UUID

# Default client ID for development when authentication is disabled
DEFAULT_CLIENT_ID = UUID("00000000-0000-0000-0000-000000000000")

# File size limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_IMPORT_ROWS = 100000

# Allowed file extensions
ALLOWED_FILE_EXTENSIONS = {".csv", ".json"}

# Content types
CONTENT_TYPE_CSV = "text/csv"
CONTENT_TYPE_JSON = "application/json"

# Allowed content types for presigned uploads
ALLOWED_UPLOAD_CONTENT_TYPES = {"text/csv", "application/json"}

# Export formats
EXPORT_FORMAT_CSV = "csv"
EXPORT_FORMAT_JSON = "json"

# Default values
DEFAULT_EXPORT_FORMAT = EXPORT_FORMAT_CSV
DEFAULT_EXPORT_LOCAL_PATH = "/tmp/exports"
DEFAULT_PRESIGNED_URL_EXPIRATION = 3600  # 1 hour in seconds

# Database pool defaults
DEFAULT_POOL_SIZE = 10
DEFAULT_MAX_OVERFLOW = 20
DEFAULT_POOL_RECYCLE = 3600  # 1 hour
DEFAULT_POOL_TIMEOUT = 30  # 30 seconds

# Export/Import batch sizes
EXPORT_BATCH_SIZE = 1000
IMPORT_BATCH_SIZE = 100

# Job statistics update throttle (seconds)
STATS_UPDATE_INTERVAL = 5

# Retry configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_MULTIPLIER = 1
RETRY_BACKOFF_MIN = 2  # seconds
RETRY_BACKOFF_MAX = 10  # seconds
