"""Plugin installer service with baseline security checks.

Phase 2 scope:
- local archive install/uninstall
- checksum and archive validation framework
- lock + rollback skeleton
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import stat
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from zipfile import ZipFile

from lifetrace.util import base_paths
from lifetrace.util.settings import settings

PLUGIN_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{1,63}$")
MAX_ARCHIVE_FILE_COUNT = 5000
MAX_ARCHIVE_TOTAL_SIZE = 2 * 1024 * 1024 * 1024  # 2GB


class PluginInstallError(RuntimeError):
    """Base install/uninstall exception."""


class PluginValidationError(PluginInstallError):
    """Validation failure for plugin id/archive/checksum."""


@dataclass
class InstallResult:
    """Install operation result."""

    plugin_id: str
    success: bool
    install_dir: str
    checksum: str | None
    message: str


@dataclass
class UninstallResult:
    """Uninstall operation result."""

    plugin_id: str
    success: bool
    install_dir: str
    message: str


class PluginInstaller:
    """Installer service for third-party plugins."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def get_install_root(self) -> Path:
        """Resolve plugin install root path."""
        configured_dir = str(settings.get("plugins.install_dir", "plugins"))
        root = Path(configured_dir)
        if not root.is_absolute():
            root = base_paths.get_user_data_dir() / root
        root.mkdir(parents=True, exist_ok=True)
        return root

    def list_installed_plugin_ids(self) -> list[str]:
        """List plugin ids from install root."""
        root = self.get_install_root()
        plugin_ids: list[str] = []
        for item in root.iterdir():
            if not item.is_dir():
                continue
            if item.name.startswith(".") or item.name.endswith(".bak"):
                continue
            if not PLUGIN_ID_PATTERN.match(item.name):
                continue
            plugin_ids.append(item.name)
        return sorted(plugin_ids)

    def get_plugin_dir(self, plugin_id: str) -> Path:
        """Get plugin install directory after id validation."""
        self.validate_plugin_id(plugin_id)
        return self.get_install_root() / plugin_id

    def is_installed(self, plugin_id: str) -> bool:
        """Return whether plugin directory exists."""
        return self.get_plugin_dir(plugin_id).exists()

    def read_manifest(self, plugin_id: str) -> dict[str, object] | None:
        """Read plugin manifest when available."""
        plugin_dir = self.get_plugin_dir(plugin_id)
        manifest_path = plugin_dir / "plugin.manifest.json"
        if not manifest_path.exists():
            return None
        with manifest_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def install_from_archive(
        self,
        plugin_id: str,
        archive_path: str,
        expected_sha256: str | None = None,
        force: bool = False,
    ) -> InstallResult:
        """Install plugin from local zip archive with validation and rollback."""
        with self._lock:
            self.validate_plugin_id(plugin_id)
            archive = Path(archive_path).expanduser().resolve()
            checksum = self._calculate_sha256(archive)
            self._validate_archive(archive)
            self._validate_checksum(checksum, expected_sha256)

            install_dir = self.get_plugin_dir(plugin_id)
            backup_dir = install_dir.with_name(
                f"{plugin_id}.bak.{datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}"
            )
            temp_dir = self.get_install_root() / f".{plugin_id}.tmp.{uuid.uuid4().hex[:8]}"

            if install_dir.exists() and not force:
                raise PluginValidationError(f"插件 {plugin_id} 已安装，若要覆盖请设置 force=true")

            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                temp_dir.mkdir(parents=True, exist_ok=True)

                self._safe_extract_zip(archive, temp_dir)

                manifest_path = temp_dir / "plugin.manifest.json"
                if not manifest_path.exists():
                    raise PluginValidationError("插件包缺少 plugin.manifest.json")

                if install_dir.exists():
                    install_dir.rename(backup_dir)
                temp_dir.rename(install_dir)

                if backup_dir.exists():
                    shutil.rmtree(backup_dir, ignore_errors=True)

                return InstallResult(
                    plugin_id=plugin_id,
                    success=True,
                    install_dir=str(install_dir),
                    checksum=checksum,
                    message="插件安装成功",
                )
            except Exception:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir, ignore_errors=True)
                if backup_dir.exists() and not install_dir.exists():
                    backup_dir.rename(install_dir)
                raise

    def uninstall(self, plugin_id: str) -> UninstallResult:
        """Uninstall plugin by removing install directory."""
        with self._lock:
            self.validate_plugin_id(plugin_id)
            install_dir = self.get_plugin_dir(plugin_id)
            if not install_dir.exists():
                raise PluginValidationError(f"插件 {plugin_id} 未安装")
            shutil.rmtree(install_dir)
            return UninstallResult(
                plugin_id=plugin_id,
                success=True,
                install_dir=str(install_dir),
                message="插件卸载成功",
            )

    def validate_plugin_id(self, plugin_id: str) -> None:
        """Validate plugin id against safe pattern."""
        if not PLUGIN_ID_PATTERN.match(plugin_id):
            raise PluginValidationError("插件 ID 非法，仅允许小写字母开头，包含小写字母/数字/_/-")

    def _calculate_sha256(self, archive_path: Path) -> str:
        """Calculate SHA-256 checksum for archive."""
        if not archive_path.exists() or not archive_path.is_file():
            raise PluginValidationError(f"插件包不存在: {archive_path}")

        digest = hashlib.sha256()
        with archive_path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _validate_archive(self, archive_path: Path) -> None:
        """Validate archive extension and entry safety."""
        if archive_path.suffix.lower() != ".zip":
            raise PluginValidationError("当前仅支持 .zip 插件包")

        with ZipFile(archive_path, "r") as zip_file:
            infos = zip_file.infolist()
            if len(infos) > MAX_ARCHIVE_FILE_COUNT:
                raise PluginValidationError(
                    f"插件包文件数超限: {len(infos)} > {MAX_ARCHIVE_FILE_COUNT}"
                )

            total_size = 0
            for info in infos:
                entry_name = info.filename
                if not entry_name:
                    raise PluginValidationError("插件包包含空路径条目")

                entry_path = Path(entry_name)
                if entry_path.is_absolute() or ".." in entry_path.parts:
                    raise PluginValidationError(f"插件包包含非法路径: {entry_name}")

                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise PluginValidationError(f"插件包不允许符号链接: {entry_name}")

                total_size += info.file_size

            if total_size > MAX_ARCHIVE_TOTAL_SIZE:
                raise PluginValidationError(
                    f"插件包解压总大小超限: {total_size} > {MAX_ARCHIVE_TOTAL_SIZE}"
                )

    def _validate_checksum(self, actual: str, expected: str | None) -> None:
        """Validate checksum according to security settings."""
        enforce_checksum = bool(settings.get("plugins.security.enforce_checksum", True))
        allow_unsigned = bool(settings.get("plugins.security.allow_unsigned", False))

        if not expected:
            if enforce_checksum and not allow_unsigned:
                raise PluginValidationError("缺少 expected_sha256，安全策略禁止无签名安装")
            return

        if actual.lower() != expected.lower():
            raise PluginValidationError("插件包校验失败（SHA-256 不匹配）")

    def _safe_extract_zip(self, archive_path: Path, target_dir: Path) -> None:
        """Extract zip into target dir after prior path validation."""
        with ZipFile(archive_path, "r") as zip_file:
            zip_file.extractall(target_dir)
