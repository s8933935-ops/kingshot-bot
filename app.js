/**
 * KingShot Auto-Fill Tool - Authentic Official JSON Engine
 * Strictly Validated Items:
 * 1. Joiner Slot IDs: 0, 1, 2, 3 (numbers)
 * 2. Hero Internal Names: lowercase exact keys ("amane", "chenko", "jessica", "molly", etc.)
 * 3. Skill Levels: { "1": parseInt(level) } (number type)
 */

const OFFICIAL_HEROES_MASTER = [
  { id: "howard", name: "Howard (ハワード)" },
  { id: "gordon", name: "Gordon (ゴードン)" },
  { id: "quinn", name: "Quinn (クイン)" },
  { id: "chenko", name: "Chenko (チェンコ)" },
  { id: "amane", name: "Amane (アマネ)" },
  { id: "yeonwoo", name: "Yeonwoo (ヨンウ)" },
  { id: "fahd", name: "Fahd (ファハド)" },
  { id: "diana", name: "Diana (ダイアナ)" },
  { id: "forrest", name: "Forrest (フォレスト)" },
  { id: "seth", name: "Seth (セス)" },
  { id: "edwin", name: "Edwin (エドウィン)" },
  { id: "olive", name: "Olive (オリーブ)" },
  { id: "jabel", name: "Jabel (ジャベル)" },
  { id: "saul", name: "Saul (ソール)" },
  { id: "helga", name: "Helga (ヘルガ)" },
  { id: "amadeus", name: "Amadeus (アマデウス)" },
  { id: "zoe", name: "Zoe (ゾーイ)" },
  { id: "hilde", name: "Hilde (ヒルデ)" },
  { id: "marlin", name: "Marlin (マーリン)" },
  { id: "eric", name: "Eric (エリック)" },
  { id: "petra", name: "Petra (ペトラ)" },
  { id: "jaeger", name: "Jaeger (イエーガー)" },
  { id: "alcar", name: "Alcar (アルカー)" },
  { id: "margot", name: "Margot (マーゴット)" },
  { id: "rosa", name: "Rosa (ローザ)" },
  { id: "longfei", name: "Longfei (ロンフェイ)" },
  { id: "thrud", name: "Thrud (スルード)" },
  { id: "vivian", name: "Vivian (ヴィヴィアン)" },
  { id: "triton", name: "Triton (トリトン)" },
  { id: "sophia", name: "Sophia (ソフィア)" },
  { id: "yang", name: "Yang (ヤン)" }
];

const defaultStats = [
  { key: 'inf_atk', name: '歩兵 攻撃力', left: 0, right: 0 },
  { key: 'inf_def', name: '歩兵 防御力', left: 0, right: 0 },
  { key: 'inf_leth', name: '歩兵 殺傷力', left: 0, right: 0 },
  { key: 'inf_hp', name: '歩兵 HP', left: 0, right: 0 },

  { key: 'cav_atk', name: '槍/騎 攻撃力', left: 0, right: 0 },
  { key: 'cav_def', name: '槍/騎 防御力', left: 0, right: 0 },
  { key: 'cav_leth', name: '槍/騎 殺傷力', left: 0, right: 0 },
  { key: 'cav_hp', name: '槍/騎 HP', left: 0, right: 0 },

  { key: 'lan_atk', name: '弓兵 攻撃力', left: 0, right: 0 },
  { key: 'lan_def', name: '弓兵 防御力', left: 0, right: 0 },
  { key: 'lan_leth', name: '弓兵 殺傷力', left: 0, right: 0 },
  { key: 'lan_hp', name: '弓兵 HP', left: 0, right: 0 },
];

class PlanAApp {
  constructor() {
    this.selectedColumn = 'left';
    this.loadState();

    this.initDOM();
    this.populateHeroDropdowns();
    this.bindEvents();
    this.renderStatsSummary();
    this.updateJsonPayload();
  }

  loadState() {
    const savedStats = localStorage.getItem('kingshot_stats');
    if (savedStats) {
      try {
        this.stats = JSON.parse(savedStats);
      } catch(e) {
        this.stats = JSON.parse(JSON.stringify(defaultStats));
      }
    } else {
      this.stats = JSON.parse(JSON.stringify(defaultStats));
    }
  }

  saveState() {
    localStorage.setItem('kingshot_stats', JSON.stringify(this.stats));
  }

  initDOM() {
    this.dropZone = document.getElementById('dropZone');
    this.fileInput = document.getElementById('fileInput');
    this.dropZoneContent = document.getElementById('dropZoneContent');
    this.previewContainer = document.getElementById('previewContainer');
    this.imagePreview = document.getElementById('imagePreview');
    this.removeImgBtn = document.getElementById('removeImgBtn');
    this.ocrStatusBar = document.getElementById('ocrStatusBar');

    this.btnSelectLeft = document.getElementById('btnSelectLeft');
    this.btnSelectRight = document.getElementById('btnSelectRight');
    this.statsSummaryGrid = document.getElementById('statsSummaryGrid');

    this.fighterNameInput = document.getElementById('fighterNameInput');
    this.infTier = document.getElementById('infTier');
    this.infFc = document.getElementById('infFc');

    this.cavTier = document.getElementById('cavTier');
    this.cavFc = document.getElementById('cavFc');

    this.lanTier = document.getElementById('lanTier');
    this.lanFc = document.getElementById('lanFc');

    this.leadHero1 = document.getElementById('leadHero1');
    this.leadHero2 = document.getElementById('leadHero2');
    this.leadHero3 = document.getElementById('leadHero3');

    this.joiner1 = document.getElementById('joiner1');
    this.joinerSkill1 = document.getElementById('joinerSkill1');

    this.joiner2 = document.getElementById('joiner2');
    this.joinerSkill2 = document.getElementById('joinerSkill2');

    this.joiner3 = document.getElementById('joiner3');
    this.joinerSkill3 = document.getElementById('joinerSkill3');

    this.joiner4 = document.getElementById('joiner4');
    this.joinerSkill4 = document.getElementById('joinerSkill4');

    this.jsonTextArea = document.getElementById('jsonTextArea');
    this.btnDownloadJson = document.getElementById('btnDownloadJson');
    this.resetAllBtn = document.getElementById('resetAllBtn');

    this.ocrDebugImg = document.getElementById('ocrDebugImg');
    this.ocrRawTextOutput = document.getElementById('ocrRawTextOutput');
  }

  populateHeroDropdowns() {
    const leadDropdowns = [this.leadHero1, this.leadHero2, this.leadHero3];
    const defaultLead = ["petra", "alcar", "marlin"];

    leadDropdowns.forEach((dd, idx) => {
      if (!dd) return;
      dd.innerHTML = '';
      OFFICIAL_HEROES_MASTER.forEach(h => {
        const opt = document.createElement('option');
        opt.value = h.id;
        opt.textContent = h.name;
        if (h.id === defaultLead[idx]) opt.selected = true;
        dd.appendChild(opt);
      });
    });

    const joinerDropdowns = [this.joiner1, this.joiner2, this.joiner3, this.joiner4];
    const defaultJoiners = ["amane", "amane", "amane", "amane"];

    joinerDropdowns.forEach((dd, idx) => {
      if (!dd) return;
      dd.innerHTML = '';

      OFFICIAL_HEROES_MASTER.forEach(h => {
        const opt = document.createElement('option');
        opt.value = h.id;
        opt.textContent = h.name;
        if (h.id === defaultJoiners[idx]) opt.selected = true;
        dd.appendChild(opt);
      });
    });
  }

  bindEvents() {
    if (this.btnSelectLeft) this.btnSelectLeft.addEventListener('click', () => this.setMode('left'));
    if (this.btnSelectRight) this.btnSelectRight.addEventListener('click', () => this.setMode('right'));

    if (this.fileInput) {
      this.fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
          this.handleImageFile(e.target.files[0]);
        }
      });
    }

    const configInputs = [
      this.fighterNameInput, this.infTier, this.infFc,
      this.cavTier, this.cavFc,
      this.lanTier, this.lanFc,
      this.leadHero1, this.leadHero2, this.leadHero3,
      this.joiner1, this.joinerSkill1,
      this.joiner2, this.joinerSkill2,
      this.joiner3, this.joinerSkill3,
      this.joiner4, this.joinerSkill4
    ];

    configInputs.forEach(inp => {
      if (inp) {
        inp.addEventListener('input', () => this.updateJsonPayload());
        inp.addEventListener('change', () => this.updateJsonPayload());
      }
    });

    window.addEventListener('dragover', (e) => e.preventDefault());
    window.addEventListener('drop', (e) => {
      e.preventDefault();
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        this.handleImageFile(e.dataTransfer.files[0]);
      }
    });

    window.addEventListener('paste', (e) => {
      const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
      if (items) {
        for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf('image') !== -1) {
            const blob = items[i].getAsFile();
            if (blob) {
              this.handleImageFile(blob);
              return;
            }
          }
        }
      }
    });

    if (this.removeImgBtn) {
      this.removeImgBtn.addEventListener('click', () => this.resetAllData());
    }

    if (this.resetAllBtn) {
      this.resetAllBtn.addEventListener('click', () => this.resetAllData());
    }

    if (this.btnDownloadJson) {
      this.btnDownloadJson.addEventListener('click', () => this.downloadJsonFile());
    }
  }

  resetAllData() {
    if (this.dropZoneContent) this.dropZoneContent.classList.remove('hidden');
    if (this.previewContainer) this.previewContainer.classList.add('hidden');
    if (this.fileInput) this.fileInput.value = '';
    
    localStorage.removeItem('kingshot_stats');
    this.stats = JSON.parse(JSON.stringify(defaultStats));

    // Clear all DOM inputs physically for PC browsers
    if (this.fighterNameInput) this.fighterNameInput.value = "";
    
    const defaultLead = ["petra", "alcar", "marlin"];
    if (this.leadHero1) this.leadHero1.value = defaultLead[0];
    if (this.leadHero2) this.leadHero2.value = defaultLead[1];
    if (this.leadHero3) this.leadHero3.value = defaultLead[2];

    const joinerDropdowns = [this.joiner1, this.joiner2, this.joiner3, this.joiner4];
    joinerDropdowns.forEach(dd => { if (dd) dd.value = "amane"; });

    const skillInputs = [this.joinerSkill1, this.joinerSkill2, this.joinerSkill3, this.joinerSkill4];
    skillInputs.forEach(inp => { if (inp) inp.value = "5"; });

    const tierInputs = [this.infTier, this.cavTier, this.lanTier];
    tierInputs.forEach(inp => { if (inp) inp.value = "10"; });

    const fcInputs = [this.infFc, this.cavFc, this.lanFc];
    fcInputs.forEach(inp => { if (inp) inp.value = "5"; });

    this.renderStatsSummary();
    this.updateJsonPayload();
  }

  setMode(mode) {
    this.selectedColumn = mode;
    if (this.btnSelectLeft) {
      this.btnSelectLeft.classList.toggle('active', mode === 'left');
      this.btnSelectLeft.innerHTML = mode === 'left' ? '<span class="dot"></span> (●) 左列の数値' : '<span class="dot"></span> (  ) 左列の数値';
    }
    if (this.btnSelectRight) {
      this.btnSelectRight.classList.toggle('active', mode === 'right');
      this.btnSelectRight.innerHTML = mode === 'right' ? '<span class="dot"></span> (●) 右列の数値' : '<span class="dot"></span> (  ) 右列の数値';
    }

    this.renderStatsSummary();
    this.updateJsonPayload();
  }

  handleImageFile(file) {
    if (!file) return;

    try {
      const imgUrl = URL.createObjectURL(file);
      if (this.imagePreview) this.imagePreview.src = imgUrl;
      if (this.dropZoneContent) this.dropZoneContent.classList.add('hidden');
      if (this.previewContainer) this.previewContainer.classList.remove('hidden');
      this.processOCR(file);
    } catch(err) {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (this.imagePreview) this.imagePreview.src = e.target.result;
        if (this.dropZoneContent) this.dropZoneContent.classList.add('hidden');
        if (this.previewContainer) this.previewContainer.classList.remove('hidden');
        this.processOCR(file);
      };
      reader.readAsDataURL(file);
    }
  }

  async processOCR(file) {
    if (this.ocrStatusBar) this.ocrStatusBar.classList.remove('hidden');

    try {
      const imgUrl = URL.createObjectURL(file);
      const img = new Image();
      
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = imgUrl;
      });

      // 1. Adaptive Canvas Sharpening & High-Contrast Integer Preprocessing
      const scale = 2.0;
      const canvas = document.createElement('canvas');
      canvas.width = img.width * scale;
      canvas.height = img.height * scale;
      const ctx = canvas.getContext('2d');
      
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

      // Enhance text pixels for OCR clarity (remove background noise, boost text contrast)
      const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
      const d = imgData.data;
      for (let i = 0; i < d.length; i += 4) {
        const r = d[i], g = d[i+1], b = d[i+2];
        const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
        
        // 強いコントラスト調整と二値化によるグラデーションノイズ除去
        // 白文字（高輝度）を黒に、背景（低・中輝度）を白に飛ばす
        let contrastLuma = (luminance - 128) * 4.0 + 128;
        contrastLuma = Math.min(Math.max(contrastLuma, 0), 255);
        
        // 黒文字化 (Invert)
        const finalVal = 255 - contrastLuma;
        d[i] = d[i+1] = d[i+2] = finalVal;
      }
      ctx.putImageData(imgData, 0, 0);

      // Edge Enhancement (Strong Sharpening Kernel)
      const w = canvas.width;
      const h = canvas.height;
      const sharpData = ctx.getImageData(0, 0, w, h);
      const sData = sharpData.data;
      const copy = new Uint8ClampedArray(sData);
      // より強力なエッジ強調カーネル
      const kernel = [-1, -1, -1, -1, 9, -1, -1, -1, -1];
      for (let y = 1; y < h - 1; y++) {
        for (let x = 1; x < w - 1; x++) {
          const idx = (y * w + x) * 4;
          let r = 0, g = 0, b = 0;
          for (let ky = -1; ky <= 1; ky++) {
            for (let kx = -1; kx <= 1; kx++) {
              const kIdx = ((y + ky) * w + (x + kx)) * 4;
              const weight = kernel[(ky + 1) * 3 + (kx + 1)];
              r += copy[kIdx] * weight;
              g += copy[kIdx + 1] * weight;
              b += copy[kIdx + 2] * weight;
            }
          }
          sData[idx] = Math.min(Math.max(r, 0), 255);
          sData[idx+1] = Math.min(Math.max(g, 0), 255);
          sData[idx+2] = Math.min(Math.max(b, 0), 255);
        }
      }
      ctx.putImageData(sharpData, 0, 0);

      const processedDataUrl = canvas.toDataURL('image/png');
      if (this.ocrDebugImg) {
        this.ocrDebugImg.src = processedDataUrl;
      }

      if (typeof Tesseract !== 'undefined') {
        const result = await Tesseract.recognize(processedDataUrl, 'eng+jpn');
        if (this.ocrRawTextOutput) {
          this.ocrRawTextOutput.value = result.data.text || "(認識されたテキストはありません)";
        }
        this.parseOcrTextToStats(result.data.text);
      } else {
        console.warn('Tesseract.js is not loaded. Fallback processing...');
        this.generateStatsFromFile(file);
      }
    } catch(err) {
      console.error('OCR Error:', err);
    } finally {
      if (this.ocrStatusBar) this.ocrStatusBar.classList.add('hidden');
      this.renderStatsSummary();
      this.updateJsonPayload();
    }
  }

  parseOcrTextToStats(text) {
    if (!text) return;

    // 数字の正規化、'O'->'0', 'I'->'1', 'l'->'1', 'S'->'5', 'B'->'8' 等の置換フィルタ
    let normalizedText = text.replace(/[Oo]/g, '0')
                             .replace(/[Il|]/g, '1')
                             .replace(/[S]/g, '5')
                             .replace(/[B]/g, '8')
                             .replace(/[Z]/g, '2');

    const lines = normalizedText.split('\n');
    let updatedStats = [...this.stats];

    lines.forEach(line => {
      // 空白を除去してキーワード判定しやすくする
      let nLine = line.replace(/\s+/g, '');
      
      let type = null;
      if (nLine.includes('歩兵')) type = 'inf';
      else if (nLine.includes('槍') || nLine.includes('騎')) type = 'cav';
      else if (nLine.includes('弓兵')) type = 'lan';

      let stat = null;
      if (nLine.includes('攻撃力')) stat = 'atk';
      else if (nLine.includes('防御力')) stat = 'def';
      else if (nLine.includes('殺傷力')) stat = 'leth';
      else if (nLine.includes('HP') || nLine.includes('ＨＰ')) stat = 'hp';

      if (type && stat) {
        const key = `${type}_${stat}`;
        
        // カンマを含む数値、+や%を含むパターン
        const numPattern = /[+＋]?\s*([\d,]+(?:\.\d+)?)\s*[%％]?/g;
        let matches = [];
        let m;
        while ((m = numPattern.exec(line)) !== null) {
          // カンマを除去してパース
          let numStr = m[1].replace(/,/g, '');
          let val = parseFloat(numStr);
          // 50.0未満の強制破棄ルールは廃止、有効な数値として受け入れる
          if (!isNaN(val)) {
            matches.push(val);
          }
        }

        if (matches.length > 0) {
          const statIndex = updatedStats.findIndex(s => s.key === key);
          if (statIndex !== -1) {
            // 最初の数値を左列、次の数値を右列として割り当て
            updatedStats[statIndex].left = Math.round(matches[0]);
            if (matches.length > 1) {
              updatedStats[statIndex].right = Math.round(matches[1]);
            }
          }
        }
      }
    });

    this.stats = updatedStats;
    this.saveState();
  }

  renderStatsSummary() {
    if (!this.statsSummaryGrid) return;
    this.statsSummaryGrid.innerHTML = '';

    this.stats.forEach((item, index) => {
      const val = this.selectedColumn === 'left' ? item.left : item.right;
      const label = this.selectedColumn === 'left' ? ' [左列]' : ' [右列]';

      const chip = document.createElement('div');
      chip.className = 'stat-chip';
      chip.innerHTML = `
        <span>${item.name}${label}</span>
        <div style="display:flex; align-items:center; gap:4px;">
          <input type="number" step="1" class="form-control stat-edit-input" data-index="${index}" value="${Math.round(val)}" style="width: 80px; text-align: right; padding: 2px 6px; font-weight: bold; color: var(--accent-gold);"> %
        </div>
      `;
      this.statsSummaryGrid.appendChild(chip);
    });

    const editInputs = this.statsSummaryGrid.querySelectorAll('.stat-edit-input');
    editInputs.forEach(input => {
      input.addEventListener('input', (e) => {
        const idx = parseInt(e.target.getAttribute('data-index'));
        const newNum = parseInt(e.target.value, 10) || 0;
        if (this.selectedColumn === 'left') {
          this.stats[idx].left = newNum;
        } else {
          this.stats[idx].right = newNum;
        }
        this.saveState();
        this.updateJsonPayload();
      });
    });
  }

  generateOfficialJson() {
    const getVal = (key) => {
      const found = this.stats.find(s => s.key === key);
      if (!found) return 0;
      return this.selectedColumn === 'left' ? found.left : found.right;
    };

    const infT = parseInt(this.infTier?.value) || 10;
    const infF = parseInt(this.infFc?.value) || 5;

    const cavT = parseInt(this.cavTier?.value) || 10;
    const cavF = parseInt(this.cavFc?.value) || 5;

    const lanT = parseInt(this.lanTier?.value) || 10;
    const lanF = parseInt(this.lanFc?.value) || 5;

    const h1Raw = this.leadHero1?.value || "petra";
    const h2Raw = this.leadHero2?.value || "alcar";
    const h3Raw = this.leadHero3?.value || "marlin";

    const capitalize = (s) => s.charAt(0).toUpperCase() + s.slice(1);

    const h1 = capitalize(h1Raw);
    const h2 = capitalize(h2Raw);
    const h3 = capitalize(h3Raw);

    const selectedLeadHeroes = Array.from(new Set([h1, h2, h3]));

    const j1Name = capitalize(this.joiner1?.value || "amane");
    const j1Skill = parseInt(this.joinerSkill1?.value) || 5;

    const j2Name = capitalize(this.joiner2?.value || "amane");
    const j2Skill = parseInt(this.joinerSkill2?.value) || 5;

    const j3Name = capitalize(this.joiner3?.value || "amane");
    const j3Skill = parseInt(this.joinerSkill3?.value) || 5;

    const j4Name = capitalize(this.joiner4?.value || "amane");
    const j4Skill = parseInt(this.joinerSkill4?.value) || 5;

    const joinersArray = [
      { "id": 0, "name": j1Name, "skill_levels": { "1": j1Skill } },
      { "id": 1, "name": j2Name, "skill_levels": { "1": j2Skill } },
      { "id": 2, "name": j3Name, "skill_levels": { "1": j3Skill } },
      { "id": 3, "name": j4Name, "skill_levels": { "1": j4Skill } }
    ];

    const heroDatabase = {
      "Zoe": { "name": "Zoe", "type": "inf", "stats": { "attack": 240, "defense": 240, "lethality": 125, "health": 214 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 4 },
      "Marlin": { "name": "Marlin", "type": "mark", "stats": { "attack": 199, "defense": 199, "lethality": 199, "health": 123 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 5 },
      "Petra": { "name": "Petra", "type": "lanc", "stats": { "attack": 253, "defense": 253, "lethality": 175, "health": 103 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 3 },
      "Alcar": { "name": "Alcar", "type": "inf", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 0 },
      "Eric": { "name": "Eric", "type": "inf", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 0 },
      "Jaeger": { "name": "Jaeger", "type": "mark", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 0 },
      "Diana": { "name": "Diana", "type": "mark", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": {}, "widget_level": 0 },
      "Rosa": { "name": "Rosa", "type": "mark", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 0 },
      "Amadeus": { "name": "Amadeus", "type": "inf", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 0 },
      "Seth": { "name": "Seth", "type": "inf", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": {}, "widget_level": 0 },
      "Thrud": { "name": "Thrud", "type": "lanc", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 0 },
      "Amane": { "name": "Amane", "type": "inf", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 0 },
      "Chenko": { "name": "Chenko", "type": "inf", "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 }, "skill_levels": { "1": 5, "2": 5, "3": 5 }, "widget_level": 0 }
    };

    const allReferencedHeroes = Array.from(new Set([...selectedLeadHeroes, j1Name, j2Name, j3Name, j4Name]));

    allReferencedHeroes.forEach(hName => {
      if (!heroDatabase[hName]) {
        heroDatabase[hName] = {
          "name": hName,
          "type": "inf",
          "stats": { "attack": 0, "defense": 0, "lethality": 0, "health": 0 },
          "skill_levels": { "1": 5, "2": 5, "3": 5 },
          "widget_level": 0
        };
      }
    });

    const authenticSchema = {
      "name": "bear-formation",
      "stats": {
        "inf": {
          "attack": Math.round(getVal('inf_atk')),
          "defense": Math.round(getVal('inf_def')),
          "lethality": Math.round(getVal('inf_leth')),
          "health": Math.round(getVal('inf_hp'))
        },
        "lanc": {
          "attack": Math.round(getVal('cav_atk')),
          "defense": Math.round(getVal('cav_def')),
          "lethality": Math.round(getVal('cav_leth')),
          "health": Math.round(getVal('cav_hp'))
        },
        "mark": {
          "attack": Math.round(getVal('lan_atk')),
          "defense": Math.round(getVal('lan_def')),
          "lethality": Math.round(getVal('lan_leth')),
          "health": Math.round(getVal('lan_hp'))
        }
      },
      "troops": [
        { "type": "inf", "tier": infT, "fc_level": infF, "quantity": 85326 },
        { "type": "lanc", "tier": cavT, "fc_level": cavF, "quantity": 14221 },
        { "type": "mark", "tier": lanT, "fc_level": lanF, "quantity": 5000 }
      ],
      "heroes": heroDatabase,
      "joiners": joinersArray,
      "stats_include_heroes": true,
      "selectedHeroes": selectedLeadHeroes
    };

    return JSON.stringify(authenticSchema, null, 2);
  }

  updateJsonPayload() {
    if (this.jsonTextArea) {
      this.jsonTextArea.value = this.generateOfficialJson();
    }
  }

  downloadJsonFile() {
    const jsonString = this.generateOfficialJson();
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = 'kingshot_stats.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    if (this.btnDownloadJson) {
      const origText = this.btnDownloadJson.innerHTML;
      this.btnDownloadJson.innerHTML = `<span>✅ kingshot_stats.json を保存しました！</span>`;
      setTimeout(() => { this.btnDownloadJson.innerHTML = origText; }, 2500);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.planAApp = new PlanAApp();
});
