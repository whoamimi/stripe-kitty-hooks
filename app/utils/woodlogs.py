# utils/woodlogs.py
# Sets up loggers with uvicorn format for FastAPI applications
from __future__ import annotations

import logging
import sys
from copy import copy

# Uvicorn color codes
GREY = "\033[90m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD_RED = "\033[1;91m"
RESET = "\033[0m"

class UvicornFormatter(logging.Formatter):
    """Custom formatter that matches uvicorn's CLI styling."""

    LEVEL_COLORS = {
        logging.DEBUG: GREY,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        # Create a copy to avoid modifying the original record
        record = copy(record)

        # Apply color to level name
        level_color = self.LEVEL_COLORS.get(record.levelno, RESET)
        record.levelname = f"{level_color}{record.levelname:<8}{RESET}"

        # Format: INFO:     taro.module - message
        return f"{record.levelname} {BLUE}{record.name}{RESET} - {record.getMessage()}"

def get_logger(name: str | None = None, **kwargs) -> logging.Logger:
    """
    Get a logger configured with uvicorn's CLI styling.

    Args:
        name: Module name (typically __name__). Used as prefix in log messages.
              If None, returns root logger.

    Returns:
        Logger instance with uvicorn-style formatting and colors.
    """
    logger_name = name if name else "uvicorn"
    logger = logging.getLogger(logger_name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(kwargs.get("debug_level", logging.INFO))

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(kwargs.get("debug_level", logging.INFO))
        handler.setFormatter(UvicornFormatter())

        logger.addHandler(handler)
        logger.propagate = False

    return logger