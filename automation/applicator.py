"""Application engine managing job applications via browser automation."""

import logging
import uuid
from typing import Any, Dict

from .browser_factory import BrowserFactory
from utils.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class ApplicationEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_manager = DatabaseManager()
        self.browser = None

    def initialize_browser(self) -> bool:
        browser_config = self.config.get("browser", {})
        browser_type = browser_config.get("type", "auto")
        self.browser = BrowserFactory.create_browser(browser_type, browser_config)
        if not self.browser:
            logger.error("Could not create browser")
            return False
        return self.browser.initialize(browser_config.get("headless", False))

    def apply_to_job(self, job_id: str, resume_id: str) -> Dict[str, Any]:
        job = self.db_manager.get_job(job_id)
        resume = self.db_manager.get_resume(resume_id)
        if not job or not resume:
            logger.error("Job or resume not found")
            return {"success": False, "error": "Job or resume not found"}
        try:
            if not self.browser:
                return {"success": False, "error": "Browser not initialized"}
            self.browser.navigate(job["url"], wait_for_load=True)
            # Placeholder for form filling logic
            application_id = str(uuid.uuid4())
            self.db_manager.save_application({
                "id": application_id,
                "job_id": job_id,
                "user_id": job["user_id"],
                "resume_id": resume_id,
                "status": "submitted",
            })
            return {"success": True, "application_id": application_id}
        except Exception as exc:
            logger.error("Application failed: %s", exc)
            return {"success": False, "error": str(exc)}

    def close_browser(self) -> None:
        if self.browser:
            self.browser.close()
            self.browser = None
