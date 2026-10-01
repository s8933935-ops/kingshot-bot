'use strict';

const assert = require('assert');
const { appendSign, KingShotApiClient, SALT } = require('../src/sgr_bot/kingshot_api_client');

console.log('--- Testing Signature Generation ---');
const testParams = {
  fid: '12345678',
  time: 1727445000
};
const signed = appendSign(testParams);
console.log('Signed params:', signed);
assert.ok(signed.sign, 'Signature must be generated');
assert.strictEqual(signed.sign.length, 32, 'Signature must be 32-char MD5 hex');
assert.strictEqual(signed.fid, '12345678');
assert.strictEqual(signed.time, 1727445000);

console.log('--- Testing API Client Interface ---');
const client = new KingShotApiClient();
assert.strictEqual(typeof client.getPlayerInfo, 'function');
assert.strictEqual(typeof client.getCaptcha, 'function');
assert.strictEqual(typeof client.exchangeGiftCode, 'function');
assert.strictEqual(typeof client.handleRedeemForEngine, 'function');

console.log('✅ kingshot_api_client unit test passed successfully!');
