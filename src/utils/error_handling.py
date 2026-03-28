"""Structured error handling for Resolve API calls."""


def resolve_error(message: str, details: str | None = None) -> dict:
    """Return a structured error response for MCP tools."""
    result = {"success": False, "error": message}
    if details:
        result["details"] = details
    return result


def resolve_success(data: dict | list | str) -> dict:
    """Return a structured success response for MCP tools."""
    return {"success": True, "data": data}
