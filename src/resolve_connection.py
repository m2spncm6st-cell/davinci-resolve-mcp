"""Lazy connection to DaVinci Resolve with reconnect logic."""

import logging
import os
import sys
import time

logger = logging.getLogger(__name__)

# Max retry attempts when connection is lost
_MAX_RECONNECT_ATTEMPTS = 3
_RECONNECT_DELAY = 1.0  # seconds between retries


class ResolveConnection:
    """Manages a lazy, reconnectable connection to DaVinci Resolve."""

    def __init__(self, timeout: float = 5.0):
        self._resolve = None
        self._last_check: float = 0
        self._check_interval: float = 2.0  # seconds between health checks
        self._timeout = timeout
        self._consecutive_failures: int = 0

    def _get_resolve(self):
        """Import and call scriptapp("Resolve") from DaVinciResolveScript module."""
        try:
            module_path = os.environ.get(
                "PYTHONPATH",
                "/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules",
            )
            if module_path not in sys.path:
                sys.path.insert(0, module_path)

            import DaVinciResolveScript as dvr

            resolve = dvr.scriptapp("Resolve")
            if resolve is None:
                logger.warning("scriptapp('Resolve') returned None — Resolve may not be running")
            return resolve
        except ImportError as e:
            logger.error("Failed to import DaVinciResolveScript: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to get Resolve instance: %s", e)
            return None

    def _health_check(self) -> bool:
        """Run a cheap health check against the cached connection."""
        if not self._resolve:
            return False
        try:
            result = self._resolve.GetProductName()
            return result is not None
        except Exception:
            return False

    def connect(self):
        """Get a connection to Resolve, reconnecting if necessary.

        Uses cached connection within check_interval. If health check fails,
        retries up to _MAX_RECONNECT_ATTEMPTS times with delay.

        Returns the Resolve object or None if unavailable.
        """
        now = time.time()

        # Return cached connection if recent health check passed
        if self._resolve and (now - self._last_check) < self._check_interval:
            return self._resolve

        # Health check on existing connection
        if self._resolve:
            if self._health_check():
                self._last_check = now
                self._consecutive_failures = 0
                return self._resolve
            else:
                logger.warning("Lost connection to Resolve, attempting reconnect...")
                self._resolve = None

        # (Re)connect with retries
        for attempt in range(1, _MAX_RECONNECT_ATTEMPTS + 1):
            self._resolve = self._get_resolve()
            if self._resolve and self._health_check():
                self._last_check = now
                self._consecutive_failures = 0
                logger.info("Connected to DaVinci Resolve (attempt %d)", attempt)
                return self._resolve

            if attempt < _MAX_RECONNECT_ATTEMPTS:
                logger.info("Reconnect attempt %d/%d failed, retrying...", attempt, _MAX_RECONNECT_ATTEMPTS)
                time.sleep(_RECONNECT_DELAY)

        self._resolve = None
        self._consecutive_failures += 1
        logger.warning(
            "Could not connect to DaVinci Resolve after %d attempts (total failures: %d)",
            _MAX_RECONNECT_ATTEMPTS,
            self._consecutive_failures,
        )
        return None

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


# ── Shared helper functions ──────────────────────────────────────────

_LUT_ROOTS = [
    "/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT",
    os.path.expanduser(
        "~/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT"
    ),
]


def tc_to_frames(tc: str, fps: float) -> int:
    """Convert a timecode string 'HH:MM:SS:FF' (or 'HH:MM:SS;FF') to frame number."""
    parts = tc.replace(";", ":").split(":")
    h, m, s, f = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    return int((h * 3600 + m * 60 + s) * fps + f)


def find_lut(lut_rel: str | None) -> str | None:
    """Resolve a relative or absolute LUT path against standard Resolve LUT directories.

    Returns the absolute path if found, or None.
    """
    if not lut_rel:
        return None
    if os.path.isabs(lut_rel) and os.path.exists(lut_rel):
        return lut_rel
    for root in _LUT_ROOTS:
        candidate = os.path.join(root, lut_rel)
        if os.path.exists(candidate):
            return candidate
    return None
