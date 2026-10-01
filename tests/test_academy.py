"""
test_academy.py
クオンツ投資アルゴリズム理論コラム・学習アカデミーAPIおよびデータ構造の単体テスト
"""

import unittest
from fastapi.testclient import TestClient

from src.invest_engine.academy_columns import get_all_columns, get_column_by_id, ACADEMY_COLUMNS
from src.api.main import app


class TestAcademyColumns(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_academy_columns_data_integrity(self):
        """全5講のコラムデータが存在し、必須フィールドが揃っていることを検証"""
        cols = get_all_columns()
        self.assertEqual(len(cols), 5)

        required_keys = [
            "id", "lesson_num", "icon", "title", "subtitle",
            "category", "read_time", "summary", "content_markdown",
            "math_formula", "code_reference"
        ]

        for col in cols:
            for key in required_keys:
                self.assertIn(key, col, f"キー '{key}' がコラム {col.get('id')} に存在しません")
            self.assertTrue(len(col["summary"]) >= 2, f"コラム {col['id']} の要点が不足しています")
            self.assertIn("file", col["code_reference"])
            self.assertIn("function", col["code_reference"])

    def test_get_column_by_id(self):
        """特定のコラムID取得およびフォールバック動作を検証"""
        col1 = get_column_by_id("column_01")
        self.assertEqual(col1["id"], "column_01")
        self.assertIn("Point-in-Time", col1["subtitle"])

        # 存在しないIDの場合は先頭のコラムにフォールバック
        col_fallback = get_column_by_id("non_existent_id")
        self.assertEqual(col_fallback["id"], "column_01")

    def test_api_academy_columns_list(self):
        """GET /api/academy/columns API のレスポンスを検証"""
        response = self.client.get("/api/academy/columns")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("columns", data)
        self.assertEqual(len(data["columns"]), 5)
        self.assertEqual(data["columns"][0]["id"], "column_01")
        self.assertEqual(data["columns"][1]["id"], "column_02")

    def test_api_academy_column_detail(self):
        """GET /api/academy/columns/{column_id} API のレスポンスを検証"""
        response = self.client.get("/api/academy/columns/column_03")
        self.assertEqual(response.status_code, 200)
        col = response.json()
        self.assertEqual(col["id"], "column_03")
        self.assertIn("メタラベリング", col["title"])
        self.assertIn("ハーフケリー", col["subtitle"])


if __name__ == "__main__":
    unittest.main()
