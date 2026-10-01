'use strict';

const assert = require('assert');
const SlidingWindowRateLimiter = require('../src/sgr_bot/SlidingWindowRateLimiter');

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function runTests() {
  console.log('================================================================');
  console.log('🧪 SlidingWindowRateLimiter 極限ストレステスト開始');
  console.log('================================================================\n');

  // Test 1: 即時バースト制限 (tryAcquire)
  {
    console.log('Test 1: 同一ミリ秒でのバースト制限 (limit: 5, windowMs: 100)');
    const limiter = new SlidingWindowRateLimiter({ limit: 5, windowMs: 100 });
    let passed = 0;
    let rejected = 0;

    for (let i = 0; i < 15; i++) {
      if (limiter.tryAcquire(1)) {
        passed++;
      } else {
        rejected++;
      }
    }

    assert.strictEqual(passed, 5, `通過数は厳密に5でなければならない (実際: ${passed})`);
    assert.strictEqual(rejected, 10, `拒否数は厳密に10でなければならない (実際: ${rejected})`);
    assert.strictEqual(limiter.getRemainingTokens(), 0, '残りトークンは0であるべき');
    limiter.destroy();
    console.log('  -> PASS: バースト制限が厳密に機能しました\n');
  }

  // Test 2: スライディング時間経過後の回復
  {
    console.log('Test 2: スライディングウィンドウ時間経過後のトークン回復');
    const limiter = new SlidingWindowRateLimiter({ limit: 3, windowMs: 50 });

    assert.strictEqual(limiter.tryAcquire(3), true, '初期3トークン取得可能');
    assert.strictEqual(limiter.tryAcquire(1), false, '枠枯渇で拒否されるべき');

    // 60ms待機（ウィンドウ外へ押し出す）
    await sleep(65);

    assert.strictEqual(limiter.getRemainingTokens(), 3, '65ms後に3トークン全回復しているべき');
    assert.strictEqual(limiter.tryAcquire(2), true, '回復後に2トークン取得可能');
    limiter.destroy();
    console.log('  -> PASS: スライディング回復が正確に動作しました\n');
  }

  // Test 3: acquire 非同期キューイング
  {
    console.log('Test 3: acquire() による枠空き待ちと順次処理');
    const limiter = new SlidingWindowRateLimiter({ limit: 2, windowMs: 50 });
    const executedTimes = [];

    // 最初に2枠を消費
    assert.strictEqual(limiter.tryAcquire(2), true);

    const p1 = limiter.acquire(1).then(() => executedTimes.push(Date.now()));
    const p2 = limiter.acquire(1).then(() => executedTimes.push(Date.now()));

    await Promise.all([p1, p2]);
    assert.strictEqual(executedTimes.length, 2);
    limiter.destroy();
    console.log('  -> PASS: 非同期待機キューが正常に解決されました\n');
  }

  // Test 4: 100並行高負荷ストレステスト
  {
    console.log('Test 4: 100並行タスクでのレート制限厳守テスト (limit: 20, windowMs: 100)');
    const limiter = new SlidingWindowRateLimiter({ limit: 20, windowMs: 100 });
    const totalRequests = 100;
    const timestamps = [];

    const tasks = Array.from({ length: totalRequests }, () => async () => {
      await limiter.acquire(1, 10000); // 最大10秒待機
      timestamps.push(Date.now());
    });

    await Promise.all(tasks.map(t => t()));

    assert.strictEqual(timestamps.length, totalRequests, '100リクエストすべて完了');

    // 任意の100ms区間において、処理数が20を超過していないかを全数スキャン検証！
    let maxInAnyWindow = 0;
    for (let i = 0; i < timestamps.length; i++) {
      const t = timestamps[i];
      const count = timestamps.filter(ts => ts >= t && ts < t + 100).length;
      maxInAnyWindow = Math.max(maxInAnyWindow, count);
    }

    console.log(`  ✓ 100並行中、任意の100ms区間での最大実行数: ${maxInAnyWindow} (上限設定: 20)`);
    assert(maxInAnyWindow <= 20, `任意の100ms区間で20を超過してはならない (最大: ${maxInAnyWindow})`);
    limiter.destroy();
    console.log('  -> PASS: 100並行下でも設定レートを1件も超過せず完璧に制御されました！\n');
  }

  // Test 5: メモリリーク検証 (10,000回アクセス)
  {
    console.log('Test 5: メモリリーク検証 (10,000回連続アクセス)');
    const limiter = new SlidingWindowRateLimiter({ limit: 50, windowMs: 50 });
    
    for (let i = 0; i < 10000; i++) {
      limiter.tryAcquire(1);
    }

    await sleep(60); // 全て期限切れにする
    limiter.getRemainingTokens(); // purge発動

    const bucketCount = limiter._buckets.size;
    console.log(`  ✓ 10,000回アクセス後の残存バケット数: ${bucketCount}`);
    assert.strictEqual(bucketCount, 0, '古いバケットは全てパージされ0個でなければならない');
    limiter.destroy();
    console.log('  -> PASS: メモリリークなし (バケット完全解放)\n');
  }

  console.log('🎉 全5つの過酷なストレステストが完全合格 (ALL PASS) しました！');
}

runTests().catch(err => {
  console.error('❌ テスト失敗:', err);
  process.exit(1);
});
