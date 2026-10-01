#!/usr/bin/env node
/**
 * test_openai_bridge.js
 * Phase 1: openai_bridge.js の単体機能・安全ガードレール動作検証
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { calculateCost, resolveApiKey } = require('../scripts/openai_bridge');

console.log("=== [Phase 1: openai_bridge.js 単体検証テスト開始] ===");

// 1. APIキー解決テスト
console.log("1. APIキー安全解決テスト...");
const apiKey = resolveApiKey();
if (apiKey) {
  console.log(`✓ APIキー解決成功 (Masked: ${apiKey.slice(0, 6)}...${apiKey.slice(-4)})`);
} else {
  console.warn("⚠️ APIキーが検出されませんでした (.env 未設定環境)");
}

// 2. コスト試算ロジック検証
console.log("\n2. コスト計算ロジック検証...");
// GPT-4o-mini: Input $0.15/M, Output $0.60/M
const costMini = calculateCost('gpt-4o-mini', 1000000, 1000000);
assert.strictEqual(costMini.toFixed(2), "0.75", "GPT-4o-mini のコスト計算が正しくありません");
console.log(`✓ GPT-4o-mini (1M in / 1M out): $${costMini.toFixed(4)} (合格)`);

// o3-mini: Input $1.10/M, Output $4.40/M
const costO3 = calculateCost('o3-mini', 1000000, 1000000);
assert.strictEqual(costO3.toFixed(2), "5.50", "o3-mini のコスト計算が正しくありません");
console.log(`✓ o3-mini (1M in / 1M out): $${costO3.toFixed(4)} (合格)`);

// 3. CLI エラーハンドリング検証（空引数の拒絶）
console.log("\n3. 空引数拒否 & ヘルプ表示検証...");
const { spawnSync } = require('child_process');
const emptyRes = spawnSync('node', ['scripts/openai_bridge.js'], { encoding: 'utf-8' });
assert.strictEqual(emptyRes.status, 1, "引数なしの場合は exit code 1 で終了すべきです");
assert(emptyRes.stderr.includes("Usage:"), "Usage ガイドが出力されていません");
console.log("✓ 空引数時の安全停止合格");

// 4. 実機疎通テスト（APIキーが存在する場合のみ実行）
if (apiKey) {
  console.log("\n4. OpenAI API 実機疎通 & Structured Outputs テスト (gpt-4o-mini)...");
  const testRes = spawnSync('node', [
    'scripts/openai_bridge.js',
    'Output a JSON object with key "status" set to "OK" and "ping" set to "pong".',
    '--model', 'gpt-4o-mini',
    '--require-json'
  ], { encoding: 'utf-8', timeout: 30000 });

  if (testRes.status === 0) {
    try {
      const parsed = JSON.parse(testRes.stdout.trim());
      assert.strictEqual(parsed.status, "OK");
      assert.strictEqual(parsed.ping, "pong");
      console.log(`✓ API 疎通 & 厳格 JSON 返却成功:`, parsed);
    } catch (e) {
      console.error(`❌ JSON パース失敗: ${testRes.stdout}`);
      process.exit(1);
    }
  } else {
    console.error(`❌ API 呼出失敗: ${testRes.stderr}`);
    process.exit(1);
  }
}

console.log("\n=======================================================");
console.log("🎉 Phase 1: openai_bridge.js 全単体テスト合格 (100% PASS)");
console.log("=======================================================");
