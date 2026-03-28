"""Lazy connection to DaVinci Resolve with reconnect logic."""

import importlib
import logging
import os
import sys
import time

logger = logging.getLogger(__name__)


class ResolveConnection:
    """Manages a lazy, reconnectable connection to DaVinci Resolve."""

    def __init__(self, timeout: float = 5.0):
        self._resolve = None
        self._last_check: float = 0
        self._check_interval: float = 2.0  # seconds between health checks
        self._timeout = timeout

    def _get_resolve(self):
        """Import and call GetResolve() from DaVinciResolveScript module."""
        try:
            # Ensure the scripting module path is available
            module_path = os.environ.get(
                "PYTHONPATH",
                "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
            )
            if module_path not in sys.path:
                sys.path.insert(0, module_path)

            import DaVinciResolveScript as dvr

            return dvr.scriptapp("Resolve")
        except ImportError as e:
            logger.error("Failed to import DaVinciResolveScript: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to get Resolve instance: %s", e)
            return None

    def connect(self):
        """Get a connection to Resolve, reconnecting if necessary.

        Returns the Resolve object or None if unavailable.
        """
        now = time.time()

        # Return cached connection if recent health check passed
        if self._resolve and (now - self._last_check) < self._check_interval:
            return self._resolve

        # Health check: try to call a simple method
        if self._resolve:
            try:
                self._resolve.GetProductName()
                self._last_check = now
                return self._resolve
            except Exception:
                logger.warning("Lost connection to Resolve, attempting reconnect...")
                self._resolve = None

        # (Re)connect
        self._resolve = self._get_resolve()
        if self._resolve:
            self._last_check = now
            logger.info("Connected to DaVinci Resolve")
        else:
            logger.warning("Could not connect to DaVinci Resolve")

        return self._resolve

    @property
    def is_connected(self) -> bool:
        """Check if we have an active connection."""
        return self.connect() is not None

    def disconnect(self):
        """Clear the cached connection."""
        self._resolve = None
        self._last_check = 0
