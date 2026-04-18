from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dip_assistant.data_builder import build_lookup_database
from dip_assistant.paths import DEFAULT_DIRECTORY_XLSX
from dip_assistant.query_service import DipQueryService


class QueryServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "dip_lookup.db"
        build_lookup_database(DEFAULT_DIRECTORY_XLSX, self.db_path)
        self.service = DipQueryService(self.db_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_exact_code_query_returns_score_and_amounts(self) -> None:
        results = self.service.search("A03.9", resident_point_value=92.5, employee_point_value=105.0)
        self.assertTrue(results)
        self.assertEqual(results[0].code, "A03.9")
        self.assertAlmostEqual(results[0].score_value, 385.35787, places=5)
        self.assertAlmostEqual(results[0].resident_estimated_amount, round(385.35787 * 92.5, 2), places=2)
        self.assertAlmostEqual(results[0].employee_estimated_amount, round(385.35787 * 105.0, 2), places=2)

    def test_keyword_query_returns_matches(self) -> None:
        results = self.service.search("细菌性痢疾", resident_point_value=None, employee_point_value=None)
        self.assertTrue(results)
        self.assertIn("细菌性痢疾", results[0].name)
        self.assertIsNone(results[0].resident_estimated_amount)
        self.assertIsNone(results[0].employee_estimated_amount)


if __name__ == "__main__":
    unittest.main()
