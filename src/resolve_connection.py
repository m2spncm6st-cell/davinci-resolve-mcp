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

    # --- Navigation Helpers ---
    # These return tuples: (obj1, obj2, ..., error_or_none)
    # If error is not None, the caller should return it immediately.

    def check(self) -> tuple:
        """Verify connection and get project manager + current project.

        Returns: (project_manager, project, error_dict_or_none)
        """
        r = self.connect()
        if not r:
            return None, None, _err(
                "Not connected to DaVinci Resolve. Is it running with External Scripting set to Local?"
            )
        pm = r.GetProjectManager()
        if not pm:
            return None, None, _err("Could not get ProjectManager")
        project = pm.GetCurrentProject()
        if not project:
            return pm, None, _err("No project is currently open")
        return pm, project, None

    def get_media_pool(self) -> tuple:
        """Navigate to MediaPool.

        Returns: (project, media_pool, error_dict_or_none)
        """
        pm, project, err = self.check()
        if err:
            return None, None, err
        mp = project.GetMediaPool()
        if not mp:
            return project, None, _err("Could not access MediaPool")
        return project, mp, None

    def get_timeline(self) -> tuple:
        """Get the current timeline.

        Returns: (project, timeline, error_dict_or_none)
        """
        pm, project, err = self.check()
        if err:
            return None, None, err
        tl = project.GetCurrentTimeline()
        if not tl:
            return project, None, _err("No timeline is currently active")
        return project, tl, None


def _err(msg: str) -> dict:
    """Standardized error response."""
    return {"success": False, "error": msg}


def _ok(**kwargs) -> dict:
    """Standardized success response."""
    return {"success": True, **kwargs}


def _ser(obj) -> any:
    """Serialize Resolve API objects to JSON-compatible types."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _ser(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_ser(item) for item in obj]
    # Resolve objects — try to get their name
    if hasattr(obj, "GetName"):
        return obj.GetName()
    return str(obj)
