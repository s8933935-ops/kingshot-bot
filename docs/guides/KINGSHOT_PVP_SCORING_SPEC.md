# KingShot / 聖剣の戦い PvP 2軸評価仕様書（SSOT）

- **制定日**: 2026-11-14
- **数理設計**: Claude Opus 5 (`claude-opus-5`)
- **実装正本スクリプト**: [scripts/pvp_two_axis_scorer.py](../../scripts/pvp_two_axis_scorer.py)
- **検証テスト**: [tests/test_pvp_two_axis_scorer.py](../../tests/test_pvp_two_axis_scorer.py)

---

## 0. 設計原則（なぜ軽量モデルでも 100% 再現できるのか）

KingShot の対人戦力（特に聖剣の戦い / KvK 王城戦）は、総戦力（兵隊水増し＝兵隊デブ）や単純な合算MT・キル数で測ると実戦を見誤る。本仕様はアカウントの戦闘能力を **互いに直交する 2軸** に分離し、固定定数と閉じた数式で定義する：

| 軸 | 名称 | レンジ | 測る対象 | 排除するノイズ |
| :--- | :--- | :---: | :--- | :--- |
| **軸1** | **PCS** (`Pure Combat Quality Score`) | `0–1000` | 1兵あたりの純粋な戦闘密度・倍率 | 兵士数、建物戦力、同盟バフ |
| **軸2** | **DTV** (`Deployable Troop Volume`) | `0–100` | 総力差から推定した出撃可能兵量・兵質 | 装備・護符・英雄等の基礎倍率 |

ダメージ計算式 $\text{Kills} \propto \sqrt{N} \times \frac{\text{Attack} \times \text{Lethality}}{\text{Enemy\_Defense} \times \text{Enemy\_Health}} \times \text{SkillMod}$ において、**PCS が右側の倍率比**、**DTV が左側の動員兵数 $N$** に対応する。

> **【運用鉄則（軽量モデル／再実行時）】**
> 次回以降、軽量モデルや自動スクリプトが対戦解析を行う場合は、独自に重みや近似式を考え直さず、必ず正本スクリプト `python scripts/pvp_two_axis_scorer.py` をそのまま実行すること。

---

## 1. 入力変数（MightPulse 一覧API基準）

MightPulse API（`/api/alliances/{aid}/members`）から全メンバー分取得できる以下の最小フィールドのみを入力とする（欠損が多い `power_breakdown` / `arena_heroes` / `lords_equipments` は依存しない）：

- `power`（総戦力 → `power_M = power / 1e6`）
- `migrant_score`（移民スコア / Transfer Score）
- `stove_lv`（火炉・真金段階。未入力時は保守的に30扱い）
- `trails_list` / `trails`（秘境試練6塔の到達 `stage`）
  - `CC`: `Crystal Cave`（護符：殺傷力・体力）
  - `MF`: `Molten Fort`（領主装備：攻撃・防御）
  - `KN`: `Knowledge Nexus`（研究／技術）
  - `FoL`: `Forest of Life`（ペット）
  - `Col`: `Coliseum`（英雄・英雄装備／Widget）
  - `RS`: `Radiant Spire`（総合塔）

---

## 2. スコア1：純粋戦闘スコア `PCS`（0–1000点）

### 2.1 塔別キャップ正規化（合計MTのスケール偏り除去）
単純合計MTでは `Col`（〜765）や `RS`（〜805）が `CC`（〜376）の約2倍の数字を持つため、無加工合算だと英雄・総合塔へ実効約47%の偏りが発生する。観測最大値＋約5%ヘッドルームを固定定数 `CAP` として `0〜1` に正規化する：

```python
CAP = {"CC": 400, "MF": 440, "KN": 320, "FoL": 340, "Col": 800, "RS": 840}
n_x = clip(x / CAP[x], 0.0, 1.0)
```

### 2.2 6塔の重み配分と根拠
```python
Q_core = 0.26*n_CC + 0.18*n_MF + 0.14*n_KN + 0.08*n_FoL + 0.20*n_Col + 0.14*n_RS
```
- **CC 護符 (`26%`)**: 希少な独立乗算層（殺傷力・体力）を供給する最大ROI部位（Migrant公式シェア45.6%から飽和補正）。
- **Col 英雄 (`20%`)**: Migrant公式での重みは88（6.5%）と低いが、集結／駐屯リーダー時は英雄スキル＋専用Widget Lv.6+が全部隊へ乗るため実戦価値として意図的に上方補正。
- **MF 領主装備 (`18%`)** / **KN 研究 (`14%`)** / **RS 総合塔 (`14%`)** / **FoL ペット (`8%`)**。

### 2.3 `migrant_score` の火炉中立化＆直交ブレンド（二重計上の排除）
`migrant_score` は各塔と $r = 0.93\text{–}0.96$ で強く相関するため、そのまま足すと二重計上になる。まず火炉倍率 $\text{TC} = \min(\text{stove\_lv}, 70)$ を除算して中立化し、独立分散（$1 - r^2 \approx 9.75\%$）＋ノイズ余裕の **`12%`** のみを残差統合する：

```python
wps = migrant_score / min(stove_lv, 70) + 2226.0
nW  = clip(wps / 42000.0, 0.0, 1.0)
PCS = 1000.0 * clip(0.88 * Q_core + 0.12 * nW, 0.0, 1.0)
```

### 2.4 合流役専用スコア `PCS_joiner` / `JoinValue`
集結・駐屯で合流者（Joiner）が出せるのは **左端英雄の第1遠征スキル（上位4名まで）＋兵質（TG）＋兵数** のみのため、役割専用スコアを分岐させる：

```python
tg = clip(floor((stove_lv - 30) / 5), 1, 8)
PCS_joiner = 1000.0 * (0.45*n_Col + 0.15*n_RS + 0.10*n_CC + 0.05*n_MF + 0.25*(tg / 8.0))
JoinValue  = (PCS_joiner / 1000.0) * DTV
```

---

## 3. スコア2：出撃可能兵隊数スコア `DTV`（0–100点）

### 3.1 非線形（凹関数）ベース戦力推定
線形回帰 `TotalPower ≈ a + b × MigrantScore` で差し引くと、上位クジラほど `Power/Mig` 比が構造的に低下（護符偏重＋建物上限飽和＋`TC=70`固定）するため「兵枯渇」と誤判定される。下側エンベロープ（兵枯渇実例）への冪乗則フィッティングにより非兵士ベース戦力を推定する：

```python
BasePower_M  = 5.79 * (wps ** 0.318)
TroopPower_M = max(power_M - BasePower_M, 0.0)
phi          = TroopPower_M / power_M if power_M > 0 else 0.0
```

### 3.2 `DTV`・`FAT_WARN`・実効駐屯戦力 `EGC_M`
```python
a   = clip(math.log1p(TroopPower_M / 20.0) / math.log(31.0), 0.0, 1.0)  # 600M兵力で飽和
s   = clip((phi - 0.15) / 0.65, 0.02, 1.0)
qf  = max(1.0 - 0.04 * (8 - tg), 0.60)
DTV = 100.0 * qf * (a ** 0.6) * (s ** 0.4)

FAT_WARN = (tg <= 6 and a >= 0.70)              # Stove<=64 かつ推定兵士約201M超（兵隊デブ警戒）
EGC_M    = TroopPower_M * ((tg / 8.0) ** 2)     # TG8駐屯帯へ混入時の実効兵質換算（TG6は0.5625倍）
```

---

## 4. 4象限分類と欠損値ハンドリング（`Flag A〜D`）

### 4象限（同帯域ベンチマーク：`PCS=600`, `DTV=60` 境界）
- **A（砲台エース：`PCS ≥ 600` & `DTV ≥ 60`）**: 主力集結リーダー／防衛駐屯長
- **B（物量・合流型：`PCS < 600` & `DTV ≥ 60`）**: 合流（ジョイナー）専任。`FAT_WARN` はTG8駐屯への混入を避け同世代レーン／陽動へ分離
- **C（精鋭・兵枯渇：`PCS ≥ 600` & `DTV < 60`）**: 兵補給でAへ即昇格。未補給なら頭枠専任または占領回収
- **D（兵枯渇・要育成：`PCS < 600` & `DTV < 60`）**: 前線駐屯から外し、空拠点即時占領・輜重回収・おとり／地下貯蔵庫スプリント担当

### 信頼度フラグ `Flag`
| Flag | データ状況 | 処理方針 |
| :---: | :--- | :--- |
| **A** | 6塔・`migrant_score` 完備 | 上記数式どおり厳密計算 |
| **B** | 6塔あり／`migrant_score=null` | $\lambda=0$ で `PCS = 1000·Q_core`（+2〜4%上方バイアス注記）、$\widehat{n_W} = \operatorname{clip}(1.362\,Q_{\text{core}} - 0.306, 0, 1)$ で `DTV` 推定 |
| **C** | `migrant_score` あり／`mystic_trial=null` | $\widehat{Q_{\text{core}}} = \operatorname{clip}((n_W + 0.306)/1.362, 0, 1)$ で `PCS` 近似（`±80点` 目安注記）、`DTV` は厳密計算 |
| **D** | 両方欠損 | スコア算出不可（`D_UNSCORED`）。ただし `power_M >= 300` は「未クロール潜在主力」として別表で必ず警告表示 |

---

## 5. 定数ロック ＆ 再校正が必要になる条件

以下の条件に該当しない限り、スクリプト内の定数（`CAP`, `W`, `WPS_CAP`, `BASE_POWER_COEF`, `BASE_POWER_EXP`）は **変更禁止** とする：
1. **キャップ解放・世代交代**: ゲーム仕様で `Stove > 70`（TG9/TG10）や新塔上限開放が起き、Top 1 層が複数塔で `n_x = 1.0` に張り付いた場合。
2. **`power_breakdown` 取得可能化**: API から実兵士戦力が直接取れるようになった場合、`5.79 * wps^0.318` 推定式を実測比較で再校正する。
3. **極端に若いサーバでの利用**: `PCS=600` / `DTV=60` の固定閾値ではなく、対戦両軍の上位40%パーセンタイルを象限境界として解釈する。
