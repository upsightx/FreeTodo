"""Omi-compatible user / firmware / misc endpoints.

The omi App calls several user-profile and firmware endpoints at startup.
We provide stub or proxy responses so the App doesn't crash.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from lifetrace.routers.omi_compat.auth import verify_token
from lifetrace.util.logging_config import get_logger

logger = get_logger()

router = APIRouter(tags=["omi-users"])


# ---------------------------------------------------------------------------
# User profile
# ---------------------------------------------------------------------------


@router.get("/v1/users/me")
async def get_current_user(uid: str = Depends(verify_token)):
    """Return a minimal user profile that satisfies the omi App."""
    return {
        "uid": uid,
        "email": "",
        "name": "LifeTrace User",
        "created_at": "2026-01-01T00:00:00Z",
        "plan_type": "unlimited",
        "has_speech_profile": False,
        "geolocation": None,
    }


# ---------------------------------------------------------------------------
# Speech profile (stub – no speaker embedding yet)
# ---------------------------------------------------------------------------


@router.get("/v3/speech-profile")
async def has_speech_profile(uid: str = Depends(verify_token)):
    return {"has_profile": False}


@router.get("/v4/speech-profile")
async def get_speech_profile(uid: str = Depends(verify_token)):
    return {"url": None}


# ---------------------------------------------------------------------------
# Firmware – proxy to omi GitHub releases
# ---------------------------------------------------------------------------


@router.get("/v2/firmware/latest")
async def get_latest_firmware(
    device_model: str = "",
    firmware_revision: str = "",
    hardware_revision: str = "",
    manufacturer_name: str = "",
):
    """Proxy firmware check.

    For now we return 404 to signal "no update available". In the
    future this can proxy to the omi GitHub Releases API.
    """
    from fastapi import HTTPException

    raise HTTPException(status_code=404, detail="No firmware update available")


# ---------------------------------------------------------------------------
# Notifications / onboarding stubs
# ---------------------------------------------------------------------------


@router.post("/v1/users/store-device-token")
async def store_device_token(uid: str = Depends(verify_token)):
    """FCM token storage – no-op since we don't use FCM."""
    return {"status": "ok"}


@router.get("/v1/users/onboarding-status")
async def onboarding_status(uid: str = Depends(verify_token)):
    return {"completed": True}


@router.post("/v3/users/geolocation")
async def update_geolocation(uid: str = Depends(verify_token)):
    return {"status": "ok"}
