#!/usr/bin/env node
/**
 * test_consortium_dispatcher.js
 * Phase 2: consortium_dispatcher.js のステートマシンとタスクボード管理の単体検証
 */

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { loadTaskBoard, loadPresets } = require('../scripts/consortium_dispatcher');

console.log("=== [Phase 2: consortium_dispatcher.js 単体検証テスト開始] ===");

// 1. プリセット読み込みテスト
console.log("1. チームプリセット読み込みテスト...");
const presetsData = loadPresets();
assert(presetsData.presets, "プリセットデータが空です");
assert(presetsData.presets['consortium-standard'], "consortium-standard プリセットが存在しません");
assert(presetsData.presets['math-logic-heavy'], "math-logic-heavy プリセットが存在しません");
console.log(`✓ プリセット確認成功 (${Object.keys(presetsData.presets).length} 種類のチームプリセットをロード)`);

// 2. タスクボード同期テスト
console.log("\n2. タスク同期ボード読み込みテスト...");
const board = loadTaskBoard();
assert(Array.isArray(board.tasks), "tasks が配列ではありません");
console.log(`✓ タスクボード確認成功 (登録済みタスク数: ${board.tasks.length})`);

// 3. CLI 一覧表示コマンドテスト
console.log("\n3. CLI 一覧表示コマンド (node consortium_dispatcher.js list) テスト...");
const { spawnSync } = require('child_process');
const listRes = spawnSync('node', ['scripts/consortium_dispatcher.js', 'list'], { encoding: 'utf-8' });
assert.strictEqual(listRes.status, 0, "list コマンドが exit code 0 で終了しませんでした");
assert(listRes.stdout.includes("3社合同タスクボード一覧"), "一覧ヘッダーが出力されていません");
console.log("✓ list コマンド実行成功");

console.log("\n=======================================================");
console.log("🎉 Phase 2: consortium_dispatcher.js 基盤テスト合格 (100% PASS)");
console.log("=======================================================");
