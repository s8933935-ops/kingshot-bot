'use strict';

const assert = require('assert');
const { SgrRedeemEngine, RedeemStatus } = require('../src/sgr_bot/sgr_redeem_engine');

async function runEngineTests() {
  console.log('🧪 Starting SgrRedeemEngine Tests...\n');

  // Test 1: Basic batch execution and result counting
  console.log('Test 1: Batch execution with status categories');
  const engine = new SgrRedeemEngine({ intervalMs: 20 }); // Fast interval for testing

  const mockMembers = [
    { kingshot_player_id: '12345671', discord_user_id: '101', discord_username: 'Alpha' },
    { kingshot_player_id: '12345670', discord_user_id: '102', discord_username: 'Beta' },   // ends with 0 -> ALREADY_CLAIMED
    { kingshot_player_id: '99912345', discord_user_id: '103', discord_username: 'Gamma' },  // starts with 999 -> INVALID_ID
    { kingshot_player_id: '12345672', discord_user_id: '104', discord_username: 'Delta' }   // SUCCESS
  ];

  let progressCalls = 0;
  const report = await engine.executeBatch(mockMembers, 'KINGS_HERO_2026', {
    onProgress: (p) => {
      progressCalls++;
      assert.ok(p.processed <= p.total);
    }
  });

  assert.strictEqual(report.total, 4);
  assert.strictEqual(report.processed, 4);
  assert.strictEqual(report.counts[RedeemStatus.SUCCESS], 2);
  assert.strictEqual(report.counts[RedeemStatus.ALREADY_CLAIMED], 1);
  assert.strictEqual(report.counts[RedeemStatus.INVALID_ID], 1);
  assert.strictEqual(progressCalls, 4);
  console.log('  ✅ Passed (Success: 2, Claimed: 1, Invalid: 1)');

  // Test 2: Expired Code handling
  console.log('Test 2: Expired code handling');
  const expiredReport = await engine.executeBatch(mockMembers.slice(0, 2), 'EXPIRED_CODE');
  assert.strictEqual(expiredReport.counts[RedeemStatus.EXPIRED], 2);
  console.log('  ✅ Passed');

  // Test 3: Concurrency prevention (cannot start two concurrent batches)
  console.log('Test 3: Rejecting simultaneous batch execution');
  const engineSlow = new SgrRedeemEngine({ intervalMs: 300 });
  const promise1 = engineSlow.executeBatch(mockMembers, 'TEST_CODE');
  let threw = false;
  try {
    await engineSlow.executeBatch(mockMembers, 'TEST_CODE_2');
  } catch (err) {
    threw = true;
    assert.ok(err.message.includes('in progress'));
  }
  assert.strictEqual(threw, true, 'Should throw error when batch is already running');
  await promise1;
  console.log('  ✅ Passed');

  console.log('\n🎉 ALL SgrRedeemEngine TESTS PASSED SUCCESSFULLY!\n');
}

runEngineTests().catch(err => {
  console.error('❌ Engine test failed:', err);
  process.exit(1);
});
