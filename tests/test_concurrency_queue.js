'use strict';

const assert = require('assert');
const ConcurrencyQueue = require('../src/sgr_bot/ConcurrencyQueue');

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runTests() {
  console.log('=== ConcurrencyQueue テスト開始 ===\n');

  // Test 1: 同時実行数制限の検証
  {
    console.log('Test 1: 同時実行数制限 (concurrency = 2)');
    const queue = new ConcurrencyQueue({ concurrency: 2 });
    let maxConcurrent = 0;
    let currentRunning = 0;

    const tasks = Array.from({ length: 6 }, (_, i) => async () => {
      currentRunning++;
      maxConcurrent = Math.max(maxConcurrent, currentRunning);
      await sleep(50);
      currentRunning--;
      return i;
    });

    const results = await queue.addAll(tasks);
    assert.strictEqual(maxConcurrent, 2, `最大同時実行数は2でなければならない (実際: ${maxConcurrent})`);
    assert.deepStrictEqual(results, [0, 1, 2, 3, 4, 5]);
    console.log('  -> PASS: 最大同時実行数2が厳密に維持されました\n');
  }

  // Test 2: 優先度制御 (Priority)
  {
    console.log('Test 2: 優先度順の実行制御');
    const queue = new ConcurrencyQueue({ concurrency: 1, autoStart: false });
    const executedOrder = [];

    queue.add(async () => { executedOrder.push('low'); }, { priority: 1 });
    queue.add(async () => { executedOrder.push('high'); }, { priority: 10 });
    queue.add(async () => { executedOrder.push('medium'); }, { priority: 5 });

    queue.start();
    await queue.onIdle();

    assert.deepStrictEqual(executedOrder, ['high', 'medium', 'low']);
    console.log('  -> PASS: 優先度順 (high -> medium -> low) に実行されました\n');
  }

  // Test 3: リトライ機能
  {
    console.log('Test 3: エラー発生時のリトライ機能');
    const queue = new ConcurrencyQueue({
      concurrency: 1,
      retryDelay: () => 10,
    });

    let attempts = 0;
    const result = await queue.add(async () => {
      attempts++;
      if (attempts < 3) {
        throw new Error('一時的エラー');
      }
      return '成功';
    }, { retries: 3 });

    assert.strictEqual(attempts, 3);
    assert.strictEqual(result, '成功');
    console.log('  -> PASS: 3回目のリトライで正常に成功しました\n');
  }

  // Test 4: onIdle 待機
  {
    console.log('Test 4: onIdle() による全タスク完了の検知');
    const queue = new ConcurrencyQueue({ concurrency: 2 });
    let completed = 0;

    for (let i = 0; i < 3; i++) {
      queue.add(async () => {
        await sleep(30);
        completed++;
      });
    }

    await queue.onIdle();
    assert.strictEqual(completed, 3);
    console.log('  -> PASS: onIdle() で全タスクの完了を検知しました\n');
  }

  console.log('🎉 全テストがパスしました！ Antigravity & Claude の連携は完璧です。');
}

runTests().catch((err) => {
  console.error('テスト失敗:', err);
  process.exit(1);
});
