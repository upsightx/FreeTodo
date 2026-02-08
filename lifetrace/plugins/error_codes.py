"""Plugin domain error codes and API error payload helpers."""

from __future__ import annotations

from dataclasses import dataclass


class PluginErrorCode:
    """Stable plugin API error codes."""

    INVALID_PLUGIN_ID = "PLUGIN_INVALID_ID"
    VALIDATION_FAILED = "PLUGIN_VALIDATION_FAILED"
    NOT_INSTALLED = "PLUGIN_NOT_INSTALLED"
    ALREADY_INSTALLED = "PLUGIN_ALREADY_INSTALLED"
    CHECKSUM_MISMATCH = "PLUGIN_CHECKSUM_MISMATCH"
    MISSING_CHECKSUM = "PLUGIN_MISSING_CHECKSUM"
    ARCHIVE_INVALID = "PLUGIN_ARCHIVE_INVALID"
    MANIFEST_MISSING = "PLUGIN_MANIFEST_MISSING"
    ENABLE_NOT_ALLOWED = "PLUGIN_ENABLE_NOT_ALLOWED"
    INSTALL_FAILED = "PLUGIN_INSTALL_FAILED"
    UNINSTALL_FAILED = "PLUGIN_UNINSTALL_FAILED"
    INTERNAL_ERROR = "PLUGIN_INTERNAL_ERROR"


@dataclass(frozen=True)
class PluginApiError:
    """Typed API error payload for plugin endpoints."""

    code: str
    message: str
    details: dict[str, object] | None = None

    def to_payload(self) -> dict[str, object]:
        """Serialize payload for HTTP responses."""
        payload: dict[str, object] = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            payload["details"] = self.details
        return payload
