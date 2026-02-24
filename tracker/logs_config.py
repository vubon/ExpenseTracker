import logging
import os

_log_level_name = os.getenv("ET_LOG_LEVEL", "INFO").upper()
_log_level = getattr(logging, _log_level_name, logging.INFO)

logging.basicConfig(
	level=_log_level,
	format="%(asctime)s %(levelname)s %(name)s - %(message)s",
	datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("tracker")
