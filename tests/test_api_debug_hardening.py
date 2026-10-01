import unittest
from fastapi.testclient import TestClient
from src.api.main import app


class TestApiDebugHardening(unittest.TestCase):
    """専門デバッグチームによるAPI堅牢化・バリデーション検証テスト"""

    def setUp(self):
        self.client = TestClient(app)

    def test_chart_invalid_period(self):
        res = self.client.get("/api/chart/GC=F?period=999y&interval=1d")
        self.assertEqual(res.status_code, 400)
        self.assertIn("無効な period", res.json()["detail"])

    def test_chart_invalid_interval(self):
        res = self.client.get("/api/chart/GC=F?period=1y&interval=999h")
        self.assertEqual(res.status_code, 400)
        self.assertIn("無効な interval", res.json()["detail"])

    def test_order_invalid_side_rejected(self):
        res = self.client.post("/api/order", json={
            "user_id": "tanaka",
            "symbol": "GC=F",
            "side": "INVALID_SIDE",
            "amount": 10.0,
            "leverage": 1.0
        })
        self.assertEqual(res.status_code, 422)

    def test_autopilot_invalid_strategy_rejected(self):
        res = self.client.post("/api/autopilot/toggle", json={
            "user_id": "tanaka",
            "is_active": True,
            "allocated_capital": 3000000.0,
            "daily_max_loss_pct": 3.0,
            "strategy_style": "super_gamble_unknown"
        })
        self.assertEqual(res.status_code, 422)

    def test_zero_leakage_audit_endpoint(self):
        res = self.client.get("/api/audit/zero-leakage")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(len(data["invariants"]), 5)

    def test_autopilot_tick_endpoint(self):
        res = self.client.post("/api/autopilot/tick?user_id=tanaka&symbol=GC=F")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("action_taken", data)
        self.assertIn("status", data)


if __name__ == "__main__":
    unittest.main()
