from __future__ import annotations

import logging
import sys

def setup_logging(debug: bool = False) -> None:
    """Configure pkgview logging. Must be called once at startup.

    - Default: WARNING and above → stderr
    - ``--debug``: DEBUG and above → stderr with timestamps and module info
    """
    level = logging.DEBUG if debug else logging.WARNING

    logger = logging.getLogger("pkgview")
    logger.setLevel(level)

    # Clear any handlers added by a previous call (e.g. in tests)
    if logger.handlers:
        logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)

    if debug:
        fmt = "%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d – %(message)s"
    else:
        fmt = "%(levelname)s: %(message)s"

    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    # Do not propagate to the root logger to avoid duplicate output
    logger.propagate = False
