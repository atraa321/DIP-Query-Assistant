from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .paths import DEFAULT_CONFIG_PATH, DEFAULT_DB_PATH, PROJECT_ROOT, SOURCE_DIR, ensure_runtime_dirs


@dataclass
class AppConfig:
    resident_point_value: Optional[float] = None
    employee_point_value: Optional[float] = None
    database_path: str = str(DEFAULT_DB_PATH)
    source_directory: str = str(SOURCE_DIR)
    window_x: int = 200
    window_y: int = 80
    window_width: int = 540
    window_height: int = 480
    always_on_top: bool = True
    idle_opacity: float = 0.78


class ConfigStore:
    def __init__(self, path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.path = path
        ensure_runtime_dirs()

    def load(self) -> AppConfig:
        if not self.path.exists():
            config = AppConfig()
            self.save(config)
            return config

        with self.path.open("r", encoding="utf-8-sig") as handle:
            payload = json.load(handle)
        return AppConfig(
            resident_point_value=_to_float_or_none(payload.get("resident_point_value")),
            employee_point_value=_to_float_or_none(payload.get("employee_point_value")),
            database_path=_normalize_runtime_path(
                payload.get("database_path"),
                DEFAULT_DB_PATH,
                expect_dir=False,
            ),
            source_directory=_normalize_runtime_path(
                payload.get("source_directory"),
                SOURCE_DIR,
                expect_dir=True,
            ),
            window_x=int(payload.get("window_x", 160)),
            window_y=int(payload.get("window_y", 120)),
            window_width=max(420, int(payload.get("window_width", 540))),
            window_height=max(340, int(payload.get("window_height", 480))),
            always_on_top=bool(payload.get("always_on_top", True)),
            idle_opacity=_to_opacity(payload.get("idle_opacity", 0.78)),
        )

    def save(self, config: AppConfig) -> None:
        ensure_runtime_dirs()
        payload = {
            "resident_point_value": config.resident_point_value,
            "employee_point_value": config.employee_point_value,
            "database_path": _serialize_runtime_path(config.database_path, DEFAULT_DB_PATH),
            "source_directory": _serialize_runtime_path(config.source_directory, SOURCE_DIR),
            "window_x": config.window_x,
            "window_y": config.window_y,
            "window_width": config.window_width,
            "window_height": config.window_height,
            "always_on_top": config.always_on_top,
            "idle_opacity": config.idle_opacity,
        }
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)


def _to_float_or_none(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_opacity(value: Any) -> float:
    try:
        opacity = float(value)
    except (TypeError, ValueError):
        return 0.78
    return min(1.0, max(0.35, opacity))


def _normalize_runtime_path(value: Any, default_path: Path, expect_dir: bool) -> str:
    text = str(value or "").strip()
    if not text:
        return str(default_path)

    candidate = Path(text)
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()

    if expect_dir:
        return str(candidate if candidate.exists() and candidate.is_dir() else default_path)
    return str(candidate if candidate.exists() and candidate.is_file() else default_path)


def _serialize_runtime_path(value: str, default_path: Path) -> str:
    text = str(value or "").strip()
    if not text:
        return str(default_path.relative_to(PROJECT_ROOT))

    candidate = Path(text)
    if not candidate.is_absolute():
        return text.replace("/", "\\")

    try:
        return str(candidate.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(default_path.relative_to(PROJECT_ROOT))
