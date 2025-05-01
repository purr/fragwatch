import sys

from loguru import logger

logger.remove()
logger.configure(handlers=[])

logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{file.path}:{line}</cyan> - "
        "<level>{message}</level>"
    ),
    level="DEBUG",
    colorize=True,
)
