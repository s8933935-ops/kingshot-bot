"""
口座リセット、AI戦略即時同期、および実運用ログからの自己学習（再学習データセット抽出）テスト
"""

import unittest
from fastapi.testclient import TestClient
from src.api.main import app, game_manager


class TestResetAndRetrain(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.user_id = "test_reset_user"
        game_manager.register_user(self.user_id, "テストリセット君", preload_samples=False)

    def test_account_reset_endpoint(self):
        """口座資金リセットが正常に動き、残高1000万円・ポジション0に戻ることを検証"""
        acc = game_manager.get_user(self.user_id)
        # 一旦ポジションを持たせる
        acc.open_position("GC=F", "BUY", 4000.0, 10.0)
        self.assertEqual(len(acc.positions), 1)

        # リセットAPI呼び出し
        res = self.client.post("/api/account/reset", json={"user_id": self.user_id, "initial_cash": 10000000.0})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ACCOUNT_RESET_SUCCESS")
        self.assertEqual(data["cash"], 10000000.0)
        self.assertEqual(len(acc.positions), 0)
        self.assertEqual(len(acc.limit_orders), 0)

    def test_autopilot_set_strategy_endpoint(self):
        """AI戦略スタイルが即座に更新され、ポーリング上書きされないことを検証"""
        res = self.client.post("/api/autopilot/set-strategy", json={"user_id": self.user_id, "strategy_style": "swing"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "STRATEGY_SET_SUCCESS")
        self.assertEqual(data["strategy_style"], "swing")

        # ステータスAPIでもswingが維持されていること
        status_res = self.client.get(f"/api/autopilot/status/{self.user_id}")
        self.assertEqual(status_res.status_code, 200)
        self.assertEqual(status_res.json()["strategy_style"], "swing")

    def test_retrain_from_history_endpoint(self):
        """蓄積されたトレードログから自己学習データセットが抽出できることを検証"""
        res = self.client.post("/api/retrain-from-history")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "RETRAIN_EVALUATED")
        self.assertIn("total_samples", data)
        self.assertIn("win_rate_pct", data)
