"""Factory for creating browser automation instances."""

import logging
from typing import Any, Dict, Optional

from .browser_interface import BrowserInterface

try:
    from .ai_browser import AIBrowser
except Exception:  # pragma: no cover - not essential if deps missing
    AIBrowser = None  # type: ignore

logger = logging.getLogger(__name__)

class BrowserFactory:
    """Create browser instances based on configuration."""

    @staticmethod
    def create_browser(browser_type: str = "standard", config: Optional[Dict[str, Any]] = None) -> Optional[BrowserInterface]:
        config = config or {}
        if browser_type == "auto":
            browser_type = "standard"
            if config.get("headless"):
                browser_type = "standard"  # placeholder for puppeteer
        try:
            if browser_type == "standard" and AIBrowser is not None:
                return AIBrowser(config)
            else:
                logger.error("Unknown or unsupported browser type: %s", browser_type)
                return None
        except Exception as exc:
            logger.error("Failed to create browser: %s", exc)
            return None
