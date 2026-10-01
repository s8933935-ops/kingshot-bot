'use strict';

const assert = require('assert');
const path = require('path');
const fs = require('fs');
const { getSgrSlashCommands, isOfficerOrAdmin, isSgrMember, handleSgrCommand } = require('../src/sgr_bot/sgr_commands');
const SgrMemberStore = require('../src/sgr_bot/sgr_member_store');
const { SgrRedeemEngine } = require('../src/sgr_bot/sgr_redeem_engine');

async function testCommands() {
  console.log('🧪 Starting SGR Slash Command and Access Control Tests...\n');

  // 1. Verify Slash Command Builder outputs
  console.log('Test 1: Slash command registration schemas');
  const commands = getSgrSlashCommands();
  assert.strictEqual(commands.length, 6);
  const commandNames = commands.map(c => c.name);
  assert.ok(commandNames.includes('sgr_register'));
  assert.ok(commandNames.includes('sgr_myid'));
  assert.ok(commandNames.includes('sgr_unregister'));
  assert.ok(commandNames.includes('sgr_list'));
  assert.ok(commandNames.includes('sgr_redeem'));
  assert.ok(commandNames.includes('sgr_export'));
  console.log('  ✅ Passed (6 slash commands defined)');

  // 2. Access Control Tests
  console.log('Test 2: Access control functions (isOfficerOrAdmin & isSgrMember)');
  
  // Normal user without roles
  const normalUserInteraction = {
    user: { id: '99999' },
    member: { roles: { cache: new Map() } },
    memberPermissions: { has: () => false }
  };
  assert.strictEqual(isOfficerOrAdmin(normalUserInteraction), false);
  assert.strictEqual(isSgrMember(normalUserInteraction), false);

  // User with SGR role
  const sgrUserInteraction = {
    user: { id: '88888' },
    member: {
      roles: {
        cache: new Map([['role_sgr', { name: 'SGR Member' }]])
      }
    },
    memberPermissions: { has: () => false }
  };
  assert.strictEqual(isOfficerOrAdmin(sgrUserInteraction), false);
  assert.strictEqual(isSgrMember(sgrUserInteraction), true);

  // User with Officer role
  const officerInteraction = {
    user: { id: '77777' },
    member: {
      roles: {
        cache: new Map([['role_off', { name: 'SGR Officer' }]])
      }
    },
    memberPermissions: { has: () => false }
  };
  assert.strictEqual(isOfficerOrAdmin(officerInteraction), true);
  assert.strictEqual(isSgrMember(officerInteraction), true); // Officer inherits member rights
  console.log('  ✅ Passed (Role-based access checks verified)');

  // 3. Command Execution Flow Simulation
  console.log('Test 3: Command execution flow (/sgr_register, /sgr_myid, /sgr_list, /sgr_redeem)');
  const testStorePath = path.join(__dirname, 'scratch', 'test_cmd_store.json');
  if (fs.existsSync(testStorePath)) fs.unlinkSync(testStorePath);

  const memberStore = new SgrMemberStore({ storagePath: testStorePath });
  memberStore.init();

  const redeemEngine = new SgrRedeemEngine({ intervalMs: 10 });

  // A. Register member via simulated interaction
  let replyData = null;
  const mockRegisterInteraction = {
    commandName: 'sgr_register',
    user: { id: 'user_001', username: 'Arthur', tag: 'Arthur#1234' },
    member: { roles: { cache: new Map([['r1', { name: 'SGR' }]]) } },
    memberPermissions: { has: () => false },
    options: {
      getString: (name) => name === 'fid' ? '55667788' : null
    },
    reply: (payload) => { replyData = payload; return Promise.resolve(); }
  };

  await handleSgrCommand(mockRegisterInteraction, memberStore, redeemEngine);
  assert.ok(replyData);
  assert.strictEqual(replyData.ephemeral, true);
  assert.ok(replyData.embeds && replyData.embeds.length === 1);
  const regEmbed = replyData.embeds[0].data;
  assert.ok(regEmbed.title.includes('登録完了'));

  // B. /sgr_myid check
  let myIdReply = null;
  const mockMyIdInteraction = {
    commandName: 'sgr_myid',
    user: { id: 'user_001', username: 'Arthur' },
    options: {},
    reply: (payload) => { myIdReply = payload; return Promise.resolve(); }
  };
  await handleSgrCommand(mockMyIdInteraction, memberStore, redeemEngine);
  assert.ok(myIdReply);
  assert.ok(myIdReply.embeds[0].data.title.includes('登録情報確認'));

  // C. /sgr_list check (Unauthorized normal user)
  let deniedReply = null;
  const mockListDeniedInteraction = {
    commandName: 'sgr_list',
    user: { id: 'user_001', username: 'Arthur' },
    member: { roles: { cache: new Map([['r1', { name: 'SGR' }]]) } },
    memberPermissions: { has: () => false },
    options: { getInteger: () => 1 },
    reply: (payload) => { deniedReply = payload; return Promise.resolve(); }
  };
  await handleSgrCommand(mockListDeniedInteraction, memberStore, redeemEngine);
  assert.ok(deniedReply);
  assert.ok(deniedReply.embeds[0].data.title.includes('アクセス権限がありません'));

  // D. /sgr_list check (Officer user)
  let listReply = null;
  const mockListOfficerInteraction = {
    commandName: 'sgr_list',
    user: { id: 'officer_001', username: 'Commander' },
    member: { roles: { cache: new Map([['r2', { name: 'Officer' }]]) } },
    memberPermissions: { has: () => false },
    options: { getInteger: () => 1 },
    reply: (payload) => { listReply = payload; return Promise.resolve(); }
  };
  await handleSgrCommand(mockListOfficerInteraction, memberStore, redeemEngine);
  assert.ok(listReply);
  assert.ok(listReply.embeds[0].data.title.includes('登録メンバー名簿'));

  // E. /sgr_redeem batch execution (Officer user)
  let editReplyData = null;
  const mockRedeemInteraction = {
    commandName: 'sgr_redeem',
    user: { id: 'officer_001', username: 'Commander' },
    member: { roles: { cache: new Map([['r2', { name: 'Officer' }]]) } },
    memberPermissions: { has: () => false },
    options: { getString: (name) => name === 'code' ? 'GIFT2026' : null },
    deferReply: () => Promise.resolve(),
    editReply: (payload) => { editReplyData = payload; return Promise.resolve(); }
  };
  await handleSgrCommand(mockRedeemInteraction, memberStore, redeemEngine);
  assert.ok(editReplyData);
  assert.ok(editReplyData.embeds[0].data.title.includes('完了レポート'));
  console.log('  ✅ Passed (Full interaction pipeline verified)');

  // Clean up
  if (fs.existsSync(testStorePath)) fs.unlinkSync(testStorePath);

  console.log('\n🎉 ALL SGR COMMAND & ACCESS CONTROL TESTS PASSED!\n');
}

testCommands().catch(err => {
  console.error('❌ Command tests failed:', err);
  process.exit(1);
});
