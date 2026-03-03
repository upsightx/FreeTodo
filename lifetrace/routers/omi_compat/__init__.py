"""Omi App / Hardware compatibility layer.

Provides API endpoints that mimic omi's backend so the omi Flutter App
and hardware devices can connect to LifeTrace Center directly.
"""

from __future__ import annotations

from fastapi import APIRouter

from lifetrace.routers.omi_compat.auth import router as auth_router
from lifetrace.routers.omi_compat.conversations import router as conversations_router
from lifetrace.routers.omi_compat.listen import router as listen_router
from lifetrace.routers.omi_compat.memories import router as memories_router
from lifetrace.routers.omi_compat.stubs import router as stubs_router
from lifetrace.routers.omi_compat.stubs_misc import router as stubs_misc_router
from lifetrace.routers.omi_compat.users import router as users_router

router = APIRouter()

router.include_router(auth_router)
router.include_router(listen_router)
router.include_router(conversations_router)
router.include_router(memories_router)
router.include_router(users_router)
router.include_router(stubs_router)
router.include_router(stubs_misc_router)
