"""Logging configuration."""

import logging
import sys


def setup_logging(debug: bool = False) -> logging.Logger:
    """Configure application logging.

    Args:
        debug: Enable debug level logging.

    Returns:
        Configured root logger.
    """
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    logger = logging.getLogger("aureon")
    logger.setLevel(level)
    return logger
