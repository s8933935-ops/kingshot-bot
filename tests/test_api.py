"""
FastAPIバックエンドの結合・単体テスト
"""

import unittest
from fastapi.testclient import TestClient
from src.api.main import app


class TestInvestKeibaAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_root_frontend_delivery(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("QuantTrade", res.text)

    def test_race_card_endpoint(self):
        res = self.client.get("/api/race-card?symbol=GC=F")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["symbol"], "GC=F")
        self.assertIn("ai_mark", data)
        self.assertIn("prob_up_pct", data)
        self.assertIn("paddock_comment", data)

    def test_leaderboard_endpoint(self):
        res = self.client.get("/api/leaderboard?sort_by=payout_rate_pct")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

    def test_races_endpoint(self):
        res = self.client.get("/api/races")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 4)

    def test_chart_endpoint(self):
        res = self.client.get("/api/chart/GC=F")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["symbol"], "GC=F")
        self.assertIn("candles", data)
        self.assertGreater(len(data["candles"]), 50)

    def test_public_portfolio_endpoint(self):
        res = self.client.get("/api/leaderboard/tanaka/portfolio")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("user_name", data)
        self.assertIn("open_positions", data)

    def test_register_and_trade_flow(self):
        # 1. ユーザー登録
        user_id = "test_trader_99"
        res_reg = self.client.post(f"/api/register?user_id={user_id}&user_name=テスト投資家99")
        self.assertEqual(res_reg.status_code, 200)

        # 2. 口座確認
        res_acc = self.client.get(f"/api/account/{user_id}")
        self.assertEqual(res_acc.status_code, 200)
        acc_data = res_acc.json()
        self.assertEqual(acc_data["stats"]["equity"], 10_000_000.0)

        # 3. 注文
        order_payload = {
            "user_id": user_id,
            "symbol": "GC=F",
            "side": "BUY",
            "amount": 5.0,
            "leverage": 1.0
        }
        res_order = self.client.post("/api/order", json=order_payload)
        self.assertEqual(res_order.status_code, 200)
        order_res = res_order.json()
        self.assertEqual(order_res["status"], "ORDER_FILLED")
        pos_id = order_res["position_id"]

        # 4. 口座再確認（ポジションが存在すること）
        res_acc2 = self.client.get(f"/api/account/{user_id}")
        self.assertEqual(len(res_acc2.json()["positions"]), 1)

        # 5. 決済
        close_payload = {
            "user_id": user_id,
            "position_id": pos_id
        }
        res_close = self.client.post("/api/close", json=close_payload)
        self.assertEqual(res_close.status_code, 200)
        self.assertEqual(res_close.json()["status"], "POSITION_CLOSED")


if __name__ == "__main__":
    unittest.main()
