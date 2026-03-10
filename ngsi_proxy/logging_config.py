"""Central logging configuration helpers."""
from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _resolve_level(level: str | int | None) -> int:
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        return logging.getLevelName(level.upper())
    return logging.INFO


def configure_logging(level: str | int | None = None, *, force: bool = False) -> None:
    """Configure root logger with a single console handler."""
    root = logging.getLogger()
    if root.handlers and not force:
        root.setLevel(_resolve_level(level))
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(DEFAULT_FORMAT))

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(_resolve_level(level))


configure_logging()
