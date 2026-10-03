"""
為替換算（USD/JPY）および実市場アンカー固定・Ornstein-Uhlenbeck平均回帰Tickのテストスイート
"""
import unittest
from pathlib import Path
from src.invest_engine.virtual_broker import VirtualAccount, Position, QUOTE_CURRENCIES
from src.invest_engine.game_manager import InvestmentGameManager
from src.invest_engine.history_db import init_db, save_trade_record, clear_user_trades, get_completed_trades


class TestFXConversionAndMarketAnchor(unittest.TestCase):

    def setUp(self):
        self.account = VirtualAccount(user_id="test_fx_user", user_name="FX Test User", initial_cash=10_000_000.0)
        self.account.latest_usd_jpy = 150.0  # 為替レートを 150.0 円/ドル に固定してテスト

    def test_usd_symbol_margin_and_pnl_conversion(self):
        """USD建て銘柄（GC=F）の証拠金・損益が為替レート（USD/JPY）で正しく円換算されることを検証"""
        symbol = "GC=F"
        entry_price = 4000.0  # 4000 ドル/oz
        amount = 1.0          # 1 オンス
        leverage = 1.0

        # 想定金額: 4000 USD * 150 JPY/USD = 600,000 円
        # 手数料 (0.03%): 600,000 * 0.0003 = 180 円
        initial_cash = self.account.cash
        pos = self.account.open_position(symbol, "BUY", entry_price, amount, leverage=leverage)

        self.assertEqual(pos.quote_currency, "USD")
        self.assertEqual(pos.fx_rate, 150.0)
        expected_fee = (4000.0 * 1.0 * 150.0) * self.account.fee_rate
        self.assertAlmostEqual(self.account.cash, initial_cash - expected_fee, places=2)

        # 価格が 4000 USD -> 4100 USD (+100 ドル) に上昇
        self.account.update_market_price(symbol, 4100.0)
        # 含み損益 (USD): +100 USD
        self.assertAlmostEqual(pos.unrealized_pnl_quote, 100.0, places=2)
        # 含み損益 (JPY): +100 USD * 150 JPY/USD = +15,000 円
        self.assertAlmostEqual(pos.unrealized_pnl, 15000.0, places=2)

        # 決済
        trade = self.account.close_position(pos.position_id, 4100.0)
        # 確定粗利益: 15,000 円
        self.assertAlmostEqual(trade.gross_pnl, 15000.0, places=2)
        self.assertAlmostEqual(trade.gross_pnl_quote, 100.0, places=2)
        self.assertEqual(trade.fx_rate, 150.0)

    def test_jpy_symbol_no_double_conversion(self):
        """日本円建て銘柄（USDJPY=X）は為替換算が 1.0 倍であることを検証"""
        symbol = "USDJPY=X"
        self.assertEqual(self.account.get_fx_rate(symbol), 1.0)
        pos = self.account.open_position(symbol, "BUY", 150.0, amount=1000.0, leverage=1.0)
        self.assertEqual(pos.quote_currency, "JPY")
        self.assertEqual(pos.fx_rate, 1.0)

    def test_ou_mean_reversion_prevents_exponential_drift(self):
        """Ornstein-Uhlenbeck平均回帰Tickにより、数百回Tickしてもアンカー価格から乖離・発散しないことを検証"""
        gm = InvestmentGameManager()
        # アンカーを 4000.0 に設定
        gm.anchor_prices["GC=F"] = 4000.0
        gm.live_prices["GC=F"] = 4000.0

        # 300回連続でTickを実行
        for _ in range(300):
            gm.tick_market()

        final_price = gm.live_prices["GC=F"]
        # ハードリミットにより、アンカー (4000.0) の ±1.0% (3960 〜 4040) の範囲内に厳格に収まること
        self.assertGreaterEqual(final_price, 4000.0 * 0.990)
        self.assertLessEqual(final_price, 4000.0 * 1.010)

    def test_fx_rate_propagation_to_positions(self):
        """USDJPYの価格変動が即座にユーザーポジションの fx_rate および円換算評価額へ伝搬することを検証"""
        gm = InvestmentGameManager()
        user = gm.register_user("prop_test_user", "Prop Test")
        pos = user.open_position("GC=F", "BUY", 4000.0, amount=1.0)

        # USDJPY が 155.0 -> 160.0 に円安進行
        user.update_market_price("USDJPY=X", 160.0)
        self.assertEqual(user.latest_usd_jpy, 160.0)
        self.assertEqual(pos.fx_rate, 160.0)

    def test_clear_user_trades(self):
        """DBから特定ユーザーの不正履歴が完全に消去されることを検証"""
        test_db = Path("data/test_audit_clean.db")
        init_db(test_db)
        save_trade_record(
            user_id="bad_user",
            trade={
                "trade_id": "bad_001",
                "symbol": "GC=F",
                "side": "BUY",
                "entry_price": 4000.0,
                "exit_price": 5000.0,
                "amount": 10.0,
                "leverage": 1.0,
                "gross_pnl": 1500000.0,
                "fee": 0.0,
                "net_pnl": 1500000.0,
                "return_pct": 25.0
            },
            source="AUTOPILOT",
            db_path=test_db
        )

        records_before = get_completed_trades(user_id="bad_user", limit=10, db_path=test_db)
        self.assertEqual(len(records_before), 1)

        clear_user_trades("bad_user", db_path=test_db)
        records_after = get_completed_trades(user_id="bad_user", limit=10, db_path=test_db)
        self.assertEqual(len(records_after), 0)

        if test_db.exists():
            test_db.unlink()


if __name__ == "__main__":
    unittest.main()
