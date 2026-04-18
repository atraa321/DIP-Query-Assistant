from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd

from .paths import DEFAULT_DB_PATH, DEFAULT_DIRECTORY_XLSX, ensure_runtime_dirs


DIRECTORY_COLUMNS: Dict[str, str] = {
    "病种编码": "dip_group_code",
    "病种类型（1.核心病种；2.综合病种）": "group_type_raw",
    "主诊断代码": "main_diag_code",
    "主诊断名称": "main_diag_name",
    "主要操作代码": "main_operation_code",
    "主要操作名称": "main_operation_name",
    "其他操作代码": "other_operation_code",
    "其他操作名称": "other_operation_name",
    "病种分值": "score_value",
}


def build_lookup_database(
    source_excel: Path = DEFAULT_DIRECTORY_XLSX,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    ensure_runtime_dirs()
    if not source_excel.exists():
        raise FileNotFoundError("未找到 DIP 目录库: %s" % source_excel)

    directory_df = pd.read_excel(source_excel, sheet_name="目录", dtype=str).fillna("")
    for source_name in DIRECTORY_COLUMNS:
        if source_name not in directory_df.columns:
            raise ValueError("目录库缺少必要列: %s" % source_name)

    normalized = directory_df[list(DIRECTORY_COLUMNS.keys())].rename(columns=DIRECTORY_COLUMNS).copy()
    normalized["dip_group_code"] = normalized["dip_group_code"].map(_clean_text)
    normalized["group_type"] = normalized["group_type_raw"].map(_normalize_group_type)
    normalized["score_value"] = normalized["score_value"].map(_to_float_or_zero)
    for field in (
        "main_diag_code",
        "main_diag_name",
        "main_operation_code",
        "main_operation_name",
        "other_operation_code",
        "other_operation_name",
    ):
        normalized[field] = normalized[field].map(_clean_text)

    normalized["dip_group_name"] = normalized.apply(_derive_group_name, axis=1)
    normalized["search_text"] = normalized.apply(_build_search_text, axis=1)
    normalized["code_upper"] = normalized["dip_group_code"].str.upper()

    normalized = normalized.drop_duplicates(
        subset=["dip_group_code", "dip_group_name", "main_diag_code", "main_operation_code"]
    ).reset_index(drop=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("DROP TABLE IF EXISTS dip_groups")
        conn.execute("DROP TABLE IF EXISTS app_meta")
        conn.execute(
            """
            CREATE TABLE dip_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dip_group_code TEXT NOT NULL,
                code_upper TEXT NOT NULL,
                dip_group_name TEXT NOT NULL,
                group_type TEXT NOT NULL,
                group_type_raw TEXT,
                main_diag_code TEXT,
                main_diag_name TEXT,
                main_operation_code TEXT,
                main_operation_name TEXT,
                other_operation_code TEXT,
                other_operation_name TEXT,
                score_value REAL NOT NULL,
                search_text TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE app_meta (
                meta_key TEXT PRIMARY KEY,
                meta_value TEXT NOT NULL
            )
            """
        )
        normalized.to_sql("dip_groups", conn, if_exists="append", index=False)
        conn.executemany(
            "INSERT INTO app_meta(meta_key, meta_value) VALUES (?, ?)",
            [
                ("source_excel", str(source_excel)),
                ("record_count", str(len(normalized))),
            ],
        )
        conn.execute("CREATE INDEX idx_dip_groups_code ON dip_groups(code_upper)")
        conn.execute("CREATE INDEX idx_dip_groups_name ON dip_groups(dip_group_name)")
        conn.execute("CREATE INDEX idx_dip_groups_score ON dip_groups(score_value)")
        conn.commit()
    finally:
        conn.close()

    return int(len(normalized))


def inspect_reference_files(source_dir: Path) -> Iterable[str]:
    for entry in sorted(source_dir.glob("*.xlsx")):
        yield entry.name


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _to_float_or_zero(value: object) -> float:
    text = _clean_text(value)
    if not text:
        return 0.0
    return float(text)


def _normalize_group_type(value: object) -> str:
    raw = _clean_text(value)
    if raw == "1":
        return "核心病种"
    if raw in ("0", "2"):
        return "综合病种"
    return "未知"


def _derive_group_name(row: pd.Series) -> str:
    if row["main_diag_name"] and row["main_operation_name"]:
        return "%s / %s" % (row["main_diag_name"], row["main_operation_name"])
    if row["main_diag_name"]:
        return row["main_diag_name"]
    if row["main_operation_name"]:
        return row["main_operation_name"]
    return row["dip_group_code"]


def _build_search_text(row: pd.Series) -> str:
    parts = [
        row["dip_group_code"],
        row["dip_group_name"],
        row["main_diag_code"],
        row["main_diag_name"],
        row["main_operation_code"],
        row["main_operation_name"],
        row["other_operation_code"],
        row["other_operation_name"],
    ]
    text = " ".join(part for part in parts if part)
    return " ".join(text.upper().split())
