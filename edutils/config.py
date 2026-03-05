"""
Configuration for edumundo-stats.

All values can be overridden via environment variables.
"""

import os

# Browser connection
CHROME_DEBUG_PORT: str = os.getenv("EDUMUNDO_DEBUG_PORT", "http://localhost:9222")

# Target URL
EDUMUNDO_URL: str = os.getenv(
    "EDUMUNDO_URL",
    "https://hva.myedumundo.com/tutor/course/3053/statistics",
)

# DOM selectors for the module and class dropdowns.
# These Bootstrap Vue IDs are auto-generated and may change after a page rebuild.
# Override via env var when the site regenerates them.
MODULE_SELECTOR: str = os.getenv("EDUMUNDO_MODULE_SELECTOR", "#__BVID__151")
CLASS_SELECTOR: str = os.getenv("EDUMUNDO_CLASS_SELECTOR", "#__BVID__152")

# Seconds to wait between requests (politeness delay)
REQUEST_DELAY: float = float(os.getenv("EDUMUNDO_REQUEST_DELAY", "0.5"))

# Milliseconds to wait after selecting an option before reading the page
MODULE_WAIT_MS: int = int(os.getenv("EDUMUNDO_MODULE_WAIT_MS", "1000"))
CLASS_WAIT_MS: int = int(os.getenv("EDUMUNDO_CLASS_WAIT_MS", "2000"))

# Retry settings for browser/page operations
MAX_RETRIES: int = int(os.getenv("EDUMUNDO_MAX_RETRIES", "3"))
RETRY_DELAY_S: float = float(os.getenv("EDUMUNDO_RETRY_DELAY_S", "2.0"))

# Logging
LOG_LEVEL: str = os.getenv("EDUMUNDO_LOG_LEVEL", "INFO")
