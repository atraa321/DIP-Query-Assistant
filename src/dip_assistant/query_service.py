from __future__ import annotations

import sqlite3
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class QueryResult:
    code: str
    name: str
    score_value: float
    resident_point_value: Optional[float]
    resident_estimated_amount: Optional[float]
    employee_point_value: Optional[float]
    employee_estimated_amount: Optional[float]
    match_type: str
    group_type: str


class DipQueryService:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def is_ready(self) -> bool:
        return self.db_path.exists()

    def search(
        self,
        keyword: str,
        resident_point_value: Optional[float],
        employee_point_value: Optional[float],
        limit: int = 50,
    ) -> List[QueryResult]:
        normalized = self._normalize_keyword(keyword)
        if not normalized:
            return []
        if not self.db_path.exists():
            raise FileNotFoundError("未找到运行时数据库: %s" % self.db_path)

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.row_factory = sqlite3.Row
            rows = self._search_rows(conn, normalized, limit)
        finally:
            conn.close()

        results = []
        for row in rows:
            score_value = float(row["score_value"])
            results.append(
                QueryResult(
                    code=row["dip_group_code"],
                    name=row["dip_group_name"],
                    score_value=score_value,
                    resident_point_value=resident_point_value,
                    resident_estimated_amount=self._calc_amount(score_value, resident_point_value),
                    employee_point_value=employee_point_value,
                    employee_estimated_amount=self._calc_amount(score_value, employee_point_value),
                    match_type=row["match_type"],
                    group_type=row["group_type"],
                )
            )
        return results

    def _search_rows(self, conn: sqlite3.Connection, keyword: str, limit: int) -> List[sqlite3.Row]:
        exact_rows = conn.execute(
            """
            SELECT dip_group_code, dip_group_name, score_value, group_type, 'exact_code' AS match_type
            FROM dip_groups
            WHERE code_upper = ?
            ORDER BY score_value DESC, dip_group_code ASC
            LIMIT ?
            """,
            (keyword, limit),
        ).fetchall()
        if exact_rows:
            return exact_rows

        if self._looks_like_code(keyword):
            code_rows = self._search_code_prefix_rows(conn, keyword, limit)
            if code_rows:
                return code_rows

        tokens = [token for token in keyword.split(" ") if token]
        where_parts = ["search_text LIKE ?"]
        params = ["%%%s%%" % keyword]
        for token in tokens:
            where_parts.append("search_text LIKE ?")
            params.append("%%%s%%" % token)

        query = """
            SELECT dip_group_code, dip_group_name, score_value, group_type, 'name_like' AS match_type
            FROM dip_groups
            WHERE %s
            ORDER BY
                score_value DESC,
                dip_group_code ASC
            LIMIT ?
        """ % " AND ".join(where_parts)
        params.extend([limit])
        return conn.execute(query, params).fetchall()

    def _search_code_prefix_rows(
        self,
        conn: sqlite3.Connection,
        keyword: str,
        limit: int,
    ) -> List[sqlite3.Row]:
        prefix_like = "%s%%" % keyword
        subtype_like = "%s.%%" % keyword
        query = """
            SELECT
                dip_group_code,
                dip_group_name,
                score_value,
                group_type,
                'code_prefix' AS match_type
            FROM dip_groups
            WHERE code_upper LIKE ?
            ORDER BY
                CASE
                    WHEN code_upper = ? THEN 0
                    ELSE 1
                END,
                score_value DESC,
                code_upper ASC
            LIMIT ?
        """
        return conn.execute(
            query,
            (prefix_like, keyword, limit),
        ).fetchall()

    @staticmethod
    def _normalize_keyword(value: str) -> str:
        return " ".join((value or "").upper().strip().split())

    @staticmethod
    def _looks_like_code(value: str) -> bool:
        return bool(re.match(r"^[A-Z][0-9]{1,3}([.:\-0-9A-ZX]*)?$", value))

    @staticmethod
    def _calc_amount(score_value: float, point_value: Optional[float]) -> Optional[float]:
        if point_value is None:
            return None
        return round(score_value * point_value, 2)
