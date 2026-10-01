import os

html_code = """<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>【キングスショット】PvPジョイナー全世代最強Tier早見表 | ゴリポンチャンネル公式</title>
  <meta name="description" content="キングスショット(Kingshot)の集結(ラリー)合流枠(ジョイナー)における全英雄Tier表・スキル倍率早見表。サウルが神の理由、チェンコ・インウーの殺傷力乗算、ロン・フェイの罠、乗算計算機完備！">
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@400;700;900&family=Orbitron:wght@600;900&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'M PLUS Rounded 1c', sans-serif; background: radial-gradient(circle at 50% 0%, #1a162b 0%, #0a0814 100%); color: #f1f5f9; min-height: 100vh; }
    .font-digit { font-family: 'Orbitron', monospace; }
    .rainbow-border {
      background: linear-gradient(90deg, #ff007a, #9600ff, #00d4ff, #00ff88, #ffbf00, #ff007a);
      background-size: 300% 300%;
      animation: rainbowGlow 4s linear infinite;
    }
    @keyframes rainbowGlow { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
    .gold-glow { box-shadow: 0 0 25px rgba(234, 179, 8, 0.4), inset 0 0 15px rgba(234, 179, 8, 0.2); }
    .tier-s { background: linear-gradient(135deg, rgba(234, 179, 8, 0.2) 0%, rgba(168, 85, 247, 0.2) 100%); border-color: #eab308; }
    .tier-a { background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(249, 115, 22, 0.15) 100%); border-color: #f97316; }
    .tier-b { background: linear-gradient(135deg, rgba(34, 197, 94, 0.15) 0%, rgba(16, 185, 129, 0.15) 100%); border-color: #22c55e; }
    .tier-c { background: linear-gradient(135deg, rgba(59, 130, 246, 0.15) 0%, rgba(99, 102, 241, 0.15) 100%); border-color: #3b82f6; }
  </style>
</head>
<body class="p-3 md:p-6">
  <!-- Header Section -->
  <header class="max-w-6xl mx-auto mb-8">
    <div class="p-1 rounded-2xl rainbow-border shadow-2xl">
      <div class="bg-slate-950/90 backdrop-blur-md rounded-2xl p-5 md:p-7 relative overflow-hidden">
        <div class="absolute inset-0 bg-[linear-gradient(to_right,#1f293715_1px,transparent_1px),linear-gradient(to_bottom,#1f293715_1px,transparent_1px)] bg-[size:2rem_2rem] pointer-events-none"></div>

        <div class="flex flex-col md:flex-row items-center justify-between gap-6 relative z-10">
          <div class="flex items-center gap-4 text-center md:text-left">
            <div class="relative">
              <img src="icons/goripon.jpg" alt="ゴリポン先生" class="w-20 h-20 md:w-24 md:h-24 rounded-full border-2 border-yellow-400 object-cover shadow-lg gold-glow">
              <span class="absolute -bottom-2 -right-1 bg-yellow-500 text-slate-950 text-xs font-black px-2 py-0.5 rounded-full shadow">先生</span>
            </div>
            <div>
              <div class="flex items-center gap-2 justify-center md:justify-start">
                <span class="bg-red-600/80 text-white text-[10px] font-bold px-2 py-0.5 rounded border border-red-400">YouTube連動</span>
                <span class="bg-purple-600/80 text-purple-200 text-[10px] font-bold px-2 py-0.5 rounded border border-purple-400">全世代対応</span>
              </div>
              <h1 class="text-2xl md:text-3xl font-black tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-yellow-300 via-pink-400 to-cyan-300 mt-1">
                キングスショット PvPジョイナー最強Tier早見表
              </h1>
              <p class="text-xs md:text-sm text-slate-300 mt-1">
                集結(ラリー)に乗せるだけで勝率激変！攻撃×殺傷の乗算シミュレーター＆戦犯回避ガイド
              </p>
            </div>
          </div>

          <!-- YouTube CTA -->
          <div class="flex flex-col sm:flex-row items-center gap-3">
            <a href="https://www.youtube.com/@%E3%82%B0%E3%83%BC%E3%83%AA%E3%83%BC%E3%83%9D%E3%83%B3-x1t" target="_blank" class="flex items-center gap-2 bg-red-600 hover:bg-red-500 text-white font-bold px-4 py-2.5 rounded-xl shadow-lg transition-all hover:scale-105">
              <i data-lucide="youtube" class="w-5 h-5"></i>
              <span>ゴリポンCHを見る</span>
            </a>
            <button onclick="scrollToCalc()" class="flex items-center gap-2 bg-slate-800 hover:bg-slate-700 text-yellow-300 border border-yellow-500/40 font-bold px-4 py-2.5 rounded-xl transition-all">
              <i data-lucide="calculator" class="w-5 h-5"></i>
              <span>乗算計算機</span>
            </button>
          </div>
        </div>

        <!-- Navigator Banter Banner -->
        <div class="mt-5 pt-4 border-t border-slate-800/80 grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div class="flex items-center gap-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
            <img src="icons/rosa_host.jpg" alt="ローザ" class="w-10 h-10 rounded-full border border-pink-400 object-cover">
            <div>
              <span class="font-bold text-pink-400">ローザ:</span>
              <span class="text-slate-300">「無課金でもチェンコやインウーの殺傷力25%で大活躍できるんですね！」</span>
            </div>
          </div>
          <div class="flex items-center gap-3 bg-slate-900/60 p-2.5 rounded-xl border border-slate-800">
            <img src="icons/petra_host.jpg" alt="ペトラ" class="w-10 h-10 rounded-full border border-cyan-400 object-cover">
            <div>
              <span class="font-bold text-cyan-400">ペトラ:</span>
              <span class="text-slate-300">「攻撃25%と殺傷25%を掛け合わせるのが基本よ。ロン・フェイは論外よ」</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>

  <!-- Quick Rule Highlight Banner -->
  <section class="max-w-6xl mx-auto mb-8 grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
    <div class="bg-slate-900/80 border border-yellow-500/40 rounded-xl p-4 shadow">
      <div class="text-yellow-400 font-bold text-sm flex items-center justify-center gap-1">
        <i data-lucide="sparkles" class="w-4 h-4"></i>【攻撃×殺傷の乗算】
      </div>
      <div class="text-xl font-digit font-black text-yellow-300 mt-1">1.25(攻) × 1.25(殺) ＝ 56%UP</div>
      <p class="text-xs text-slate-400 mt-1">同種バフは加算(50%)、攻撃と殺傷を組み合わせると掛け算で威力爆発！</p>
    </div>
    <div class="bg-slate-900/80 border border-cyan-500/40 rounded-xl p-4 shadow">
      <div class="text-cyan-400 font-bold text-sm flex items-center justify-center gap-1">
        <i data-lucide="shield" class="w-4 h-4"></i>【無課金の救世主】
      </div>
      <div class="text-xl font-digit font-black text-cyan-300 mt-1">チェンコ / インウー ＝ 殺傷25%</div>
      <p class="text-xs text-slate-400 mt-1">誰でも完凸できる紫英雄がSランク！攻撃特化リーダーと完璧シナジー！</p>
    </div>
    <div class="bg-slate-900/80 border border-red-500/40 rounded-xl p-4 shadow">
      <div class="text-red-400 font-bold text-sm flex items-center justify-center gap-1">
        <i data-lucide="alert-triangle" class="w-4 h-4"></i>【ロン・フェイの罠】
      </div>
      <div class="text-xl font-digit font-black text-red-400 mt-1">40%被ダメ軽減 ＝ 期待値20%</div>
      <p class="text-xs text-slate-400 mt-1">防衛最強でも合流はCランク戦犯！重複不可で神バフ枠を潰す！</p>
    </div>
  </section>

  <!-- Filter Controls -->
  <section class="max-w-6xl mx-auto mb-6">
    <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4 shadow-xl">
      <div class="flex flex-wrap items-center gap-2">
        <span class="text-xs font-bold text-slate-400 mr-1">Tier:</span>
        <button onclick="setTierFilter('ALL')" id="btn-tier-ALL" class="tier-btn px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-700 text-white border border-slate-600 transition">ALL</button>
        <button onclick="setTierFilter('S')" id="btn-tier-S" class="tier-btn px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-800 text-yellow-400 border border-yellow-500/40 hover:bg-yellow-500/20 transition">🌈 S Tier (必須神)</button>
        <button onclick="setTierFilter('A')" id="btn-tier-A" class="tier-btn px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-800 text-orange-400 border border-orange-500/40 hover:bg-orange-500/20 transition">🔥 A Tier (準主役)</button>
        <button onclick="setTierFilter('B')" id="btn-tier-B" class="tier-btn px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-800 text-emerald-400 border border-emerald-500/40 hover:bg-emerald-500/20 transition">🌿 B Tier (職人枠)</button>
        <button onclick="setTierFilter('C')" id="btn-tier-C" class="tier-btn px-3 py-1.5 rounded-lg text-xs font-bold bg-slate-800 text-blue-400 border border-blue-500/40 hover:bg-blue-500/20 transition">⚠️ C Tier (地雷罠)</button>
      </div>

      <div class="flex items-center gap-2">
        <span class="text-xs font-bold text-slate-400 mr-1">兵種:</span>
        <button onclick="setTroopFilter('ALL')" id="btn-troop-ALL" class="troop-btn px-2.5 py-1 rounded text-xs font-bold bg-slate-700 text-white">ALL</button>
        <button onclick="setTroopFilter('infantry')" id="btn-troop-infantry" class="troop-btn px-2.5 py-1 rounded text-xs font-bold bg-slate-800 text-slate-300 hover:text-white">🛡️ 歩兵</button>
        <button onclick="setTroopFilter('cavalry')" id="btn-troop-cavalry" class="troop-btn px-2.5 py-1 rounded text-xs font-bold bg-slate-800 text-slate-300 hover:text-white">🐎 騎兵</button>
        <button onclick="setTroopFilter('archer')" id="btn-troop-archer" class="troop-btn px-2.5 py-1 rounded text-xs font-bold bg-slate-800 text-slate-300 hover:text-white">🏹 弓兵</button>
      </div>

      <div class="relative w-full md:w-56">
        <i data-lucide="search" class="w-4 h-4 absolute left-3 top-2.5 text-slate-400"></i>
        <input type="text" id="searchInput" oninput="handleSearch()" placeholder="英雄名で検索..." class="w-full bg-slate-950 border border-slate-700 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-yellow-400">
      </div>
    </div>
  </section>

  <!-- Heroes Grid -->
  <main class="max-w-6xl mx-auto mb-16">
    <div id="heroesContainer" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"></div>
  </main>

  <!-- Interactive Section: Combat Multiplier Calculator & Rally Checker -->
  <section id="calcSection" class="max-w-6xl mx-auto mb-16">
    <div class="bg-slate-900/95 border border-purple-500/40 rounded-2xl p-6 md:p-8 shadow-2xl relative overflow-hidden">
      <div class="flex items-center gap-3 mb-6">
        <div class="p-3 bg-purple-600/20 rounded-xl border border-purple-400">
          <i data-lucide="swords" class="w-6 h-6 text-purple-400"></i>
        </div>
        <div>
          <h2 class="text-xl md:text-2xl font-black text-white">4人合流（ラリージョイナー）編成チェッカー</h2>
          <p class="text-xs md:text-sm text-slate-400">合流4枠を選択して、総合火力倍率とスキルの被り（加算ロス）を即時診断！</p>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
          <label class="text-xs text-yellow-400 font-bold block mb-2">【枠1: 主力攻撃枠】</label>
          <select id="slot1" onchange="calculateRally()" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-bold">
            <option value="saul">サウル (S: 自前乗算26.5%)</option>
            <option value="hilde">ヒルダ (S: 自前乗算26.5%)</option>
            <option value="margot">マーゴ (S: 攻撃25%確定)</option>
            <option value="amane">アマネ (S: 殺傷25%確定)</option>
            <option value="petra">ペトラ (B: 3兵種時43.75%)</option>
            <option value="long-fei">ロン・フェイ (C: 期待値20%戦犯)</option>
          </select>
        </div>
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
          <label class="text-xs text-cyan-400 font-bold block mb-2">【枠2: 殺傷力枠 (無課金神)】</label>
          <select id="slot2" onchange="calculateRally()" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-bold">
            <option value="chenko">チェンコ (S: 殺傷25%確定/無課金神)</option>
            <option value="yeonwoo">インウー (S: 殺傷25%確定/無課金神)</option>
            <option value="amane">アマネ (S: 殺傷25%確定)</option>
            <option value="eric">エリック (S: 敵攻撃力ダウン)</option>
            <option value="fahd">ファハド (S/A: 敵与ダメダウン)</option>
            <option value="long-fei">ロン・フェイ (C: 期待値20%戦犯)</option>
          </select>
        </div>
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
          <label class="text-xs text-orange-400 font-bold block mb-2">【枠3: デバフ/弱体化】</label>
          <select id="slot3" onchange="calculateRally()" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-bold">
            <option value="eric">エリック (S: 敵攻撃力ダウン)</option>
            <option value="fahd">ファハド (S/A: 敵与ダメダウン)</option>
            <option value="margot">マーゴ (S: 攻撃25%確定)</option>
            <option value="triton">トリトン (S: 防御25%重複なし)</option>
            <option value="rosa">ローザ (B: 期待値20%重複可)</option>
            <option value="long-fei">ロン・フェイ (C: 期待値20%戦犯)</option>
          </select>
        </div>
        <div class="bg-slate-950 p-4 rounded-xl border border-slate-800">
          <label class="text-xs text-emerald-400 font-bold block mb-2">【枠4: 防御/特化シナジー】</label>
          <select id="slot4" onchange="calculateRally()" class="w-full bg-slate-900 border border-slate-700 rounded-lg p-2 text-xs text-white font-bold">
            <option value="triton">トリトン (S: 防御25%重複なし)</option>
            <option value="petra">ペトラ (B: 3兵種時43.75%)</option>
            <option value="yang">ヤン (B: トリトン乗算シナジー)</option>
            <option value="thrud">スルーズ (B: 48/4/48編成特化)</option>
            <option value="long-fei">ロン・フェイ (C: 期待値20%戦犯)</option>
          </select>
        </div>
      </div>

      <div id="rallyResultCard" class="bg-slate-950/80 border border-yellow-500/40 rounded-xl p-5 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <div class="flex items-center gap-2">
            <span id="rallyScoreBadge" class="bg-yellow-500 text-slate-950 font-black text-xs px-2.5 py-0.5 rounded">理想の神編成</span>
            <span class="text-xs text-slate-400">推定総合実効倍率:</span>
          </div>
          <div class="text-2xl md:text-3xl font-digit font-black text-yellow-300 mt-1" id="rallyMultiplierText">
            約 2.14倍（+114%）
          </div>
          <p id="rallyAdviceText" class="text-xs text-slate-300 mt-1">
            攻撃25%×殺傷25%の完全乗算が成立！スキルの重複が一切なく、格上相手でも大逆転可能な黄金比率です！
          </p>
        </div>
        <div class="text-right">
          <button onclick="calculateRally()" class="bg-yellow-500 hover:bg-yellow-400 text-slate-950 font-bold px-4 py-2 rounded-xl text-xs flex items-center gap-1 shadow">
            <i data-lucide="refresh-cw" class="w-4 h-4"></i> 再計算
          </button>
        </div>
      </div>
    </div>
  </section>

  <footer class="max-w-6xl mx-auto border-t border-slate-800 pt-8 pb-16 text-center text-xs text-slate-500">
    <div class="flex items-center justify-center gap-2 mb-3">
      <img src="icons/goripon.jpg" alt="ゴリポン" class="w-6 h-6 rounded-full border border-yellow-500/40">
      <span class="text-slate-300 font-bold">ゴリポンチャンネル公認 PvP攻略データベース</span>
    </div>
    <p>本データは海外上位ランカーの検証シミュレーションおよびゲーム内戦闘数式に基づき作成されています。</p>
    <p class="mt-1">© 2026 ゴリポンチャンネル All Rights Reserved.</p>
  </footer>

  <script>
    const heroesData = [
      // S Tier (God Tier)
      { id: 'saul', name: 'サウル', origName: 'Saul', tier: 'S', gen: 'Gen 1', troop: 'archer', troopName: '弓兵', icon: 'icons/saul.png', badge: '自前乗算の神', skillName: '軍事指導 (攻撃15% + 殺傷10%)', value: '+26.5% (実効)', desc: '第1世代なのに自前で1.15×1.10=1.265倍の乗算を発動。他英雄とバフが被りにくく加算希釈されない永久人権ジョイナー。' },
      { id: 'hilde', name: 'ヒルダ', origName: 'Hilde', tier: 'S', gen: 'Gen 2', troop: 'cavalry', troopName: '騎兵', icon: 'icons/hilde.png', badge: '自前乗算の神', skillName: '剛力の秘薬 (分割バフ)', value: '+26.5% (実効)', desc: 'サウル同様の分割スキル。集結リーダーが誰であっても多様な編成で乗算火力を叩き出すSランクの要。' },
      { id: 'chenko', name: 'チェンコ', origName: 'Chenko', tier: 'S', gen: 'Gen 1 (SR)', troop: 'cavalry', troopName: '騎兵', icon: 'icons/chenko.png', badge: '殺傷25%・無課金神', skillName: '突進援護 (殺傷力25%確定UP)', value: '+25.0% 確定', desc: '誰でも完凸できる紫英雄ながら「殺傷力25%常時確定」！攻撃UP持ちリーダーと組むと別枠乗算で威力を跳ね上げる金字塔。' },
      { id: 'yeonwoo', name: 'インウー', origName: 'Yeonwoo', tier: 'S', gen: 'Gen 1 (SR)', troop: 'archer', troopName: '弓兵', icon: 'icons/yeonwoo.png', badge: '殺傷25%・無課金神', skillName: '護身 (殺傷力25%確定UP)', value: '+25.0% 確定', desc: '熊狩りでもおなじみの殺傷力確定25%！チェンコ同様、誰でも育てやすくPvP集結でも最強の仕事をする超優秀ジョイナー。' },
      { id: 'eric', name: 'エリック', origName: 'Eric', tier: 'S', gen: 'Gen 3', troop: 'infantry', troopName: '歩兵', icon: 'icons/eric.png', badge: '唯一無二デバフ', skillName: '威嚇咆哮 (敵攻撃力20%低下)', value: '希少乗算枠', desc: 'ゲーム内唯一無二の「敵部隊攻撃力ダウン」コード。他バフと100%被らず必ず乗算でダメージを削る最高峰ジョイナー。' },
      { id: 'fahd', name: 'ファハド', origName: 'Fahd', tier: 'S', gen: 'Gen 1 (SR)', troop: 'cavalry', troopName: '騎兵', icon: 'icons/fahd.png', badge: '初期S→後代A', skillName: '砂漠の強襲 (敵与ダメ20%減)', value: '希少デバフ', desc: '初期世代では敵被ダメ減が唯一無二でSランク。第4世代以降は同スキル持ちが増えるためAランクに落ち着く。' },
      { id: 'margot', name: 'マーゴ', origName: 'Margot', tier: 'S', gen: 'Gen 4', troop: 'cavalry', troopName: '騎兵', icon: 'icons/margot.png', badge: '攻撃25%基準値', skillName: '突撃激励 (攻撃力25%確定UP)', value: '+25.0% 確定', desc: '運要素ゼロの確定攻撃25%バフ。チェンコやインウーの殺傷25%と組むことで1.25×1.25=56%の乗算火力を生み出す。' },
      { id: 'amane', name: 'アマネ', origName: 'Amane', tier: 'S', gen: 'Gen 4', troop: 'archer', troopName: '弓兵', icon: 'icons/amane.png', badge: '殺傷25%基準値', skillName: '戦慄の矢 (殺傷力25%確定UP)', value: '+25.0% 確定', desc: 'レジェンド枠の殺傷力25%確定バフ。無条件で25%底上げするため、攻撃特化リーダーと完璧に噛み合う。' },
      { id: 'triton', name: 'トリトン', origName: 'Triton', tier: 'S', gen: 'Gen 6', troop: 'infantry', troopName: '歩兵', icon: 'icons/triton.png', badge: '防御25%重複なし', skillName: '深海の加護 (防御25%確定UP)', value: '+25.0% 確定', desc: 'Sランクの多くが攻撃・殺傷に偏る中、希少な「確定防御25%」。他英雄と被らず別枠乗算を狙える第6世代の神。' },

      // A Tier
      { id: 'vivian', name: 'ヴィヴィアン', origName: 'Vivian', tier: 'A', gen: 'Gen 5', troop: 'archer', troopName: '弓兵', icon: 'icons/vivian.png', badge: '仕様要注意枠', skillName: '精霊の射撃 (通常攻撃連動)', value: '実質約20%', desc: '額面25%に見えるが、通常攻撃の判定上書きバグで一部不発になる例外持ち。悪くはないが過信禁物。' },
      { id: 'charles', name: 'チャールズ', origName: 'Charles', tier: 'A', gen: 'Gen 7', troop: 'infantry', troopName: '歩兵', icon: 'icons/charles.png', badge: '強豪重複注意', skillName: '敵殺傷力20%低下', value: '実効約20%', desc: '希少なデバフだが、Gen7ラリーリーダー自身が持っていることが多く重複加算のリスクがあるためA評価。' },

      // B Tier
      { id: 'petra', name: 'ペトラ', origName: 'Petra', tier: 'B', gen: 'Gen 3', troop: 'cavalry', troopName: '騎兵', icon: 'icons/petra.png', badge: '3兵種で期待値43%', skillName: '急所狙い (兵種攻撃毎50%判定)', value: '最大 +43.75%', desc: '3兵種揃えば毎ターン3回判定で発動率87.5%＝全英雄最強倍率！ただし「重複不可」のため同盟内で1人限定のB評価。' },
      { id: 'rosa', name: 'ローザ', origName: 'Rosa', tier: 'B', gen: 'Gen 4', troop: 'archer', troopName: '弓兵', icon: 'icons/rosa.png', badge: '例外スタック可能', skillName: '突撃支援 (確率発動)', value: '期待値 +20.0%', desc: 'マーゴに席を取られがちだが、例外的に「複数人乗せても効果が重複スタックする」検証済み。穴埋めに有用。' },
      { id: 'thrud', name: 'スルーズ', origName: 'Thrud', tier: 'B', gen: 'Gen 5', troop: 'cavalry', troopName: '騎兵', icon: 'icons/thrud.png', badge: '48/4/48特化', skillName: '戦乙女の誓い (15%+15%)', value: '変則特化型', desc: '分割スキルだが騎兵に乗らない。騎兵を極限まで削った48/4/48等の弓・歩兵特化編成でSランク超えを叩き出す。' },
      { id: 'yang', name: 'ヤン', origName: 'Yang', tier: 'B', gen: 'Gen 6', troop: 'archer', troopName: '弓兵', icon: 'icons/yang.png', badge: 'トリトン乗算爆発', skillName: '雪崩撃 (4ターン毎100%)', value: 'トリトンで1.6倍', desc: '実質25%だが、トリトンのスキル2（スキルダメ30%UP）が乗ると1.25×1.3＝約1.625倍に化ける爆発的シナジー枠。' },

      // C Tier (Traps)
      { id: 'long-fei', name: 'ロン・フェイ', origName: 'Long Fei (Hector)', tier: 'C', gen: 'Gen 5', troop: 'infantry', troopName: '歩兵', icon: 'icons/long-fei.png', badge: '⚠️ 大戦犯トラップ', skillName: '金城湯池 (40%確率で被ダメ50%減)', value: '期待値 20% (重複不可)', desc: '個人防衛では最強だが、合流枠では期待値20%の運ゲー。しかも重複不可でサウル等の神バフ枠を潰す超危険な地雷！' },
      { id: 'zoe', name: 'ゾーイ', origName: 'Zoe', tier: 'C', gen: 'Gen 2', troop: 'infantry', troopName: '歩兵', icon: 'icons/zoe.png', badge: '⚠️ 確率被りトラップ', skillName: '20%確率で40%ダメUP(3T)', value: '期待値 24%', desc: '確率発動の継続バフ。リーダーのスキルと被りやすく重複不可のためジョイナーには不向き。' },
      { id: 'alcar', name: 'アルカー', origName: 'Alcar', tier: 'C', gen: 'Gen 4', troop: 'infantry', troopName: '歩兵', icon: 'icons/alcar.png', badge: '⚠️ 序盤死にスキル', skillName: '70%確率(5T毎2T)', value: '序盤0%の罠', desc: '最初の5ターン発動しない。被ダメージが最も集中する勝負の開幕に全く仕事しないためCランク。' },
      { id: 'sophia', name: 'ソフィア', origName: 'Sophia', tier: 'C', gen: 'Gen 6', troop: 'cavalry', troopName: '騎兵', icon: 'icons/sophia.png', badge: '⚠️ 確率軽減罠', skillName: '40%確率で被ダメ50%減', value: '期待値 20%', desc: 'ロン・フェイと同型の40%運ゲースキル。他人の確定バフ枠を食いつぶすためジョイナー選外。' }
    ];

    let currentTier = 'ALL';
    let currentTroop = 'ALL';
    let currentSearch = '';

    function renderHeroes() {
      const container = document.getElementById('heroesContainer');
      container.innerHTML = '';

      const filtered = heroesData.filter(h => {
        const matchTier = currentTier === 'ALL' || h.tier === currentTier;
        const matchTroop = currentTroop === 'ALL' || h.troop === currentTroop;
        const matchSearch = currentSearch === '' || 
          h.name.toLowerCase().includes(currentSearch.toLowerCase()) || 
          h.origName.toLowerCase().includes(currentSearch.toLowerCase());
        return matchTier && matchTroop && matchSearch;
      });

      if (filtered.length === 0) {
        container.innerHTML = '<div class="col-span-full text-center py-12 text-slate-500 font-bold">該当する英雄が見つかりませんでした。</div>';
        return;
      }

      filtered.forEach(h => {
        const tierClass = h.tier === 'S' ? 'tier-s' : h.tier === 'A' ? 'tier-a' : h.tier === 'B' ? 'tier-b' : 'tier-c';
        const tierBadgeColor = h.tier === 'S' ? 'bg-yellow-500 text-slate-950' : h.tier === 'A' ? 'bg-orange-500 text-white' : h.tier === 'B' ? 'bg-emerald-500 text-slate-950' : 'bg-blue-600 text-white';

        const card = document.createElement('div');
        card.className = `rounded-2xl border p-4 transition-all duration-200 hover:-translate-y-1 shadow-lg ${tierClass}`;
        card.innerHTML = `
          <div class="flex items-start gap-3.5">
            <div class="relative flex-shrink-0">
              <img src="${h.icon}" alt="${h.name}" onerror="this.src='https://via.placeholder.com/64?text=${h.name}'" class="w-16 h-16 rounded-xl border-2 border-slate-700 object-cover bg-slate-950 shadow">
              <span class="absolute -top-2 -left-2 ${tierBadgeColor} text-xs font-black px-2 py-0.5 rounded-full shadow">${h.tier}</span>
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between">
                <h3 class="text-base font-black text-white truncate">${h.name} <span class="text-xs text-slate-400 font-normal">(${h.origName})</span></h3>
                <span class="text-[10px] text-slate-400 bg-slate-800/80 px-2 py-0.5 rounded border border-slate-700">${h.gen}</span>
              </div>
              <div class="flex items-center gap-1.5 mt-1">
                <span class="text-[10px] bg-slate-800 text-slate-300 px-1.5 py-0.5 rounded">${h.troopName}</span>
                <span class="text-[10px] bg-yellow-500/20 text-yellow-300 px-1.5 py-0.5 rounded border border-yellow-500/30 font-bold">${h.badge}</span>
              </div>
              <div class="mt-2 text-xs font-digit font-bold text-yellow-300">
                ${h.value} <span class="text-[10px] text-slate-400 font-normal">(${h.skillName})</span>
              </div>
            </div>
          </div>
          <div class="mt-3 pt-3 border-t border-slate-800/80 text-xs text-slate-300 leading-relaxed">
            ${h.desc}
          </div>
        `;
        container.appendChild(card);
      });
      lucide.createIcons();
    }

    function setTierFilter(tier) {
      currentTier = tier;
      document.querySelectorAll('.tier-btn').forEach(btn => {
        btn.classList.remove('bg-slate-700', 'text-white');
        btn.classList.add('bg-slate-800');
      });
      document.getElementById(`btn-tier-${tier}`).classList.add('bg-slate-700', 'text-white');
      renderHeroes();
    }

    function setTroopFilter(troop) {
      currentTroop = troop;
      document.querySelectorAll('.troop-btn').forEach(btn => {
        btn.classList.remove('bg-slate-700', 'text-white');
        btn.classList.add('bg-slate-800');
      });
      document.getElementById(`btn-troop-${troop}`).classList.add('bg-slate-700', 'text-white');
      renderHeroes();
    }

    function handleSearch() {
      currentSearch = document.getElementById('searchInput').value;
      renderHeroes();
    }

    function scrollToCalc() {
      document.getElementById('calcSection').scrollIntoView({ behavior: 'smooth' });
    }

    function calculateRally() {
      const s1 = document.getElementById('slot1').value;
      const s2 = document.getElementById('slot2').value;
      const s3 = document.getElementById('slot3').value;
      const s4 = document.getElementById('slot4').value;
      const slots = [s1, s2, s3, s4];

      let hasLongFei = slots.includes('long-fei');
      let duplicates = slots.filter((item, index) => slots.indexOf(item) !== index);
      let mult = 1.0;

      slots.forEach(h => {
        if (h === 'saul' || h === 'hilde') mult *= 1.265;
        else if (h === 'margot' || h === 'amane' || h === 'triton' || h === 'chenko' || h === 'yeonwoo') mult *= 1.25;
        else if (h === 'eric') mult *= 1.22;
        else if (h === 'petra') mult *= 1.4375;
        else if (h === 'yang') mult *= 1.30;
        else if (h === 'rosa') mult *= 1.20;
        else if (h === 'long-fei') mult *= 1.10;
      });

      const badge = document.getElementById('rallyScoreBadge');
      const multText = document.getElementById('rallyMultiplierText');
      const advice = document.getElementById('rallyAdviceText');

      multText.innerText = `約 ${mult.toFixed(2)}倍 (+${Math.round((mult - 1) * 100)}%)`;

      if (hasLongFei) {
        badge.className = 'bg-red-600 text-white font-black text-xs px-2.5 py-0.5 rounded';
        badge.innerText = '⚠️ 戦犯注意（ロン・フェイ混入）';
        advice.innerHTML = '<span class="text-red-400 font-bold">危険！</span> ロン・フェイが混ざっています。40%運ゲーの被ダメ軽減は他の確定神バフ枠を食いつぶし、複数人が乗せても重複しません。無課金でも手に入るチェンコやインウー、またはサウルに変更してください！';
      } else if (duplicates.length > 0) {
        badge.className = 'bg-orange-500 text-white font-black text-xs px-2.5 py-0.5 rounded';
        badge.innerText = '⚠️ 重複による加算ロスあり';
        advice.innerText = `英雄（${duplicates.join(', ')}）が被っています！同種バフが重なると乗算にならず加算（足し算）に希釈されます。異なる英雄に分散させてください！`;
      } else {
        badge.className = 'bg-yellow-500 text-slate-950 font-black text-xs px-2.5 py-0.5 rounded';
        badge.innerText = '🌈 理想の神編成（完全乗算）';
        advice.innerText = '全枠が異なるステータス（攻撃・殺傷・デバフ・防御）で分散されています！無課金英雄（チェンコ/インウー）も完璧に乗算火力へ寄与する最高の黄金比率です！';
      }
    }

    document.addEventListener('DOMContentLoaded', () => {
      renderHeroes();
      lucide.createIcons();
    });
  </script>
</body>
</html>"""

with open(r'web_tierlist\index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)

with open(r'C:\Users\s8933\Downloads\PvPジョイナー動画\web_tierlist\index.html', 'w', encoding='utf-8') as f:
    f.write(html_code)

# Copy yeonwoo.png to downloads web_tierlist
import shutil
shutil.copy(r'web_tierlist\icons\yeonwoo.png', r'C:\Users\s8933\Downloads\PvPジョイナー動画\web_tierlist\icons\yeonwoo.png')

print("Updated web_tierlist/index.html and synced to Downloads!")
