"""Utilities for AgentOS runtime configuration."""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

from lifetrace.util.base_paths import get_user_data_dir
from lifetrace.util.logging_config import get_logger
from lifetrace.util.settings import settings

logger = get_logger()

DEFAULT_AGENT_OS_PORT_MIN = 8200
DEFAULT_AGENT_OS_PORT_MAX = 8299
PORT_RANGE_MIN_ITEMS = 2


def _resolve_port_range() -> tuple[int, int]:
    value = settings.get("agno.agent_os.port_range", {}) or {}
    min_port = DEFAULT_AGENT_OS_PORT_MIN
    max_port = DEFAULT_AGENT_OS_PORT_MAX

    if isinstance(value, dict):
        min_port = int(value.get("min", min_port))
        max_port = int(value.get("max", max_port))
    elif isinstance(value, list | tuple) and len(value) >= PORT_RANGE_MIN_ITEMS:
        min_port = int(value[0])
        max_port = int(value[1])

    if min_port > max_port:
        min_port, max_port = max_port, min_port

    return min_port, max_port


def resolve_agent_os_port_file() -> Path:
    path_value = settings.get("agno.agent_os.port_file", "agent_os_port.json")
    path_str = str(path_value or "agent_os_port.json")
    path = Path(path_str)
    if path.is_absolute():
        return path
    return get_user_data_dir() / path


def write_agent_os_port_file(host: str, port: int) -> None:
    path = resolve_agent_os_port_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"host": host, "port": port}
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def read_agent_os_port_file() -> dict[str, Any] | None:
    path = resolve_agent_os_port_file()
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("[agentos] 端口文件解析失败: %s", path)
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def select_agent_os_port(host: str) -> int:
    port_value = settings.get("agno.agent_os.port")
    if port_value:
        return int(port_value)

    min_port, max_port = _resolve_port_range()
    for port in range(min_port, max_port + 1):
        if is_port_available(host, port):
            return port

    raise RuntimeError(f"AgentOS 端口区间 {min_port}-{max_port} 内无可用端口")


def resolve_agent_os_base_url() -> str:
    base_url = settings.get("agno.agent_os.base_url")
    if base_url:
        return str(base_url).rstrip("/")

    host = str(settings.get("agno.agent_os.host", "127.0.0.1"))
    port_data = read_agent_os_port_file()
    if port_data:
        port = port_data.get("port")
        host = port_data.get("host", host)
        if port:
            return f"http://{host}:{port}"

    port_value = settings.get("agno.agent_os.port")
    if port_value:
        return f"http://{host}:{int(port_value)}"

    min_port, _ = _resolve_port_range()
    return f"http://{host}:{min_port}"
