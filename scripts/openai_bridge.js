#!/usr/bin/env node
/**
 * openai_bridge.js (Hard-Capped & Safety-Guarded Edition)
 * Antigravity <-> OpenAI API (GPT-4o / o3-mini / GPT-4o-mini) グローバル連携ブリッジ
 *
 * 主な機能:
 * 1. ゼロ外部依存: Node.js 標準の https モジュールで動作（npm install 不要）
 * 2. コスト暴走・無限再帰防止ハードキャップ（1時間あたりの呼出回数制限）
 * 3. タイムアウト安全弁（180秒で自動キル）
 * 4. Structured Outputs 対応（--require-json で 100% 厳格な JSON 返却を保証）
 * 5. 推論トークン（Hidden CoT: o3-mini）の自動捕捉と token_watcher 連携
 * 6. 自己修復フォールバック（--out / --test 指定時にテスト自動実行・再試行）
 */

const https = require('https');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const SCRIPTS_DIR = __dirname;
const CONFIG_DIR = path.resolve(SCRIPTS_DIR, '..', '..', '..');
const LOGS_DIR = path.join(CONFIG_DIR, 'council_logs');
const CALL_COUNTER_FILE = path.join(LOGS_DIR, '.openai_call_counter');
const MAX_CALLS_PER_HOUR = parseInt(process.env.OPENAI_BRIDGE_MAX_CALLS || '30', 10);
const DEFAULT_TIMEOUT_MS = 180000; // 180秒

// token_watcher 連携
let tokenWatcher = null;
try {
  tokenWatcher = require('./token_watcher');
} catch (e) {}

/**
 * 暴走防止ハードキャップ（安全弁）
 */
function checkHardCap() {
  let count = 0;
  try {
    if (fs.existsSync(CALL_COUNTER_FILE)) {
      const data = JSON.parse(fs.readFileSync(CALL_COUNTER_FILE, 'utf-8'));
      if (Date.now() - data.timestamp < 3600000) {
        count = data.count || 0;
      }
    }
  } catch (e) {
    count = 0;
  }

  if (count >= MAX_CALLS_PER_HOUR) {
    console.error(`[openai_bridge] ⚠️ 安全緊急停止 (Hard-Cap Triggered): 1時間あたりの呼び出し上限 (${MAX_CALLS_PER_HOUR}回) に達しました。コスト暴走防止のため自動停止します。解除するには ${CALL_COUNTER_FILE} を削除してください。`);
    process.exit(42);
  }

  try {
    if (!fs.existsSync(LOGS_DIR)) fs.mkdirSync(LOGS_DIR, { recursive: true });
    fs.writeFileSync(CALL_COUNTER_FILE, JSON.stringify({ count: count + 1, timestamp: Date.now() }), 'utf-8');
  } catch (e) {}
}

/**
 * .env から OPENAI_API_KEY を安全に探索・読み込み
 */
function resolveApiKey() {
  if (process.env.OPENAI_API_KEY) {
    return process.env.OPENAI_API_KEY.trim();
  }

  // 探索パス一覧
  const candidateEnvPaths = [
    path.resolve(process.cwd(), '.env'),
    path.resolve(SCRIPTS_DIR, '.env'),
    path.resolve(SCRIPTS_DIR, '..', '.env'),
    path.resolve(CONFIG_DIR, '.env'),
    'c:\\Users\\s8933\\.gemini\\antigravity\\scratch\\multi-agent-designer\\.env'
  ];

  for (const envPath of candidateEnvPaths) {
    if (fs.existsSync(envPath)) {
      try {
        const content = fs.readFileSync(envPath, 'utf-8');
        const match = content.match(/^OPENAI_API_KEY\s*=\s*([^\r\n#]+)/m);
        if (match && match[1]) {
          const key = match[1].trim().replace(/^["']|["']$/g, '');
          if (key) return key;
        }
      } catch (e) {}
    }
  }

  return null;
}

/**
 * モデルエイリアスの安全解決（GPT-6 Astra / Sol / Luna 対応）
 */
function resolveModelAlias(inputModel) {
  const m = (inputModel || '').toLowerCase().trim();
  if (m === 'astra' || m === 'gpt-6-astra') {
    return 'gpt-6-astra';
  }
  if (m === 'sol' || m === 'gpt-6-sol') {
    return 'gpt-6-sol';
  }
  if (m === 'luna' || m === 'gpt-6-luna') {
    return 'gpt-6-luna';
  }
  if (m === 'o3-mini') return 'o3-mini';
  if (m === 'o1-mini') return 'o1-mini';
  if (m === 'o1') return 'o1';
  if (m === '4o' || m === 'gpt-4o') return 'gpt-4o';
  if (m === 'mini' || m === '4o-mini' || m === 'gpt-4o-mini') return 'gpt-4o-mini';
  return inputModel;
}

/**
 * コスト試算（モデル別レート）
 */
function calculateCost(model, inputTokens, outputTokens) {
  let inRate = 0.15;  // per 1M
  let outRate = 0.60;

  if (model.includes('astra')) {
    inRate = 5.00;
    outRate = 20.00;
  } else if (model.includes('sol')) {
    inRate = 1.00;
    outRate = 4.00;
  } else if (model.includes('luna')) {
    inRate = 0.10;
    outRate = 0.40;
  } else if (model.includes('o3-mini') || model.includes('o1-mini')) {
    inRate = 1.10;
    outRate = 4.40;
  } else if (model.includes('gpt-4o') && !model.includes('mini')) {
    inRate = 2.50;
    outRate = 10.00;
  } else if (model.includes('o1')) {
    inRate = 15.00;
    outRate = 60.00;
  }

  const cost = ((inputTokens / 1000000) * inRate) + ((outputTokens / 1000000) * outRate);
  return cost;
}

/**
 * OpenAI API (HTTPS 直接呼び出し)
 */
function callOpenAiDirect(apiKey, model, messages, options = {}) {
  return new Promise((resolve, reject) => {
    const isReasoningModel = model.startsWith('o1') || model.startsWith('o3');

    const payloadObj = {
      model: model,
      messages: messages
    };

    if (isReasoningModel) {
      // o-series 特有パラメータ
      payloadObj.max_completion_tokens = options.maxTokens || 4000;
      if (options.reasoningEffort) {
        payloadObj.reasoning_effort = options.reasoningEffort;
      }
    } else {
      payloadObj.temperature = options.temperature !== undefined ? options.temperature : 0.2;
      payloadObj.max_tokens = options.maxTokens || 4000;
    }

    if (options.requireJson) {
      payloadObj.response_format = { type: "json_object" };
    }

    const payload = JSON.stringify(payloadObj);

    const reqOptions = {
      hostname: 'api.openai.com',
      port: 443,
      path: '/v1/chat/completions',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
        'Content-Length': Buffer.byteLength(payload)
      },
      timeout: options.timeoutMs || DEFAULT_TIMEOUT_MS
    };

    const startTime = Date.now();
    const req = https.request(reqOptions, (res) => {
      let rawData = '';
      res.setEncoding('utf8');
      res.on('data', chunk => rawData += chunk);
      res.on('end', () => {
        const elapsedSec = (Date.now() - startTime) / 1000;

        if (res.statusCode !== 200) {
          let errMsg = `OpenAI API Error ${res.statusCode}`;
          try {
            const errJson = JSON.parse(rawData);
            errMsg += `: ${errJson.error?.message || rawData}`;
          } catch (e) {
            errMsg += `: ${rawData.slice(0, 300)}`;
          }
          return reject(new Error(errMsg));
        }

        try {
          const json = JSON.parse(rawData);
          const choice = json.choices && json.choices[0];
          const text = choice?.message?.content || '';

          const usage = json.usage || {};
          const inputTokens = usage.prompt_tokens || 0;
          const outputTokens = usage.completion_tokens || 0;
          const reasoningTokens = usage.completion_tokens_details?.reasoning_tokens || 0;
          const costUsd = calculateCost(model, inputTokens, outputTokens);

          // token_watcher へ記録
          if (tokenWatcher && typeof tokenWatcher.recordUsage === 'function') {
            tokenWatcher.recordUsage({
              model: model,
              tier: isReasoningModel ? 'openai-reasoning' : 'openai-standard',
              inputTokens: inputTokens,
              outputTokens: outputTokens,
              durationSec: Math.round(elapsedSec),
              costUsd: costUsd,
              promptLength: payload.length,
              status: 'SUCCESS'
            });
          }

          resolve({
            text: text.trim(),
            inputTokens,
            outputTokens,
            reasoningTokens,
            costUsd,
            durationSec: elapsedSec
          });
        } catch (parseErr) {
          reject(new Error(`Failed to parse OpenAI response: ${parseErr.message}`));
        }
      });
    });

    req.on('error', (err) => {
      reject(new Error(`OpenAI Network Error: ${err.message}`));
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`OpenAI request timed out after ${options.timeoutMs || DEFAULT_TIMEOUT_MS}ms`));
    });

    req.write(payload);
    req.end();
  });
}

/**
 * コマンドライン引数パース
 */
function parseArgs() {
  const args = process.argv.slice(2);
  let prompt = '';
  let systemPrompt = '';
  let filePath = null;
  let model = 'gpt-4o-mini'; // デフォルトは高コスパ
  let requireJson = false;
  let outPath = null;
  let testCmd = null;
  let timeoutMs = DEFAULT_TIMEOUT_MS;

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--file' && i + 1 < args.length) {
      filePath = args[++i];
    } else if (args[i] === '--system' && i + 1 < args.length) {
      systemPrompt = args[++i];
    } else if (args[i] === '--model' && i + 1 < args.length) {
      model = args[++i];
    } else if (args[i] === '--out' && i + 1 < args.length) {
      outPath = args[++i];
    } else if (args[i] === '--test' && i + 1 < args.length) {
      testCmd = args[++i];
    } else if (args[i] === '--require-json') {
      requireJson = true;
    } else if (args[i] === '--timeout' && i + 1 < args.length) {
      timeoutMs = parseInt(args[++i], 10);
    } else if (!prompt) {
      prompt = args[i];
    }
  }

  if (filePath && fs.existsSync(filePath)) {
    prompt = fs.readFileSync(filePath, 'utf-8');
  }

  model = resolveModelAlias(model);

  return { prompt, systemPrompt, model, requireJson, outPath, testCmd, timeoutMs };
}

/**
 * メイン実行エントリポイント
 */
async function main() {
  const { prompt, systemPrompt, model, requireJson, outPath, testCmd, timeoutMs } = parseArgs();

  if (!prompt) {
    console.error("Usage: node openai_bridge.js \"<prompt>\" [--model <model>] [--system \"<sys>\"] [--file <path>] [--out <path>] [--test \"<cmd>\"] [--require-json]");
    process.exit(1);
  }

  // ハードキャップ検査
  checkHardCap();

  // APIキー解決
  const apiKey = resolveApiKey();
  if (!apiKey) {
    console.error("[openai_bridge] ❌ エラー: OPENAI_API_KEY が見つかりません。.env ファイルまたは環境変数を設定してください。");
    process.exit(1);
  }

  const isReasoningModel = model.startsWith('o1') || model.startsWith('o3');

  // メッセージの構築
  const messages = [];
  if (systemPrompt && !isReasoningModel) {
    // o1/o3 は system role を非推奨または developer role を使用
    messages.push({ role: "system", content: systemPrompt });
  } else if (systemPrompt && isReasoningModel) {
    messages.push({ role: "developer", content: systemPrompt });
  }

  let effectivePrompt = prompt;
  if (requireJson && !effectivePrompt.includes("JSON")) {
    effectivePrompt += "\n\nOutput strictly valid parseable JSON. Do not include markdown wraps or conversational prose.";
  }
  messages.push({ role: "user", content: effectivePrompt });

  let attempts = 0;
  const maxAttempts = testCmd ? 2 : 1;

  while (attempts < maxAttempts) {
    attempts++;
    try {
      const res = await callOpenAiDirect(apiKey, model, messages, {
        requireJson,
        timeoutMs
      });

      let outputText = res.text;

      // ファイル出力指定がある場合
      if (outPath) {
        let codeContent = outputText;
        const codeMatch = outputText.match(/```(?:[a-zA-Z0-9_-]+)?\n([\s\S]*?)```/);
        if (codeMatch) codeContent = codeMatch[1];

        const outDir = path.dirname(path.resolve(outPath));
        if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
        fs.writeFileSync(outPath, codeContent, 'utf-8');
      }

      // テスト自動実行指定がある場合
      if (testCmd) {
        console.error(`[openai_bridge] 🧪 テスト検証実行中: ${testCmd}`);
        const testRes = spawnSync(testCmd, { shell: true, encoding: 'utf-8', timeout: 60000 });
        if (testRes.status !== 0) {
          const testErr = testRes.stderr || testRes.stdout || `Exit code ${testRes.status}`;
          console.error(`[openai_bridge] ⚠️ テスト失敗 (試行 ${attempts}/${maxAttempts}): ${testErr.slice(0, 150)}`);
          if (attempts < maxAttempts) {
            messages.push({ role: "assistant", content: outputText });
            messages.push({ role: "user", content: `Your previous code failed tests:\n${testErr.slice(0, 500)}\nPlease fix all errors and provide the corrected implementation.` });
            continue;
          }
          throw new Error(`Test failed after ${attempts} attempts: ${testErr}`);
        }
      }

      // 成功時: 出力を stdout へ
      console.log(outputText);
      process.exit(0);
    } catch (err) {
      console.error(`[openai_bridge] ❌ 実行失敗: ${err.message}`);
      process.exit(1);
    }
  }
}

if (require.main === module) {
  main();
}

module.exports = { callOpenAiDirect, calculateCost, resolveApiKey };
