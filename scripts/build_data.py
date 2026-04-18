from __future__ import annotations

import argparse
from pathlib import Path

from dip_assistant.data_builder import build_lookup_database
from dip_assistant.paths import DEFAULT_DB_PATH, DEFAULT_DIRECTORY_XLSX


def main() -> int:
    parser = argparse.ArgumentParser(description="从 DIP Excel 目录库生成本地 SQLite 查询库。")
    parser.add_argument("--source", default=str(DEFAULT_DIRECTORY_XLSX), help="DIP 目录库 Excel 路径")
    parser.add_argument("--output", default=str(DEFAULT_DB_PATH), help="输出 SQLite 路径")
    args = parser.parse_args()

    count = build_lookup_database(source_excel=Path(args.source), db_path=Path(args.output))
    print("查询库生成完成：%s 条记录 -> %s" % (count, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
