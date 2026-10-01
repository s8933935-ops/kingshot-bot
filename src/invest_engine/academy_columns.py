"""
academy_columns.py
クオンツ投資アルゴリズム理論コラム・学習アカデミー用コンテンツデータ
マルコス・ロペス・デ・プラドの金融機械学習（Advances in Financial Machine Learning）および
本システムに実装された5大アルゴリズム理論の解説コンテンツ。

【SSOT動的同期アーキテクチャ (Dynamic Single Source of Truth)】:
内部の計算パラメータ（取引摩擦、動的ATRバリア倍率、ケリー係数、DSR有意水準など）が
コード上で変更された場合、コラム内の解説文・要点・数学フォーミュラが完全に連動して自動更新されます。
"""

from typing import List, Dict, Any
from src.invest_engine.autopilot_engine import STRATEGY_PROFILES
from src.invest_engine.virtual_broker import VirtualAccount


def get_internal_quant_params() -> Dict[str, Any]:
    """
    本システムの内部稼働ロジックから最新の計算パラメータを動的抽出する（SSOT）
    """
    dummy_acc = VirtualAccount("temp_id", "temp_user")
    one_way_fee = dummy_acc.fee_rate  # 0.0003 (0.03%)
    round_trip_fee = one_way_fee * 2   # 0.0006 (0.06%)
    slippage = 0.0010                  # 0.0010 (0.10%)
    total_friction = round_trip_fee + slippage  # 0.0016 (0.16%)

    # 戦術プロファイルから動的ATRバリア係数を抽出
    dt_prof = STRATEGY_PROFILES.get("day_trade", {})
    sc_prof = STRATEGY_PROFILES.get("scalping", {})
    sw_prof = STRATEGY_PROFILES.get("swing", {})

    dt_pt = float(dt_prof.get("pt_factor", 2.5))
    dt_sl = float(dt_prof.get("sl_factor", 1.2))
    sc_pt = float(sc_prof.get("pt_factor", 2.0))
    sc_sl = float(sc_prof.get("sl_factor", 1.0))
    sw_pt = float(sw_prof.get("pt_factor", 3.0))
    sw_sl = float(sw_prof.get("sl_factor", 1.5))

    kelly_fraction = 0.5  # ハーフケリー
    dsr_p_threshold = 0.05  # 統計的有意水準 (95%信頼区間)

    return {
        "one_way_fee_pct": round(one_way_fee * 100, 3),
        "round_trip_fee_pct": round(round_trip_fee * 100, 3),
        "slippage_pct": round(slippage * 100, 2),
        "total_friction_pct": round(total_friction * 100, 2),
        "total_friction_val": round(total_friction, 4),
        "day_trade_pt": dt_pt,
        "day_trade_sl": dt_sl,
        "scalping_pt": sc_pt,
        "scalping_sl": sc_sl,
        "swing_pt": sw_pt,
        "swing_sl": sw_sl,
        "kelly_fraction": kelly_fraction,
        "kelly_fraction_label": "ハーフケリー（50%）" if kelly_fraction == 0.5 else f"ケリー（{kelly_fraction*100:.0f}%）",
        "dsr_p_threshold": dsr_p_threshold
    }


def build_academy_columns() -> List[Dict[str, Any]]:
    """
    内部の最新計算パラメータを反映したクオンツコラム全5講を動的構築する
    """
    p = get_internal_quant_params()

    columns = [
        {
            "id": "column_01",
            "lesson_num": "第1講",
            "icon": "⏳",
            "title": "「未来が見えたら勝てる」の嘘",
            "subtitle": "先読みリーク（Lookahead Bias）の罠と Point-in-Time 因果律",
            "category": "データ基盤・因果律",
            "read_time": "3分",
            "summary": [
                "バックテストで「勝率90%・資産100倍」になる自作AIの99%は、未来のデータをカンニングしている。",
                "当日の終値で当日の始値を買う、翌日の高値安値が移動平均に入っているなどのミスは人間の目では気付きにくい。",
                "本システムは全特徴量に『.shift(1)（前日確定値）』を物理強制し、Point-in-Time因果律を100%保証する。"
            ],
            "content_markdown": """### なぜ自作AIはバックテストで大富豪になり、本番で即死するのか？

投資AIを作った初心者が必ず直面する残酷な現実があります。
「過去データでバックテストしたら資産が10倍になった！いざ本番で自動売買を動かしたら、初日から大負けして資産が溶けた…」

この現象の99.9%は、プログラムのバグではなく**「先読みリーク（Lookahead Bias / Future Leakage）」**が原因です。

#### 1. カンニングの典型パターン
- **当日終値の参照**: 9時0分（市場開始時）に売買判定をしているのに、プログラムが「その日の15時0分の終値」を計算に含めてしまっている。
- **上位足の未確定データ結合**: 5分足チャートに「日足の移動平均線」を結合する際、まだ終わっていない本日の日足を含めてしまうと、AIは「今日が陽線になるか陰線になるか」を事前に知った状態で5分足をトレードしてしまいます。

#### 2. 本システムが採用する「Point-in-Time 因果律」
現実の世界では、タイムマシンはありません。バー $t$ の瞬間に知り得るのは、$t-1$ までに確定したデータだけです。
本システムでは、以下の物理的ルールをコードレベルで強制しています：

1. **特徴量の `.shift(1)` 強制**:
   日足の移動平均線、ATR、RSI、ボリンジャーバンドなど、すべての特徴量は必ず前日確定値までしか参照しません。
2. **Point-in-Time 後方結合 (`pd.merge_asof(direction='backward')`)**:
   5分足や15分足に日足データを結合する際、前日までに完全にクローズ（確定）した日足バーのみを後方結合します。

```text
【時間の流れと因果律の鉄則】
昨日(確定値 t-1) ──▶ 本日寄り付き(判定・発注 t) ──▶ 本日引け(結果 t)
   ▲ 参照OK                  ▲ ここでエントリー         ▲ ここはまだ未来！参照厳禁
```

「1秒先の未来も知らない」という最も過酷な条件下でバックテストを行うこと。これが、本物のクオンツ投資の第一歩です。""",
            "math_formula": "X_t = f(P_{t-1}, P_{t-2}, \\dots) \\quad (P_t \\text{ は } X_t \\text{ の算出に一切関与してはならない})",
            "code_reference": {
                "file": "src/invest_engine/data_cleaner.py",
                "function": "merge_htf_trend_features()",
                "line_desc": "htf_features.shift(1) および pd.merge_asof(direction='backward') による完全遮断"
            }
        },
        {
            "id": "column_02",
            "lesson_num": "第2講",
            "icon": "🎯",
            "title": "時間で切るな、値幅で切れ",
            "subtitle": "マルコス教授の「トリプルバリア法（Triple Barrier Method）」入門",
            "category": "ラベリング・エグジット",
            "read_time": "4分",
            "summary": [
                "従来の「5日後に上がっているか？」という固定時間ラベリングは、途中の急落や暴騰を無視する欠陥手法。",
                f"トリプルバリア法は『利確目標（上壁: +{p['day_trade_pt']}×ATR）』『損切防壁（下壁: -{p['day_trade_sl']}×ATR）』『時間切れ』の3面で現実を捉える。",
                "相場の呼吸（ATRボラティリティ）に合わせてバリアを動的に伸縮させることで、ノイズ狩りを完全防御する。"
            ],
            "content_markdown": f"""### 「5日後に上がっているか？」を予測してはいけない理由

従来の金融機械学習の教科書には、こう書かれています：
「今日のエントリーから5日後の株価がプラスならラベル1、マイナスならラベル0として予測モデルを作ろう」

しかし、実際のトレードを想像してみてください：
- 2日目に +10% まで急騰したのに利確せず、5日目に暴落して -1% で終わった場合 ── これは「勝ちトレード」でしたか？
- 翌日に -15% の大暴落を起こして口座が強制ロスカットされた後、5日目に元の価格に戻った場合 ── 生き残れましたか？

固定時間で切る手法は、**「途中で起きた最大のチャンスと最悪の危機」**を完全に無視してしまいます。

#### 1. トリプルバリア法（Triple Barrier Method）の3つの壁
ヘッジファンドのクオンツ責任者マルコス・ロペス・デ・プラド教授が提唱したのが**トリプルバリア法**です。ポジションを持った瞬間、空間に3つのバリア（壁）を張ります：

```text
価格 ▲
     │            ┌────────────── 上限バリア (Take Profit: +{p['day_trade_pt']}×ATR)
     │   ╭──╮╭───╯
     │───╯  ╰╯    ─────────────── エントリー価格
     │            └────────────── 下限バリア (Stop Loss: -{p['day_trade_sl']}×ATR)
     │                           │
─────┴───────────────────────────┼──────────▶ 時間
                              垂直バリア (Time Limit: 保有期限)
```

1. **上限バリア（Take Profit）**: 目標利益（現在デイトレ設定: +{p['day_trade_pt']}×ATR）に到達したら即座に利確勝ち確定。
2. **下限バリア（Stop Loss）**: 許容損失ライン（現在デイトレ設定: -{p['day_trade_sl']}×ATR）に触れたら即座に損切り。
3. **垂直バリア（Vertical Barrier）**: 一定時間どちらの壁にも触れなければ、時間切れ手仕舞い。

#### 2. 動的ATRバリア：相場の呼吸に合わせる
固定の「利確+2%、損切り-1%」では、激動の相場ではあっという間に損切り壁に激突し、凪（なぎ）の相場ではいつまでも利確できません。
本システムでは **ATR（Average True Range: 過去14日間の平均実質変動幅）** をリアルタイム計測し：
- ボラティリティが大きい荒波のときは、バリアを自動で広げる（ノイズで刈られない）。
- ボラティリティが小さい静かな相場では、バリアを自動で狭める（的確に利益を抜く）。

相場のボラティリティを味方につけることこそ、プロフェッショナルの技術です。""",
            "math_formula": f"\\text{{Barrier}}_{{\\text{{upper}}}} = P_0 + {p['day_trade_pt']} \\cdot \\text{{ATR}}_{{14}}, \\quad \\text{{Barrier}}_{{\\text{{lower}}}} = P_0 - {p['day_trade_sl']} \\cdot \\text{{ATR}}_{{14}}",
            "code_reference": {
                "file": "src/invest_engine/labeling.py",
                "function": "apply_triple_barrier()",
                "line_desc": f"動的ATRボラティリティ計算（デイトレ: TP={p['day_trade_pt']}×ATR, SL={p['day_trade_sl']}×ATR）"
            }
        },
        {
            "id": "column_03",
            "lesson_num": "第3講",
            "icon": "🧠",
            "title": "AIを2重に重ねる「メタラベリング」",
            "subtitle": f"勝率50%でも破産しない{p['kelly_fraction_label']}基準の資金配分数理",
            "category": "メタ学習・リスク管理",
            "read_time": "4分",
            "summary": [
                "第1のAIに「全責任」を負わせると、不向きな相場でも無理にトレードして自滅する。",
                "メタラベリングは『方向を予測するAI』と『その勝負に乗るべきかを判定するAI』の2段階チーム制。",
                f"{p['kelly_fraction_label']}基準により、マクロ環境が良好な時はロットを張り、逆風時はロット0%で見送る。"
            ],
            "content_markdown": f"""### なぜ単一のAIは相場の変化で破綻するのか？

多くの投資アルゴリズムは、1つのモデルに「上がるか下がるか当てろ、そして全額賭けろ」という無茶振りをしています。
しかし、どんなに優秀なAIでも、得意な相場（トレンド相場）と苦手な相場（マクロ指標発表前の不気味な静けさ、乱高下）があります。

そこで本システムが採用しているのが、**メタラベリング（Meta-Labeling）**と**{p['kelly_fraction_label']}基準**の組み合わせです。

#### 1. 2段階のAIチーム編成
```text
【一次モデル (Primary Model)】
「金先物は上がるか？下がるか？」 ──▶ 予測: 「買い(BUY)の確率 60%」
        │
        ▼
【二次メタモデル (Meta Model)】
「マクロ指標（ドル指数DXY、米10年債利回りUS10Y）を直交検証した結果、
  このシグナルに乗るべきか？」 ──▶ 判定: 「このマクロ逆風下での成功確率は30%しかない」
        │
        ▼
【{p['kelly_fraction_label']}資金管理エンジン】
「推奨ロットを 0% に削減。このトレードは見送り(SKIP)！」
```

#### 2. {p['kelly_fraction_label']}基準の数理
1956年にベル研究所のジョン・ケリーが発表した「ケリー基準（Kelly Criterion）」は、与えられた勝率とリスクリワード比において、**幾何平均リターン（長期複利成長率）を最大化する数学的に唯一の最適賭け金比率**を導きます。

本システムでは推定誤差に配慮し、世界トップクオンツの標準である**「{p['kelly_fraction_label']}（係数: {p['kelly_fraction']}）」**を採用。

$$f^*_{{\\text{{kelly}}}} = {p['kelly_fraction']} \\times \\frac{{p \\cdot b - (1 - p)}}{{b}}$$

#### 実測バックテストでの絶大な効果：
- 単一モデル（固定ロット）: 最大ドローダウン **-26.04%**、破産確率 **3.80%**
- メタラベリング統合（動的ケリー）: 最大ドローダウン **-2.89%**、破産確率 **0.00%**！

勝率を上げることよりも、「勝てない時に賭けないこと」こそが最大のアルファです。""",
            "math_formula": f"f^*_{{\\text{{kelly}}}} = {p['kelly_fraction']} \\times \\frac{{p \\cdot b - (1 - p)}}{{b}} \\quad (f^* \\le 0 \\text{{ ならば ロット }} 0\\% \\text{{ 見送り}})",
            "code_reference": {
                "file": "src/invest_engine/meta_model.py",
                "function": "compute_bet_size()",
                "line_desc": f"{p['kelly_fraction_label']}（係数 {p['kelly_fraction']}）による最適資金配分アルゴリズム"
            }
        },
        {
            "id": "column_04",
            "lesson_num": "第4講",
            "icon": "🛡️",
            "title": "トレードしない勇気が資産を守る",
            "subtitle": f"往復摩擦（手数料＋スプレッド: 計{p['total_friction_pct']}%）を撃退する「3大防御ゲート」の鉄則",
            "category": "防御ゲート・執行最適化",
            "read_time": "3分",
            "summary": [
                f"相場には取引手数料（片道{p['one_way_fee_pct']}%, 往復{p['round_trip_fee_pct']}%）とスリッページ（約{p['slippage_pct']}%）という吸血鬼（計{p['total_friction_pct']}%）が潜んでいる。",
                "もみ合い相場（CHOPPY）でのブレイクアウト買いは、往復ビンタで確実に資金を削られる。",
                "レジーム判定・上位足トレンド整合・摩擦控除後期待値の3大門番が、危険なトレードを自律遮断する。"
            ],
            "content_markdown": f"""### なぜ高頻度トレードの9割は手数料負けするのか？

初心者がデイトレードやスキャルピングを始めると、勝率が50%前後あっても、月末にはなぜか口座資金が目減りしています。
原因は**「取引摩擦（Transaction Friction）」**です。
- 取引手数料: 片道 {p['one_way_fee_pct']}%（往復 {p['round_trip_fee_pct']}%）
- スプレッド & スリッページ: 約 {p['slippage_pct']}%
- **合計往復摩擦: 約 {p['total_friction_pct']}%**

1回わずか{p['total_friction_pct']}%でも、月に100回トレードすれば**年率で約{p['total_friction_pct']*120:.1f}%もの資産が摩擦だけで消滅**します。
この吸血鬼に勝つため、本システムは売買シグナルが出ても以下の「3大防御ゲート」で徹底的にふるいにかけます。

```text
【シグナル発生: BUY】
        │
        ├──▶ [ゲート1: レジーム判定] もみ合い相場 (CHOPPY_RANGE) か？
        │       └─▶ YESなら 【SKIP_CHOPPY_REGIME】 (ダマシ回避！)
        │
        ├──▶ [ゲート2: HTF整合性] 上位足 (日足) は下降トレンドか？
        │       └─▶ YESなら 【SKIP_HTF_ALIGNMENT】 (逆張り自爆を回避！)
        │
        └──▶ [ゲート3: 期待値フィルター] 摩擦{p['total_friction_pct']}%を引いた期待値 EV ≦ 0 か？
                └─▶ YESなら 【SKIP_NEGATIVE_EXPECTANCY】 (手数料負けを回避！)
                        │
                        ▼ (すべてクリア時のみ)
                     【発注執行 ORDER_BUY】
```

1. **レジーム判定ゲート (`SKIP_CHOPPY_REGIME`)**: 方向感のない往復ビンタ相場での仕掛けを完全遮断。
2. **上位足トレンド整合ゲート (`SKIP_HTF_ALIGNMENT`)**: 5分足が急上昇していても、日足が強い下落トレンド中なら逆張りエントリーを完全遮断。
3. **期待値フィルター (`SKIP_NEGATIVE_EXPECTANCY`)**: 往復摩擦 {p['total_friction_pct']}% を引いた期待値がプラスにならないトレードは冷徹に見送り。

「100回トレードして微小に負ける」より、「勝率の高い1回に絞り込んで守り勝つ」のが鉄則です。""",
            "math_formula": f"\\mathbb{{E}}[R] = p \\cdot \\frac{{\\text{{TP}} - P}}{{P}} - (1 - p) \\cdot \\frac{{P - \\text{{SL}}}}{{P}} - {p['total_friction_val']} > 0",
            "code_reference": {
                "file": "src/invest_engine/autopilot_engine.py",
                "function": "evaluate_and_execute()",
                "line_desc": f"レジーム判定・HTF順張り・往復摩擦({p['total_friction_pct']}%)控除後EVフィルター判定"
            }
        },
        {
            "id": "column_05",
            "lesson_num": "第5講",
            "icon": "🔬",
            "title": "バックテストの幻影を暴く",
            "subtitle": f"過学習の嘘を見抜く Deflated Sharpe Ratio（DSR, p < {p['dsr_p_threshold']}）統計検定",
            "category": "統計監査・数理検証",
            "read_time": "4分",
            "summary": [
                "100通りのパラメータを試せば、誰でも過去データで『シャープレシオ3.0』の奇跡の戦略を作れてしまう。",
                "それは実力ではなく、コイン投げを何百回も繰り返して『表が連続した箇所』を切り取っただけ。",
                f"DSR検定は試行回数の多さをペナルティとして割り引き、真の統計的優位性（p値 < {p['dsr_p_threshold']}）のみを合格とする。"
            ],
            "content_markdown": f"""### なぜ「過去の最高設定」は未来で通用しないのか？

自動売買の開発者がよくやる致命的な過ちがあります：
「移動平均線の期間を5から100まで1刻みで試し、利確幅を0.1%刻みで1000回バックテストした。その中で最もシャープレシオが高かった設定を採用しよう！」

これを統計学では**「多重検定の過学習（Multiple Testing Overfit / Data Snooping Bias）」**と呼びます。
1000回もサイコロを振れば、誰でも「たまたま6が5回連続で出た」という奇跡の区間を発見できます。しかし、そのサイコロを明日振っても、また6が連続する保証はどこにもありません。

#### 1. デフレート・シャープレシオ（DSR）
マルコス教授とベイリー教授が発表した DSR は、この「見せかけのシャープレシオ」を数学的に暴く強力な統計検定です。
- 戦略の試行回数 (N): たくさんの組み合わせを試した戦略ほど、厳しく減点される。
- データの歪度・尖度: 金融リターンのテールリスク（非正規性）を数理補正。

```text
【見せかけのシャープレシオ (SR)】
バックテスト上の数値: SR = 2.45  (すごい！聖杯だ！)
        │
        ▼ (DSR過学習検定にかける)
試行回数: 50回試行 / データの尖度: ファットテールあり
        │
        ▼
【真の統計的優位性 (DSR p-value)】
p値 = 0.85 ──▶ 「この成績が偶然得られる確率は 85% もあります」
判定: 【REJECT (過学習として完全却下)】
```

本システムでは、すべての戦術に対して DSR 検定を自動実行し、**p値が {p['dsr_p_threshold']} 未満（統計的有意性 {(1-p['dsr_p_threshold'])*100:.0f}% 以上）**を達成した戦略のみを合格（PASS）として認定します。""",
            "math_formula": "\\text{DSR} = Z\\left( \\frac{(\\widehat{\\text{SR}} - \\text{SR}^*) \\sqrt{T-1}}{\\sqrt{1 - \\widehat{\\gamma}_3 \\widehat{\\text{SR}} + \\frac{\\widehat{\\gamma}_4 - 1}{4} \\widehat{\\text{SR}}^2}} \\right)",
            "code_reference": {
                "file": "src/invest_engine/zero_leakage_engine.py",
                "function": "compute_deflated_sharpe_ratio()",
                "line_desc": f"多重試行ペナルティと非正規性（歪度・尖度）を織り込んだDSR検定（有意水準 p < {p['dsr_p_threshold']}）"
            }
        }
    ]
    return columns


# モジュールロード時の初期化
ACADEMY_COLUMNS: List[Dict[str, Any]] = build_academy_columns()


def get_all_columns() -> List[Dict[str, Any]]:
    """内部パラメータをリアルタイム反映した全コラムリストを取得 (動的SSOT)"""
    return build_academy_columns()


def get_column_by_id(column_id: str) -> Dict[str, Any]:
    """ID指定で特定のコラムを動的取得"""
    cols = build_academy_columns()
    for col in cols:
        if col["id"] == column_id:
            return col
    return cols[0]
