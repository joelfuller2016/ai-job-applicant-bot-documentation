"""Common interface for browser automation implementations."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class BrowserInterface(ABC):
    """Abstract base class defining browser automation methods."""

    @abstractmethod
    def initialize(self, headless: bool = False) -> bool:
        """Initialize the browser."""
        raise NotImplementedError

    @abstractmethod
    def close(self) -> bool:
        """Close the browser."""
        raise NotImplementedError

    @abstractmethod
    def navigate(self, url: str, wait_for_load: bool = True) -> bool:
        """Navigate to a URL."""
        raise NotImplementedError

    @abstractmethod
    def is_element_present(self, selector: str, timeout: int = 10) -> bool:
        """Return True if element exists."""
        raise NotImplementedError

    @abstractmethod
    def wait_for_element(self, selector: str, timeout: int = 10) -> Any:
        """Wait for element to appear."""
        raise NotImplementedError

    @abstractmethod
    def click(self, selector: str, wait_after: int = 1) -> bool:
        """Click an element."""
        raise NotImplementedError

    @abstractmethod
    def fill_text(self, selector: str, text: str) -> bool:
        """Fill an input field with text."""
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, selector: str, file_path: Union[str, Path]) -> bool:
        """Upload a file using an input element."""
        raise NotImplementedError

    @abstractmethod
    def execute_script(self, script: str, *args) -> Any:
        """Execute JavaScript in browser context."""
        raise NotImplementedError
