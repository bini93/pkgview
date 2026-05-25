from __future__ import annotations

import logging

import pytest


@pytest.fixture(autouse=True)
def reset_pkgview_logging():
    """Silence pkgview logging during tests and clean up handlers afterwards.

    Using ``autouse=True`` ensures no test accidentally emits log output to
    stderr, while tests that *want* to assert on log records can still use
    pytest's ``caplog`` fixture:

        def test_brew_warns_when_missing(caplog):
            with caplog.at_level(logging.WARNING, logger="pkgview.detectors.brew"):
                result = BrewDetector().detect()
            assert result == {}
            assert any("brew" in r.message for r in caplog.records)
    """
    logger = logging.getLogger("pkgview")
    original_level = logger.level
    original_handlers = logger.handlers[:]

    logger.handlers.clear()
    logger.setLevel(logging.CRITICAL)

    yield

    logger.handlers.clear()
    for handler in original_handlers:
        logger.addHandler(handler)
    logger.setLevel(original_level)
