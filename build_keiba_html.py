import json

# Load base data
with open('scratch_mightpulse_top10.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Load CAT data
with open('cat_top10.json', 'r', encoding='utf-8') as f:
    cat_data = json.load(f)

# Replace or add CAT if not present
existing_kids = [d['kid'] for d in data]
if 837 not in existing_kids:
    data.append(cat_data)
else:
    for i, d in enumerate(data):
        if d['kid'] == 837 and d['abbr'] == 'CAT':
            data[i] = cat_data

# Sort by Top3 average mystic trial
data.sort(key=lambda x: x['top3_avg_mt'], reverse=True)

# Define odds, popularities, and keiba marks
marks = {
    '855': {'mark': '◎', 'mark_name': '本命', 'class': 'mark-honmei', 'odds': '1.8倍', 'ninki': '2番人気 (4,411票)', 'jockey': 'Dracfolus (3,695階)', 'stable': '王国#855 / 陣営厩舎', 'leg': '追込一閃・超破壊砲台'},
    '24K': {'mark': '◯', 'mark_name': '対抗', 'class': 'mark-taikou', 'odds': '2.1倍', 'ninki': '1番人気 (6,051票)', 'jockey': 'Niki (3,585階)', 'stable': '王国#900 / 黄金厩舎', 'leg': '先行押し切り・重厚大軍団'},
    'RYO': {'mark': '▲', 'mark_name': '単穴', 'class': 'mark-tana', 'odds': '5.4倍', 'ninki': '3番人気 (2,937票)', 'jockey': 'NomNomNom (3,226階)', 'stable': '王国#846 / 涼風厩舎', 'leg': '好位差し・一角崩し狙い'},
    'CAT': {'mark': '☆', 'mark_name': '特注穴', 'class': 'mark-ana', 'odds': '14.0倍', 'ninki': '4番人気 (291票)', 'jockey': 'Admiral Tinky (3,500階)', 'stable': '王国#837 / 単騎猫軍', 'leg': '単騎強襲・砲台一撃特化'},
    'DOM': {'mark': '△', 'mark_name': '連下', 'class': 'mark-renge', 'odds': '12.0倍', 'ninki': '5番人気 (188票)', 'jockey': 'Top1 (3,424階)', 'stable': '王国#855 / 覇王別動隊', 'leg': '援護射撃・晶塔攪乱'},
    'TOP': {'mark': '×', 'mark_name': '大穴', 'class': 'mark-ana', 'odds': '18.5倍', 'ninki': '6番人気 (162票)', 'jockey': 'Top1 (3,042階)', 'stable': '王国#850 / 兵隊巨躯', 'leg': '大逃げ粘り・兵数物量'},
    'KOR_836': {'mark': '無', 'mark_name': '見送り', 'class': 'mark-none', 'odds': '28.0倍', 'ninki': '7番人気 (106票)', 'jockey': 'Top1 (3,284階)', 'stable': '王国#836 / 虎豹騎', 'leg': '単騎強襲・層不足'},
    'KOR_841': {'mark': '無', 'mark_name': '見送り', 'class': 'mark-none', 'odds': '80.0倍', 'ninki': '8番人気 (83票)', 'jockey': 'Top1 (2,302階)', 'stable': '王国#841', 'leg': '成長途上・圏外'},
    'WET': {'mark': '無', 'mark_name': '見送り', 'class': 'mark-none', 'odds': '45.0倍', 'ninki': '9番人気 (65票)', 'jockey': 'Top1 (3,115階)', 'stable': '王国#881', 'leg': '力不足・基礎バフ劣勢'},
    'EMP': {'mark': '無', 'mark_name': '見送り', 'class': 'mark-none', 'odds': '55.0倍', 'ninki': '10番人気 (32票)', 'jockey': 'Top1 (2,959階)', 'stable': '王国#911', 'leg': '兵隊水増し・実戦難'}
}

# Generate Chart Data
labels = []
top1_data = []
top3_data = []
top10_data = []
power_data = []
kills_data = []

for d in data:
    tag = f"#{d['kid']} [{d['abbr']}]"
    labels.append(tag)
    top1_data.append(d['top1_mt'])
    top3_data.append(round(d['top3_avg_mt'], 1))
    top10_data.append(round(d['top10_avg_mt'], 1))
    power_data.append(round(d['top10_power'] / 1e9, 2))
    kills_data.append(round(d['top10_kills'] / 1e6, 1))

chart_json = {
    'labels': labels,
    'top1': top1_data,
    'top3': top3_data,
    'top10': top10_data,
    'power': power_data,
    'kills': kills_data
}

html_content = f'''<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>【東スポ・報知風】第13競技エリア(#863-#912) 炎竜の覇者(GⅠ) 徹底大予想＆オッズ分析</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --paper-bg: #f8f6f0;
      --paper-line: #222;
      --red-accent: #d32f2f;
      --gold-accent: #b78103;
      --blue-accent: #0277bd;
      --green-accent: #2e7d32;
      --text-main: #111;
      --text-muted: #555;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: #2b2b2b;
      font-family: "Hiragino Kaku Gothic ProN", "Yu Gothic", "Meiryo", sans-serif;
      color: var(--text-main);
      padding: 10px;
    }}
    .newspaper-container {{
      max-width: 1280px;
      margin: 0 auto;
      background: var(--paper-bg);
      border: 4px double #111;
      padding: 20px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.6);
    }}
    /* ヘッダー題字 */
    .header-top {{
      border-bottom: 3px solid #111;
      padding-bottom: 10px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }}
    .paper-title {{
      font-size: 2.3rem;
      font-weight: 900;
      letter-spacing: -1px;
      color: #000;
      font-family: "Impact", "Hiragino Mincho ProN", serif;
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
    }}
    .paper-title span.badge {{
      background: var(--red-accent);
      color: #fff;
      font-size: 0.95rem;
      padding: 4px 10px;
      border-radius: 4px;
    }}
    .paper-title span.area-badge {{
      background: #1a237e;
      color: #ffeb3b;
      font-size: 0.95rem;
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid #ffd600;
    }}
    .issue-info {{
      text-align: right;
      font-size: 0.85rem;
      color: var(--text-muted);
      line-height: 1.4;
    }}
    /* 特大見出し */
    .headline-box {{
      margin: 15px 0;
      border: 3px solid var(--red-accent);
      background: #fff5f5;
      padding: 15px 20px;
      position: relative;
    }}
    .headline-sub {{
      font-size: 1.05rem;
      font-weight: bold;
      color: var(--red-accent);
      margin-bottom: 5px;
    }}
    .headline-main {{
      font-size: 1.95rem;
      font-weight: 900;
      line-height: 1.35;
      color: #111;
    }}
    .headline-main em {{
      color: var(--red-accent);
      font-style: normal;
      background: linear-gradient(transparent 65%, #ffeb3b 65%);
    }}
    .lead-text {{
      margin-top: 10px;
      font-size: 0.92rem;
      line-height: 1.6;
      color: #333;
    }}

    /* 解説コールアウトボックス（推定オッズ＆人気4位CATの真実） */
    .explainer-box {{
      background: #e8f5e9;
      border: 2px solid #2e7d32;
      border-radius: 6px;
      padding: 15px;
      margin-bottom: 20px;
      font-size: 0.9rem;
      line-height: 1.6;
    }}
    .explainer-title {{
      font-size: 1.05rem;
      font-weight: 900;
      color: #1b5e20;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    /* グリッドレイアウト */
    .main-grid {{
      display: grid;
      grid-template-columns: 2fr 1fr;
      gap: 20px;
      margin-top: 20px;
    }}
    @media (max-width: 900px) {{
      .main-grid {{ grid-template-columns: 1fr; }}
      .paper-title {{ font-size: 1.7rem; }}
      .headline-main {{ font-size: 1.35rem; }}
    }}

    /* 出走表（競馬新聞テーブル） */
    .card-box {{
      background: #fff;
      border: 1px solid #bbb;
      padding: 15px;
      margin-bottom: 20px;
      box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }}
    .section-title {{
      font-size: 1.25rem;
      font-weight: 900;
      border-left: 6px solid var(--red-accent);
      padding-left: 10px;
      margin-bottom: 15px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .section-title .badge-sub {{
      font-size: 0.8rem;
      background: #222;
      color: #fff;
      padding: 3px 8px;
      border-radius: 3px;
    }}
    table.race-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.86rem;
    }}
    table.race-table th, table.race-table td {{
      border: 1px solid #ccc;
      padding: 7px 5px;
      text-align: center;
    }}
    table.race-table th {{
      background: #eee;
      font-weight: 900;
      color: #222;
    }}
    .mark-cell {{
      font-size: 1.35rem;
      font-weight: 900;
      width: 45px;
    }}
    .mark-honmei {{ color: #d32f2f; }}
    .mark-taikou {{ color: #1976d2; }}
    .mark-tana {{ color: #b78103; }}
    .mark-renge {{ color: #388e3c; }}
    .mark-ana {{ color: #7b1fa2; }}
    .mark-none {{ color: #999; font-size: 0.95rem; }}

    .alliance-cell {{
      text-align: left !important;
      font-weight: bold;
    }}
    .alliance-tag {{
      display: inline-block;
      background: #222;
      color: #ffeb3b;
      padding: 2px 5px;
      border-radius: 3px;
      font-size: 0.82rem;
      margin-right: 4px;
    }}
    .highlight-top {{
      background: #fff9c4 !important;
      font-weight: 900;
      color: #d32f2f;
    }}
    .whale-highlight {{
      color: #d32f2f;
      font-weight: bold;
    }}

    /* インフォグラフィック チャートエリア */
    .chart-container {{
      position: relative;
      margin: 15px 0;
      background: #fff;
      padding: 10px;
      border: 1px solid #ddd;
    }}

    /* 買い目・勝負馬券ボックス */
    .betting-card {{
      background: #fff8e1;
      border: 2px dashed #b78103;
      padding: 15px;
      margin-top: 15px;
      border-radius: 6px;
    }}
    .betting-title {{
      font-size: 1.15rem;
      font-weight: 900;
      color: #b78103;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .bet-row {{
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px dotted #ccc;
      font-size: 0.9rem;
    }}
    .bet-row:last-child {{ border-bottom: none; }}
    .bet-tag {{ font-weight: bold; color: #222; }}
    .bet-ret {{ font-weight: 900; color: #d32f2f; }}

    .whale-pill {{
      display: block;
      background: #ffebee;
      border: 1px solid #ef9a9a;
      border-radius: 4px;
      padding: 4px 8px;
      margin-bottom: 6px;
      font-size: 0.8rem;
      color: #c62828;
    }}
    .player-pill {{
      display: block;
      background: #f1f3f4;
      border: 1px solid #ddd;
      border-radius: 4px;
      padding: 4px 8px;
      margin-bottom: 6px;
      font-size: 0.8rem;
    }}
    .footer-note {{
      margin-top: 20px;
      padding-top: 10px;
      border-top: 2px solid #111;
      font-size: 0.8rem;
      color: #666;
      text-align: center;
    }}
  </style>
</head>
<body>

<div class="newspaper-container">
  <!-- ヘッダー -->
  <header class="header-top">
    <div class="paper-title">
      <span>🐉 帝王杯日報</span>
      <span class="badge">炎竜の覇者(GⅠ) 特別号</span>
      <span class="area-badge">🚩 第13競技エリア (#863 - #912) 激突編</span>
    </div>
    <div class="issue-info">
      対象競技区: <strong>第13競技エリア（王国#863 〜 王国#912）</strong><br>
      データ提供: MightPulse API / AI合同コンソーシアム特命取材班
    </div>
  </header>

  <!-- 特大一面見出し -->
  <section class="headline-box">
    <div class="headline-sub">【第13競技エリア頂上決戦】見かけの兵隊総戦力に騙されるな！ 英雄・装備の「真の実力」が完全白日の下に！</div>
    <div class="headline-main">
      本命は史上最強クジラ擁する<em>◎#855 [855]</em>か！？<br>
      受けて立つ支持数No.1の厚層軍団<em>◯#900 [24K]</em>の激突！
    </div>
    <p class="lead-text">
      炎竜宮殿の5時間耐久争奪戦を制するのは誰だ！？<br>
      MightPulseより独自入手した各同盟トップ10プレイヤーの<strong>「ミスティックトライアル（Mystic Trial）進捗階数」</strong>を徹底監査した結果、
      世間の支持数（人気投票）とは乖離した驚愕の戦力格差が浮き彫りとなった。
      単体最強の突破力か、複数クジラによる無尽蔵のローテーションか——。勝負の行方を徹底分析！
    </p>
  </section>

  <!-- 読者への解説コーナー：推定オッズの定義 -->
  <section class="explainer-box">
    <div class="explainer-title">
      <span>💡 【読者解説】「推定オッズ」の定義について</span>
    </div>
    <div>
      ゲーム内イベントの投票報酬は「的中すれば誰でも一律10倍」という固定倍率です。<br>
      しかし、本紙に掲載している<strong>「推定オッズ」</strong>は、競馬専門紙の能力指数と同様に、
      <strong>『ミスティックトライアル階数（基礎バフ・英雄装備・研究進捗）から逆算した本来あるべき勝率期待値（フェアオッズ）』</strong>を示しています。<br>
      支持数1位の 24K（オッズ2.1倍）よりも、単体最大火力で圧倒する 855 の勝率を約50%（オッズ1.8倍）と本紙は高く評価しており、<strong>「世間の人気投票（支持数）と、隠された真の実力差のギャップ」</strong>をあえて可視化しています。
    </div>
  </section>

  <!-- 出走表（メイン競馬新聞テーブル） -->
  <section class="card-box">
    <div class="section-title">
      <span>🏆 炎竜の覇者 出走本紙予想表（枠順・印・オッズ・実戦力診断）</span>
      <span class="badge-sub">第13競技エリア / 炎竜宮殿 5時間耐久</span>
    </div>

    <div style="overflow-x:auto;">
      <table class="race-table">
        <thead>
          <tr>
            <th style="width:40px;">枠/印</th>
            <th style="width:140px;">同盟・サーバー</th>
            <th style="width:75px;">推定オッズ</th>
            <th style="width:115px;">支持数(人気)</th>
            <th>エース砲台 (Top1)</th>
            <th>Top3 平均階数</th>
            <th>Top10 平均</th>
            <th>Top10 総戦力</th>
            <th>Top10 キル数</th>
            <th>脚質・陣営レポート</th>
          </tr>
        </thead>
        <tbody>
'''

for idx, d in enumerate(data):
    key = d['abbr']
    if d['abbr'] == 'KOR':
        key = f"KOR_{d['kid']}"
    info = marks.get(key, {'mark': '無', 'mark_name': '見送り', 'class': 'mark-none', 'odds': '99.0倍', 'ninki': '-', 'jockey': f"Top1 ({d['top1_mt']}階)", 'stable': f"#{d['kid']}", 'leg': '情報精査中'})
    
    top3_class = "highlight-top" if d['top3_avg_mt'] >= 3500 else ""
    top1_class = "whale-highlight" if d['top1_mt'] >= 3500 else ""
    
    html_content += f'''
          <tr>
            <td class="mark-cell {info['class']}">{info['mark']}</td>
            <td class="alliance-cell">
              <span class="alliance-tag">#{d['kid']}</span> [{d['abbr']}]<br>
              <small style="color:#666;">人員: {d['member_count']}名</small>
            </td>
            <td style="font-weight:900; font-size:1.05rem; color:#d32f2f;">{info['odds']}</td>
            <td>{info['ninki']}</td>
            <td class="{top1_class}"><strong>{info['jockey']}</strong></td>
            <td class="{top3_class}"><strong>{d['top3_avg_mt']:.1f}階</strong></td>
            <td>{d['top10_avg_mt']:.1f}階</td>
            <td>{(d['top10_power']/1e9):.2f}B</td>
            <td>{(d['top10_kills']/1e6):.1f}M</td>
            <td style="text-align:left; font-size:0.8rem; line-height:1.4;">
              <strong>【{info['leg']}】</strong><br>
              {info['stable']}。
            </td>
          </tr>
    '''

html_content += f'''
        </tbody>
      </table>
    </div>
  </section>

  <!-- メイングリッド（インフォグラフィック ＆ 買い目指南） -->
  <div class="main-grid">
    <!-- 左カラム: インフォグラフィック比較チャート -->
    <div class="card-box">
      <div class="section-title">
        <span>📊 決定的インフォグラフィック：ミスティック階数 vs 見かけの総戦力</span>
        <span class="badge-sub">第13競技エリア実測値</span>
      </div>

      <p style="font-size:0.85rem; color:#444; margin-bottom:10px;">
        ※下のグラフは、各同盟の<strong>「Top 3 平均ミスティック階数（実戦力・赤棒）」</strong>と<strong>「Top 10 総戦力（兵隊込みPower・青折れ線）」</strong>の相関を示したものです。<br>
        戦力値が高くてもミスティックが低い同盟は「兵隊水増し（兵隊デブ）」であり、上位クジラの集結攻撃を受けると一瞬で蒸発します。
      </p>

      <div class="chart-container" style="height:350px;">
        <canvas id="mysticComparisonChart"></canvas>
      </div>

      <div class="chart-container" style="height:260px;">
        <canvas id="killsComparisonChart"></canvas>
      </div>
    </div>

    <!-- 右カラム: 競馬予想・本紙特命推奨馬券（投票戦略） -->
    <div>
      <div class="card-box" style="background:#fffde7; border-color:#fbc02d;">
        <div class="section-title" style="border-color:#b78103;">
          <span>🎯 本紙特命記者 買い目指南</span>
          <span class="badge-sub">期待値最大化</span>
        </div>

        <p style="font-size:0.88rem; line-height:1.5; margin-bottom:10px;">
          炎竜の覇者・応援システムは<strong>「1口1,000竜爪 → 的中10,000竜爪（10倍）」</strong>、外れても半額500竜爪が返還される神ルール。
          数学的損益分岐点は勝率わずか<strong>5.26%</strong>のため、上位3枠をフル活用するのが鉄則！
        </p>

        <div class="betting-card">
          <div class="betting-title">
            <span>🔥 鉄板本命トリオ（推奨3同盟投票）</span>
          </div>

          <div class="bet-row">
            <span class="bet-tag">① 【本命◎】 #855 [855]</span>
            <span class="bet-ret">1,000竜爪 投票</span>
          </div>
          <div style="font-size:0.75rem; color:#555; padding:2px 0 6px 15px;">
            理由: Top1が3,695階、Top3平均3,613階は全エリアぶっちぎり。宮殿防衛の絶対障壁。
          </div>

          <div class="bet-row">
            <span class="bet-tag">② 【対抗◯】 #900 [24K]</span>
            <span class="bet-ret">1,000竜爪 投票</span>
          </div>
          <div style="font-size:0.75rem; color:#555; padding:2px 0 6px 15px;">
            理由: 3,400〜3,580階超の重課金クジラが5枚。キル数21億の圧倒的物量と継戦力。
          </div>

          <div class="bet-row">
            <span class="bet-tag">③ 【単穴▲】 #846 [RYO]</span>
            <span class="bet-ret">1,000竜爪 投票</span>
          </div>
          <div style="font-size:0.75rem; color:#555; padding:2px 0 6px 15px;">
            理由: 実力ランクS。上位2強が正面激突して消耗・泥沼化した際の漁夫の利筆頭。
          </div>
        </div>

        <!-- パドック気配・展開シミュレーション -->
        <div style="margin-top:20px; font-size:0.85rem; line-height:1.6;">
          <h4 style="font-size:0.95rem; font-weight:900; margin-bottom:6px; color:#222; border-bottom:2px solid #222; padding-bottom:3px;">
            🏇 第13競技エリア レース展開シミュレーション
          </h4>
          <p>
            <strong>【序盤】</strong> 移動速度特化の突入組が一瞬宮殿を奪うが、10分以内に上位同盟の第1波集結で吹き飛ぶ（予想クイズQ2「最初に占領した者が覇者になるか」は迷わず『いいえ』）。<br>
            <strong>【中盤】</strong> #900 [24K] が圧倒的な兵力で宮殿を制圧にかかるが、#855 [855] のモンスタークジラ（Dracfolus / 3,695階）率いるピンポイント破壊集結が直撃。宮殿の所有権が目まぐるしく入れ替わる激戦へ。<br>
            <strong>【終盤】</strong> 同サバ別動隊 [DOM] との連携で晶塔バフを確保した [855] が、最終防衛ラインを構築して逃げ切るか、[24K] が層の厚さで押し潰すかの一騎打ち！
          </p>
        </div>
      </div>

      <!-- クジラ砲台ピックアップ -->
      <div class="card-box">
        <div class="section-title">
          <span>🐋 注目クジラ（集結主・砲台）格付け</span>
        </div>
        <div style="line-height:1.6; font-size:0.82rem;">
          <div class="whale-pill">
            👑 <strong>Dracfolus (#855)</strong>: 戦力2.76B / <strong>3,695階</strong> (全サバ頂点)
          </div>
          <div class="whale-pill">
            🥈 <strong>Niki (#900)</strong>: 戦力2.53B / <strong>3,585階</strong> (24K総大将)
          </div>
          <div class="whale-pill">
            🥉 <strong>Luka (#900)</strong>: 戦力2.45B / <strong>3,577階</strong> (撃破3億超)
          </div>
          <div class="player-pill">
            🐱 <strong>Admiral Tinky (#837)</strong>: 戦力1.48B / <strong>3,500階</strong> (CAT孤高の砲台)
          </div>
          <div class="player-pill">
            ⚔️ <strong>Metabold (#855)</strong>: 戦力997M / <strong>3,573階</strong> (隠れ超高バフ)
          </div>
          <div class="player-pill">
            ⚔️ <strong>Alice~靜 (#900)</strong>: 戦力2.04B / <strong>3,473階</strong> (撃破3.9億)
          </div>
        </div>
      </div>
    </div>
  </div>

  <footer class="footer-note">
    KingShot 炎竜の覇者 大予想新聞 | 第13競技エリア(#863-#912) 特別編 | 発行: AI合同コンソーシアム（Gemini / Claude / GPT-6 / Qwen） | データソース: MightPulse API
  </footer>
</div>

<script>
  // Chart 1: Mystic Trial vs Power
  const ctx1 = document.getElementById('mysticComparisonChart').getContext('2d');
  const chartData = {json.dumps(chart_json, ensure_ascii=False)};

  new Chart(ctx1, {{
    type: 'bar',
    data: {{
      labels: chartData.labels,
      datasets: [
        {{
          label: 'Top3 平均ミスティック(階数)',
          data: chartData.top3,
          backgroundColor: 'rgba(211, 47, 47, 0.85)',
          borderColor: 'rgba(211, 47, 47, 1)',
          borderWidth: 1,
          yAxisID: 'y'
        }},
        {{
          label: 'Top10 平均ミスティック(階数)',
          data: chartData.top10,
          backgroundColor: 'rgba(255, 152, 0, 0.6)',
          borderColor: 'rgba(255, 152, 0, 1)',
          borderWidth: 1,
          yAxisID: 'y'
        }},
        {{
          label: 'Top10 総戦力 (Billion)',
          data: chartData.power,
          type: 'line',
          borderColor: 'rgba(2, 119, 189, 1)',
          backgroundColor: 'rgba(2, 119, 189, 0.2)',
          borderWidth: 3,
          pointRadius: 5,
          yAxisID: 'y1'
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      scales: {{
        y: {{
          type: 'linear',
          display: true,
          position: 'left',
          title: {{ display: true, text: 'ミスティックトライアル (階数)' }},
          min: 1500,
          max: 4000
        }},
        y1: {{
          type: 'linear',
          display: true,
          position: 'right',
          title: {{ display: true, text: 'Top10 総戦力 (B)' }},
          grid: {{ drawOnChartArea: false }},
          min: 0,
          max: 20
        }}
      }},
      plugins: {{
        legend: {{ position: 'top' }},
        tooltip: {{
          callbacks: {{
            label: function(context) {{
              let label = context.dataset.label || '';
              if (label) label += ': ';
              if (context.parsed.y !== null) {{
                label += context.parsed.y + (context.datasetIndex === 2 ? ' B' : ' 階');
              }}
              return label;
            }}
          }}
        }}
      }}
    }}
  }});

  // Chart 2: Top 10 Kills Comparison
  const ctx2 = document.getElementById('killsComparisonChart').getContext('2d');
  new Chart(ctx2, {{
    type: 'bar',
    data: {{
      labels: chartData.labels,
      datasets: [
        {{
          label: 'Top10 累計撃破数 (Million Kills)',
          data: chartData.kills,
          backgroundColor: 'rgba(74, 20, 140, 0.75)',
          borderColor: 'rgba(74, 20, 140, 1)',
          borderWidth: 1
        }}
      ]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      scales: {{
        y: {{
          beginAtZero: true,
          title: {{ display: true, text: '撃破キル数 (M)' }}
        }}
      }},
      plugins: {{
        legend: {{ position: 'top' }}
      }}
    }}
  }});
</script>

</body>
</html>
'''

with open('炎竜の覇者_競馬予想新聞.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print('SUCCESS: Updated 炎竜の覇者_競馬予想新聞.html with CAT and Area #863-#912 info!')
