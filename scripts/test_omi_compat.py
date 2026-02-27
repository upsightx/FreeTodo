"""Quick smoke-test for the omi-compat API layer.

Usage:
    python scripts/test_omi_compat.py [BASE_URL]

Default BASE_URL is http://127.0.0.1:8001
"""

from __future__ import annotations

import asyncio
import sys

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001"
TOKEN = "lifetrace-omi-compat-2026"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}


def ok(label: str) -> None:
    print(f"  [OK] {label}")


def fail(label: str, detail: str = "") -> None:
    print(f"  [FAIL] {label}  {detail}")


async def main() -> None:
    async with httpx.AsyncClient(base_url=BASE, headers=HEADERS, timeout=10) as c:
        print(f"\n=== omi-compat smoke test  ({BASE}) ===\n")

        # 1. GET /v1/users/me
        print("[1] GET /v1/users/me")
        r = await c.get("/v1/users/me")
        if r.status_code == 200 and "uid" in r.json():
            ok(f"status={r.status_code}  uid={r.json()['uid']}")
        else:
            fail(f"status={r.status_code}", r.text[:200])

        # 2. GET /v1/users/onboarding-status
        print("[2] GET /v1/users/onboarding-status")
        r = await c.get("/v1/users/onboarding-status")
        if r.status_code == 200:
            ok(f"completed={r.json().get('completed')}")
        else:
            fail(f"status={r.status_code}")

        # 3. GET /v3/speech-profile
        print("[3] GET /v3/speech-profile")
        r = await c.get("/v3/speech-profile")
        if r.status_code == 200:
            ok(f"has_profile={r.json().get('has_profile')}")
        else:
            fail(f"status={r.status_code}")

        # 4. GET /v1/conversations
        print("[4] GET /v1/conversations")
        r = await c.get("/v1/conversations")
        if r.status_code == 200:
            data = r.json()
            ok(f"returned {len(data)} conversations")
        else:
            fail(f"status={r.status_code}", r.text[:200])

        # 5. GET /v3/memories
        print("[5] GET /v3/memories")
        r = await c.get("/v3/memories")
        if r.status_code == 200:
            data = r.json()
            ok(f"returned {len(data)} memories")
        else:
            fail(f"status={r.status_code}", r.text[:200])

        # 6. POST /v1/users/store-device-token (no-op)
        print("[6] POST /v1/users/store-device-token")
        r = await c.post("/v1/users/store-device-token")
        if r.status_code == 200:
            ok("accepted")
        else:
            fail(f"status={r.status_code}")

        # 7. GET /v2/firmware/latest (should 404)
        print("[7] GET /v2/firmware/latest")
        r = await c.get("/v2/firmware/latest")
        if r.status_code == 404:
            ok("no update available (expected 404)")
        else:
            fail(f"status={r.status_code} (expected 404)")

        # 8. WebSocket /v4/listen (quick connect/disconnect)
        print("[8] WebSocket /v4/listen")
        try:
            import websockets  # type: ignore[import-untyped]

            ws_base = BASE.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = (
                f"{ws_base}/v4/listen"
                f"?uid=lifetrace-user&token={TOKEN}"
                f"&language=zh&sample_rate=16000&codec=pcm16"
            )
            async with websockets.connect(ws_url) as ws:
                await ws.close()
            ok("connected and closed cleanly")
        except ImportError:
            fail("websockets package not installed, skipping WS test")
        except Exception as e:
            fail(f"WebSocket error: {e}")

        # 9. Auth rejection test
        print("[9] Auth rejection (bad token)")
        r = await c.get(
            "/v1/users/me",
            headers={"Authorization": "Bearer wrong-token"},
        )
        if r.status_code == 401:
            ok("correctly rejected")
        else:
            fail(f"status={r.status_code} (expected 401)")

        print("\n=== done ===\n")


if __name__ == "__main__":
    asyncio.run(main())
