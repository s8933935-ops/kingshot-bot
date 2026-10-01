'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');
const SgrMemberStore = require('../src/sgr_bot/sgr_member_store');

async function runTests() {
  console.log('🧪 Starting SgrMemberStore Comprehensive Tests...\n');
  const testStoragePath = path.join(__dirname, '..', 'scratch', 'test_sgr_members.json');

  // Clean up any old test file
  if (fs.existsSync(testStoragePath)) {
    fs.unlinkSync(testStoragePath);
  }

  // 1. Initialization
  console.log('Test 1: Store initialization and empty file creation');
  const store = new SgrMemberStore({ storagePath: testStoragePath });
  store.init();
  assert.strictEqual(fs.existsSync(testStoragePath), true, 'Storage file should exist after init');
  assert.strictEqual(store.getAllActiveMembers().length, 0, 'Initial active count should be 0');
  console.log('  ✅ Passed');

  // 2. Member Registration
  console.log('Test 2: Registering members');
  const res1 = store.register('100000000000000001', '12345678', 'PlayerOne', 'SGR Vanguard');
  assert.strictEqual(res1.success, true);
  assert.strictEqual(res1.isNew, true);
  assert.strictEqual(res1.member.kingshot_player_id, '12345678');
  assert.strictEqual(res1.member.discord_username, 'PlayerOne');

  const res2 = store.register('100000000000000002', '87654321', 'PlayerTwo', 'SGR Officer');
  assert.strictEqual(res2.success, true);
  assert.strictEqual(res2.isNew, true);
  console.log('  ✅ Passed');

  // 3. Validation: Invalid FID
  console.log('Test 3: Rejecting invalid FID format');
  const invalidRes = store.register('100000000000000003', '12', 'ShortIdUser'); // too short (<4)
  assert.strictEqual(invalidRes.success, false);
  assert.strictEqual(invalidRes.error, 'INVALID_FID_FORMAT');
  console.log('  ✅ Passed');

  // 4. Duplicate FID Conflict Check
  console.log('Test 4: Rejecting duplicate FID collision between different users');
  const dupRes = store.register('100000000000000004', '12345678', 'Impostor');
  assert.strictEqual(dupRes.success, false);
  assert.strictEqual(dupRes.error, 'FID_ALREADY_REGISTERED');
  assert.strictEqual(dupRes.conflictUser, 'PlayerOne');
  console.log('  ✅ Passed');

  // 5. Updating an Existing Member's FID
  console.log('Test 5: Updating existing member FID');
  const updateRes = store.register('100000000000000001', '99999999', 'PlayerOneRenamed');
  assert.strictEqual(updateRes.success, true);
  assert.strictEqual(updateRes.updated, true);
  assert.strictEqual(updateRes.member.kingshot_player_id, '99999999');
  assert.strictEqual(updateRes.member.discord_username, 'PlayerOneRenamed');
  console.log('  ✅ Passed');

  // 6. Lookups
  console.log('Test 6: Member lookups (by Discord ID and by FID)');
  const m1 = store.getMember('100000000000000001');
  assert.strictEqual(m1.kingshot_player_id, '99999999');

  const mByFid = store.getMemberByFid('87654321');
  assert.strictEqual(mByFid.discord_user_id, '100000000000000002');
  console.log('  ✅ Passed');

  // 7. Unregister (Soft Delete)
  console.log('Test 7: Unregister member (soft-delete)');
  const unregRes = store.unregister('100000000000000002');
  assert.strictEqual(unregRes.success, true);
  assert.strictEqual(store.getMember('100000000000000002'), null, 'Unregistered user should not appear in getMember');
  assert.strictEqual(store.getAllActiveMembers().length, 1, 'Active members should now be 1');

  const stats = store.getStats();
  assert.strictEqual(stats.total, 2);
  assert.strictEqual(stats.active, 1);
  assert.strictEqual(stats.inactive, 1);
  console.log('  ✅ Passed');

  // 8. Re-registration of unregistered user
  console.log('Test 8: Re-registering previously unregistered user');
  const reRegRes = store.register('100000000000000002', '87654321', 'PlayerTwo');
  assert.strictEqual(reRegRes.success, true);
  assert.strictEqual(reRegRes.member.active_flag, true);
  assert.strictEqual(store.getAllActiveMembers().length, 2);
  console.log('  ✅ Passed');

  // 9. Bulk Import & CSV/JSON Export
  console.log('Test 9: Bulk import and CSV/JSON export');
  const bulkData = [
    { discord_user_id: '100000000000000003', kingshot_player_id: '11112222', discord_username: 'PlayerThree' },
    { discord_user_id: '100000000000000004', kingshot_player_id: '33334444', discord_username: 'PlayerFour' },
    { discord_user_id: '100000000000000005', kingshot_player_id: 'invalid', discord_username: 'PlayerFive' },
  ];
  const bulkRes = store.bulkImport(bulkData);
  assert.strictEqual(bulkRes.imported, 3);
  assert.strictEqual(store.getAllActiveMembers().length, 5);

  const csv = store.exportToCSV();
  assert.ok(csv.includes('PlayerOneRenamed'));
  assert.ok(csv.includes('99999999'));
  assert.ok(csv.includes('PlayerThree'));

  const json = store.exportToJSON();
  const parsed = JSON.parse(json);
  assert.strictEqual(parsed.length, 5);
  console.log('  ✅ Passed');

  // 10. Persistence Check (New Instance)
  console.log('Test 10: Persistence verification across process/instance reload');
  const reloadedStore = new SgrMemberStore({ storagePath: testStoragePath });
  reloadedStore.init();
  const reloadedMembers = reloadedStore.getAllActiveMembers();
  assert.strictEqual(reloadedMembers.length, 5);
  assert.strictEqual(reloadedStore.getMember('100000000000000001').kingshot_player_id, '99999999');
  console.log('  ✅ Passed');

  // Clean up scratch file
  if (fs.existsSync(testStoragePath)) {
    fs.unlinkSync(testStoragePath);
  }

  console.log('\n🎉 ALL 10 TESTS PASSED SUCCESSFULLY! SgrMemberStore is fully verified.\n');
}

runTests().catch(err => {
  console.error('❌ Test failed with error:', err);
  process.exit(1);
});
