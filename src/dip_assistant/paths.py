from __future__ import annotations

import sys
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys.executable).resolve().parent
else:
    PROJECT_ROOT = PACKAGE_ROOT.parents[1]

CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
SOURCE_DIR = PROJECT_ROOT / "数据源"
ASSETS_DIR = PROJECT_ROOT / "assets"

DEFAULT_CONFIG_PATH = CONFIG_DIR / "settings.json"
DEFAULT_DB_PATH = DATA_DIR / "dip_lookup.db"
DEFAULT_DIRECTORY_XLSX = SOURCE_DIR / "平顶山2025年DIP2.0分组目录库.xlsx"
DEFAULT_ICD10_XLSX = SOURCE_DIR / "ICD10国临版2.0对照医保版2.0.xlsx"
DEFAULT_ICD9_XLSX = SOURCE_DIR / "ICD9国临版3.0对照医保版2.0.xlsx"
APP_ICON_PATH = (
    (ASSETS_DIR / "app-icon.ico")
    if (ASSETS_DIR / "app-icon.ico").exists()
    else (PROJECT_ROOT / "app-icon.ico")
)


def ensure_runtime_dirs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
