#!/usr/bin/env node
/**
 * claude_bridge.js (Hard-Capped & Quality-Guarded Eco Edition)
 * Antigravity <-> Claude Code CLI 連携グローバルブリッジ
 *
 * 主な機能:
 * 1. コスト暴走・無限再帰防止ハードキャップ（1タスクあたりの最大実行回数制限）
 * 2. プロセスハング防止タイムアウト（180秒自動キル）
 * 3. 難易度Tierに応じたモデル切り替え（Haiku / Sonnet / Opus）
 * 4. 【新機能】エコモード（--eco）: Haikuベースでトークン消費を極小化
 * 5. 【新機能】品質保証ガード: コード省略の絶対禁止・厳格バリデーションプロンプトの自動注入
 * 6. 【新機能】自己修復フォールバック（--out / --test）: テスト失敗時に自動でSonnet昇格＆再生成
 */

const { spawn, execSync } = require('child_process');
const tokenWatcher = require('./token_watcher');
const semanticCache = require('./semantic_cache');
const promptCompressor = require('./prompt_compressor');
const speculativeEngine = require('./speculative_engine');
const fs = require('fs');
const path = require('path');

// 暴走防止用ハードキャップ（安全弁）
const MAX_CALLS_PER_RUN = parseInt(process.env.CLAUDE_BRIDGE_MAX_CALLS || '20', 10);
const CALL_COUNTER_FILE = path.resolve('C:\\Users\\s8933\\.gemini\\config\\council_logs\\.call_counter');
const TIMEOUT_MS = 240000; // 240秒（4分）で自動安全停止

function checkHardCap() {
  let count = 0;
  try {
    if (fs.existsSync(CALL_COUNTER_FILE)) {
      const data = JSON.parse(fs.readFileSync(CALL_COUNTER_FILE, 'utf-8'));
      // 1時間以上前のカウントはリセット
      if (Date.now() - data.timestamp < 3600000) {
        count = data.count;
      }
    }
  } catch (e) {
    count = 0;
  }

  if (count >= MAX_CALLS_PER_RUN) {
    console.error(`[claude_bridge] ⚠️ 安全緊急停止 (Hard-Cap Triggered): 1時間あたりの呼び出し上限 (${MAX_CALLS_PER_RUN}回) に達しました。コスト暴走防止のため自動停止します。解除するには ${CALL_COUNTER_FILE} を削除してください。`);
    process.exit(42);
  }

  // カウント更新
  try {
    fs.writeFileSync(CALL_COUNTER_FILE, JSON.stringify({ count: count + 1, timestamp: Date.now() }), 'utf-8');
  } catch (e) {}
}

function parseArgs() {
  const args = process.argv.slice(2);
  let prompt = '';
  let systemPrompt = '';
  let filePath = null;
  let model = null;
  let isEco = false;
  let isSpeculative = false;
  let isTeamPipeline = false;
  let outPath = null;
  let testCmd = null;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--file' && i + 1 < args.length) {
      filePath = args[++i];
    } else if (args[i] === '--system' && i + 1 < args.length) {
      systemPrompt = args[++i];
    } else if (args[i] === '--model' && i + 1 < args.length) {
      model = args[++i];
    } else if (args[i] === '--tier' && i + 1 < args.length) {
      const tier = args[++i].toLowerCase();
      if (tier === '0' || tier === 'local') {
        model = 'local';
      } else if (tier === 'low' || tier === 'light') {
        model = 'haiku';
      } else if (tier === '4' || tier === 'opus' || tier === 'ultra' || tier === 'extreme') {
        model = 'opus';
      } else {
        model = 'sonnet';
      }
    } else if (args[i] === '--eco') {
      isEco = true;
    } else if (args[i] === '--speculative') {
      isSpeculative = true;
    } else if (args[i] === '--team' || (args[i] === '--pipeline' && args[i + 1] === 'team')) {
      isTeamPipeline = true;
      if (args[i] === '--pipeline') i++;
    } else if (args[i] === '--out' && i + 1 < args.length) {
      outPath = args[++i];
    } else if (args[i] === '--test' && i + 1 < args.length) {
      testCmd = args[++i];
    } else if (!args[i].startsWith('--')) {
      prompt = args[i];
    }
  }

  if (filePath) {
    const fullPath = path.resolve(filePath);
    if (!fs.existsSync(fullPath)) {
      console.error(`[claude_bridge] エラー: ファイルが見つかりません: ${fullPath}`);
      process.exit(1);
    }
    const fileContent = fs.readFileSync(fullPath, 'utf-8');
    prompt = prompt ? `${prompt}\n\n【対象ファイル・指示内容】:\n${fileContent}` : fileContent;
  }

  // エコモード時のモデル設定（未指定なら haiku）
  if (isEco && !model) {
    model = 'haiku';
  }

  // 品質保証ガードプロンプトの注入
  const qualityGuardPrompt = 
    '【品質保証制約】\n' +
    '1. コードの省略（「...」「// 同様」等のプレースホルダー、未実装TODO）は絶対に禁止。完全に動作する全行を出力すること。\n' +
    '2. 境界値・nullチェック・エラーハンドリングを厳密に行い、潜在的バグを排除すること。\n' +
    '3. 出力コードは単体テスト可能で自己完結した構造にすること。\n' +
    '4. 余計な前置きや解説の挨拶は最小限にし、要求された成果物（コードブロック等）を的確に出力すること。';

  if (isEco || outPath) {
    systemPrompt = systemPrompt ? `${systemPrompt}\n\n${qualityGuardPrompt}` : qualityGuardPrompt;
  }

  // Opus (Tier 4) 専用のガードレールプロンプト（トークン暴走防止・設計＆監査特化）
  const opusGuardPrompt = 
    '【Claude Opus (Tier 4: 極限推論) ガードレール制約】\n' +
    '1. あなたは最高峰の最高技術顧問・クオンツ監査官として振る舞ってください。\n' +
    '2. 何百行ものボイラープレートや冗長なコード全行を出力する必要はありません。\n' +
    '3. 「根本原因の数学的・理論的解明」「インターフェース型定義」「アルゴリズム擬似コード」「エッジケース指摘」に集中し、最大2000トークン以内で簡潔に出力してください。実装はローカルAIが担当します。';

  if (model === 'opus') {
    systemPrompt = systemPrompt ? `${systemPrompt}\n\n${opusGuardPrompt}` : opusGuardPrompt;
  }


  return { prompt, systemPrompt, model, isEco, isSpeculative, isTeamPipeline, outPath, testCmd, filePath };
}

function extractCodeBlock(content) {
  const codeBlockRegex = /```(?:[a-zA-Z0-9_-]+)?\s*([\s\S]*?)```/;
  const match = content.match(codeBlockRegex);
  if (match && match[1]) {
    return match[1].trim();
  }
  return content.trim();
}

function executeClaudeOnce(prompt, systemPrompt, model) {
  return new Promise((resolve, reject) => {
    checkHardCap();

    const isWin = process.platform === 'win32';
    let cmdStr = 'claude -p';
    if (model) {
      cmdStr += ` --model ${model}`;
    }
    if (systemPrompt) {
      const escapedSys = systemPrompt.replace(/"/g, '\\"').replace(/\n/g, ' ');
      cmdStr += ` --system-prompt "${escapedSys}"`;
    }

    const cmd = isWin ? 'cmd.exe' : 'claude';
    const args = isWin ? ['/c', cmdStr] : cmdStr.split(' ').slice(1);

    const child = spawn(cmd, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      cwd: process.cwd(),
      env: {
        ...process.env,
        NODE_NO_WARNINGS: '1',
        PYTHONIOENCODING: 'utf-8',
        LANG: 'ja_JP.UTF-8'
      },
      maxBuffer: 50 * 1024 * 1024
    });

    const killTimer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error(`タイムアウト超過 (${TIMEOUT_MS / 1000}秒)`));
    }, TIMEOUT_MS);

    let stdoutData = '';
    let stderrData = '';

    child.stdout.on('data', (chunk) => {
      stdoutData += chunk.toString('utf-8');
    });

    child.stderr.on('data', (chunk) => {
      stderrData += chunk.toString('utf-8');
    });

    child.on('close', (code) => {
      clearTimeout(killTimer);
      if (code === 0) {
        resolve(stdoutData);
      } else {
        reject(new Error(`Claude終了エラー (コード: ${code}): ${stderrData || stdoutData}`));
      }
    });

    child.on('error', (err) => {
      clearTimeout(killTimer);
      reject(err);
    });

    child.stdin.write(prompt, 'utf-8');
    child.stdin.end();
  });
}

async function run() {
  let { prompt, systemPrompt, model, isEco, isSpeculative, isTeamPipeline, outPath, testCmd, filePath } = parseArgs();

  if (!prompt || prompt.trim() === '') {
    console.error('[claude_bridge] 使用法: node claude_bridge.js "プロンプト" [--file パス] [--model haiku|sonnet|opus] [--eco] [--out 出力先パス] [--test "テストコマンド"]');
    process.exit(1);
  }

  const rawOriginalPrompt = prompt;

  // --- 前処理①: セマンティック・キャッシュ照会 (L1/L2 高速照会: 0秒・0トークン) ---
  const cacheResult = semanticCache.lookupCache(prompt, filePath);
  if (cacheResult.hit) {
    console.error(`[claude_bridge] ⚡ [CACHE_HIT] キャッシュヒット！ (${cacheResult.type}, 類似度=${cacheResult.similarity})`);
    console.error(`[claude_bridge] 🚀 0秒・完全0トークンで即座に応答します (保存モデル: ${cacheResult.model})`);

    if (outPath) {
      const codeOnly = extractCodeBlock(cacheResult.response);
      const targetPath = path.resolve(outPath);
      const parentDir = path.dirname(targetPath);
      if (!fs.existsSync(parentDir)) fs.mkdirSync(parentDir, { recursive: true });
      fs.writeFileSync(targetPath, codeOnly, 'utf-8');
      console.error(`[claude_bridge] 💾 キャッシュ出力を保存しました: ${targetPath}`);
    }

    if (testCmd) {
      console.error(`[claude_bridge] 🧪 キャッシュ出力の自動テスト検証を実行中: ${testCmd}`);
      try {
        execSync(testCmd, { stdio: 'pipe', encoding: 'utf-8', cwd: process.cwd() });
        console.error(`[claude_bridge] ✅ キャッシュ出力テスト合格！`);
      } catch (testErr) {
        console.error(`[claude_bridge] ⚠️ キャッシュ検証失敗: キャッシュを破棄し再生成へ移行します...`);
        // キャッシュが無効だったので通常フローへ継続
        cacheResult.hit = false;
      }
    }

    if (cacheResult.hit) {
      process.stdout.write(cacheResult.response);
      process.exit(0);
    }
  }

  // --- 前処理②: 安全プロンプト圧縮 (構文スリム化 & クリティカルバイパス) ---
  const compResult = promptCompressor.compressPrompt(prompt);
  if (compResult.bypassed) {
    console.error('[claude_bridge] 🛡️ [COMPRESS_BYPASS] クリティカル要件のためプロンプト圧縮をバイパスしました (生テキスト100%維持)');
  } else if (compResult.savedChars > 0) {
    console.error(`[claude_bridge] 🗜️ [PROMPT_COMPRESSED] プロンプト安全圧縮適用: -${compResult.savedChars}文字 (${compResult.compressionRatio} 削減)`);
    prompt = compResult.compressed;
  }

  // --- 品質最優先・モデルダウン遮断機能 (Anti-Downgrade Engine) ---
  const criticalKeywords = [
    'ケリー基準', '期待値', '最適ポートフォリオ', 'クオンツ', 'montecarlo',
    '確率統計', 'kelly', 'expected_value', 'regime', 'mutex', 'racecondition',
    'デッドロック', 'semaphore', '排他制御', '並行処理', 'atomic',
    'jwt', '暗号', 'crypto', 'auth', '決済', 'payment', 'migration', '不可逆',
    '@quality-lock'
  ];

  const lowerPrompt = prompt.toLowerCase();
  const isCriticalTask = criticalKeywords.some(kw => lowerPrompt.includes(kw.toLowerCase()));

  if (isCriticalTask && (model === 'local' || model === 'haiku' || model === 'qwen' || model === 'ollama')) {
    console.error('====================================================================');
    console.error(' 🛡️ [QUALITY_GUARD] 品質最優先・モデルダウン完全遮断ガードレール発動！');
    console.error(' - 理由: 高難度数理・並行処理・セキュリティ等のクリティカル要件を検知。');
    console.error(' - 判定: 品質低下を100%防ぐため、安価モデルへのモデルダウンを拒絶します。');
    console.error(' - 決定: Tier 3 (Claude 3.7 Sonnet) を強制維持して実行します。');
    console.error('====================================================================\n');
    model = 'sonnet';
  }


  if (model === 'local' || model === 'qwen' || model === 'ollama') {
    const localBridgePath = path.join(__dirname, 'local_bridge.js');
    console.error('[claude_bridge] 🏠 ローカルAI (Tier 0: Qwen2.5-Coder / Ollama) へ自律ルーティングします (コスト: $0)...');
    try {
      const localArgs = process.argv.slice(2).filter((arg, idx, arr) => {
        if (arg === '--model' && arr[idx + 1] === 'local') return false;
        if (arr[idx - 1] === '--model' && arg === 'local') return false;
        if (arg === '--tier' && (arr[idx + 1] === '0' || arr[idx + 1] === 'local')) return false;
        if (arr[idx - 1] === '--tier' && (arg === '0' || arg === 'local')) return false;
        return true;
      });
      const cmdStr = 'node "' + localBridgePath + '" ' + localArgs.map(a => '"' + a.replace(/"/g, '\\"') + '"').join(' ');
      execSync(cmdStr, { stdio: 'inherit' });
      process.exit(0);
    } catch (localErr) {
      console.error('[claude_bridge] ⚠️ ローカルAI実行でテスト検証または処理エラーが発生しました。');
      
      const escalationReportPath = 'C:\\Users\\s8933\\.gemini\\config\\council_logs\\.last_escalation_report.md';
      let metaReport = '';
      if (fs.existsSync(escalationReportPath)) {
        try {
          metaReport = fs.readFileSync(escalationReportPath, 'utf-8');
          fs.unlinkSync(escalationReportPath); // 1回使い切りでクリーンアップ
          console.error('[claude_bridge] 🧠 [META_COGNITIVE_ESCALATION] Qwen 14Bの敗因分析レポートを検知。Sonnet最頭部へインジェクトします！');
        } catch (e) {}
      }

      if (metaReport) {
        prompt = `${metaReport}\n\n================================================================================\n【元のユーザー要求】:\n${prompt}\n================================================================================`;
      } else {
        console.error('[claude_bridge] 🛡️ 安全装置作動: エラー出力を最大1,500文字に自動カットオフし、Tier 3 (Sonnet) へ昇格します...');
        const rawErr = (localErr.stderr || localErr.stdout || localErr.message || '').toString();
        const safeErr = rawErr.substring(0, 1500);
        prompt = `${prompt}\n\n【前回のローカルAIコードでテストエラーが発生しました】:\nエラー要約 (安全装置により最大1500文字に制限済み):\n${safeErr}\n\nテストが合格するように修正した完全なコードのみを出力してください。`;
      }
      model = 'sonnet';
    }
  }

  // --- Speculative Code Generation (推測的コード生成: Qwen下書き＋Sonnet差分修正) ---
  if (isSpeculative) {
    const gate = speculativeEngine.evaluateComplexityGate(rawOriginalPrompt);
    if (!gate.shouldSpeculate) {
      console.error(`[claude_bridge] 🛡️ [COMPLEXITY_GATE_BYPASS] ${gate.reason}`);
      model = 'sonnet';
    } else {
      console.error('[claude_bridge] ⚡ [SPECULATIVE_MODE] ローカル Qwen 14B による超速ドラフト先行生成中...');
      try {
        const draftCode = await speculativeEngine.generateLocalDraft(rawOriginalPrompt);
        console.error(`[claude_bridge] 📝 ドラフト骨格生成完了 (${draftCode.length}文字)。Sonnet への差分修正プロンプトを構築します...`);
        prompt = speculativeEngine.buildSpeculativePrompt(rawOriginalPrompt, draftCode);
        model = 'sonnet';
      } catch (draftErr) {
        console.error('[claude_bridge] ⚠️ ドラフト生成失敗、通常フローへフォールバック:', draftErr.message);
      }
    }
  }

  // --- Team Pipeline Mode (チームパイプライン: Haiku 前処理/リスク抽出 ➔ Sonnet 設計/実装) ---
  if (isTeamPipeline) {
    console.error('[claude_bridge] 👥 [TEAM_PIPELINE] Claude 陣営チームエージェント発動！');
    console.error('  -> Step 1/2: Claude 3.5 Haiku によるリスク・エッジケース前処理抽出...');
    const riskPrompt = `List 3 to 5 critical failure modes, concurrency issues, or edge cases for the following task. Keep it very concise (bullet points, under 5 lines):\n\n${prompt}`;
    let riskReport = '';
    try {
      riskReport = await executeClaudeOnce(riskPrompt, 'You are an objective Red Team risk analyst. Extract all critical edge cases and failure modes directly.', 'haiku');
      console.error(`  -> Step 1 完了: リスク抽出 (${riskReport.length}文字)`);
    } catch (e) {
      console.error(`  -> Step 1 スキップ: ${e.message}`);
    }

    console.error('  -> Step 2/2: Claude 3.7 Sonnet による堅牢アーキテクチャ設計＆実装...');
    const refinedPrompt = `${prompt}\n\n【Red Team Identified Risks & Edge Cases (Must Address)】:\n${riskReport || 'None identified'}\n\nAddress all risks and provide the complete, robust architectural solution.`;
    currentModel = 'sonnet';
    prompt = refinedPrompt;
  } else {
    currentModel = model || 'haiku';
  }

  if (currentModel === 'opus') {
    console.error('[claude_bridge] 👑 最高峰モデル Claude Opus (Tier 4: 極限推論) が発動されました。ガードレールを適用して実行します...');
  } else if (!isTeamPipeline) {
    console.error(`[claude_bridge] 🚀 実行開始: モデル=${currentModel} (エコモード=${isEco ? '有効' : '標準'})`);
  }

  try {
    let output = await executeClaudeOnce(prompt, systemPrompt, currentModel);

    if (outPath) {
      const codeOnly = extractCodeBlock(output);
      const targetPath = path.resolve(outPath);
      const parentDir = path.dirname(targetPath);
      if (!fs.existsSync(parentDir)) {
        fs.mkdirSync(parentDir, { recursive: true });
      }
      fs.writeFileSync(targetPath, codeOnly, 'utf-8');
      console.error(`[claude_bridge] 💾 出力ファイルを保存しました: ${targetPath}`);
    }

    if (testCmd) {
      console.error(`[claude_bridge] 🧪 自動品質テストを実行中: ${testCmd}`);
      try {
        execSync(testCmd, { stdio: 'pipe', encoding: 'utf-8', cwd: process.cwd() });
        console.error(`[claude_bridge] ✅ 品質テスト合格！(モデル: ${currentModel})`);
      } catch (testError) {
        console.error(`[claude_bridge] ⚠️ 品質テスト失敗: モデル ${currentModel} の出力で検証エラーが発生しました。`);
        console.error(`[claude_bridge] 🔄 フォールバック発動: Tier 3 (Sonnet) へ自動昇格して自己修復します...`);

        const testErrOutput = (testError.stderr || testError.stdout || testError.message).toString();
        const retryPrompt = `${prompt}\n\n【前回の試行コードでテストエラーが発生しました。修正してください】:\nエラー詳細:\n${testErrOutput.substring(0, 1500)}\n\n必ずテストが合格するように修正した完全なコードのみを出力してください。`;

        output = await executeClaudeOnce(retryPrompt, systemPrompt, 'sonnet');

        if (outPath) {
          const codeOnly = extractCodeBlock(output);
          fs.writeFileSync(path.resolve(outPath), codeOnly, 'utf-8');
          console.error(`[claude_bridge] 💾 Sonnetによる修復コードを保存しました: ${outPath}`);
        }

        console.error(`[claude_bridge] 🧪 昇格後の再品質テストを実行中: ${testCmd}`);
        execSync(testCmd, { stdio: 'inherit', cwd: process.cwd() });
        console.error(`[claude_bridge] ✅ Sonnet昇格後の品質テストに合格しました！`);
      }
    }


    // Token Watcher メトリクス記録＆リアルタイム異常監視
    const inputTokEst = Math.ceil(prompt.length / 3.5);
    const outputTokEst = Math.ceil(output.length / 3.5);
    let costRate = currentModel === 'opus' ? 0.000075 : currentModel === 'sonnet' ? 0.000015 : 0.000004;
    tokenWatcher.recordUsage({
      model: currentModel,
      tier: currentModel === 'opus' ? 'Tier 4' : currentModel === 'sonnet' ? 'Tier 3' : 'Tier 2',
      inputTokens: inputTokEst,
      outputTokens: outputTokEst,
      promptLength: prompt.length,
      targetFile: outPath,
      hasTest: !!testCmd,
      costUsd: (inputTokEst + outputTokEst) * costRate,
      status: 'SUCCESS'
    });

    // 後処理: セマンティック・キャッシュへ自動非同期保存
    try {
      semanticCache.storeCache(rawOriginalPrompt, filePath, output, currentModel);
    } catch (_) {}

    process.stdout.write(output);
    process.exit(0);

  } catch (err) {
    console.error(`[claude_bridge] 致命的エラー: ${err.message}`);
    process.exit(1);
  }
}

run();
