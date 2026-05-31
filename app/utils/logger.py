"""Loguru logger configuration for SocialPulse Intelligence."""
from loguru import logger
import sys

# Remove default handler
logger.remove()

# Add stdout handler with structured format
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function} | {message}",
    level="INFO",
    colorize=True,
)

# Optionally add file handler for production
logger.add(
    "logs/socialpulse_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {module}:{function}:{line} | {message}",
    level="DEBUG",
    rotation="1 day",
    retention="7 days",
    compression="gz",
    enqueue=True,
)

__all__ = ["logger"]
