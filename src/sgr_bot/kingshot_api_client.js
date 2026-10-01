'use strict';

const crypto = require('crypto');

const SALT = 'mN4!pQs6JrYwV9';
const BASE_URL = 'https://kingshot-giftcode.centurygame.com/api';

/**
 * Generate MD5 Signature for Century Games KingShot API
 * 
 * Algorithm:
 * 1. Sort object keys alphabetically.
 * 2. Join keys and URL-encoded values with '&'.
 * 3. Append secret salt "mN4!pQs6JrYwV9".
 * 4. Generate hex-encoded MD5 digest.
 */
function appendSign(params) {
  const sortedKeys = Object.keys(params).sort();
  const queryStr = sortedKeys.reduce((acc, key) => {
    const val = typeof params[key] === 'object'
      ? JSON.stringify(params[key])
      : encodeURIComponent(params[key]);
    return (acc ? acc + '&' : '') + key + '=' + val;
  }, '');

  const sign = crypto.createHash('md5').update(queryStr + SALT).digest('hex');
  return { sign, ...params };
}

/**
 * Send signed form request to KingShot API
 */
async function sendRequest(endpoint, params = {}) {
  const signedData = appendSign(params);
  const formData = new FormData();
  for (const [key, value] of Object.entries(signedData)) {
    formData.append(key, value);
  }

  const response = await fetch(`${BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Origin': 'https://ks-giftcode.centurygame.com',
      'Referer': 'https://ks-giftcode.centurygame.com/',
      'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    },
    body: formData
  });

  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch (err) {
    return { code: -1, msg: text, httpStatus: response.status };
  }
}

/**
 * KingShot API Client
 */
class KingShotApiClient {
  /**
   * Fetch Player / Character Information
   * @param {string} fid Player ID
   * @returns {Promise<Object>}
   */
  async getPlayerInfo(fid) {
    const res = await sendRequest('/player', {
      fid: String(fid),
      time: Date.now()
    });
    return res;
  }

  /**
   * Fetch CAPTCHA image
   * @param {string} fid Player ID
   * @returns {Promise<Object>}
   */
  async getCaptcha(fid) {
    const res = await sendRequest('/captcha', {
      fid: String(fid),
      time: Date.now()
    });
    return res;
  }

  /**
   * Redeem Gift Code for Player
   * @param {string} fid Player ID
   * @param {string} cdk Gift Code
   * @param {string|number} [kid=''] Kingdom ID (required by KingShot)
   * @param {string} [captchaCode=''] CAPTCHA code (if required)
   * @returns {Promise<Object>}
   */
  async exchangeGiftCode(fid, cdk, kid = '', captchaCode = '') {
    const params = {
      fid: String(fid),
      cdk: String(cdk).trim(),
      time: Math.floor(Date.now() / 1000)
    };
    if (kid) {
      params.kid = String(kid);
    }
    if (captchaCode) {
      params.captcha_code = captchaCode;
    }

    const res = await sendRequest('/gift_code', params);
    return res;
  }

  /**
   * Unified Redeem Handler compatible with SgrRedeemEngine
   * @param {string} fid 
   * @param {string} code 
   * @param {Object} [member]
   * @returns {Promise<{status: string, message: string, raw?: Object}>}
   */
  async handleRedeemForEngine(fid, code, member = {}) {
    try {
      const kid = member.kingshot_kingdom_id || member.kid || '';
      const res = await this.exchangeGiftCode(fid, code, kid);

      // Analyze response code & err_code
      // 0 or 20000: SUCCESS
      // 'RECEIVED.' or 'SAME TYPE EXCHANGE.' or 40009 / 40011: ALREADY_CLAIMED
      // 'CDK EXPIRED.' or 40102 / 40007 / 40014: EXPIRED
      // 'USER INFO ERROR.' or 40004 / 40020: INVALID_ID
      // 'CDK NOT FOUND.' or 40008 (without RECEIVED): INVALID_CODE
      const codeNum = Number(res.code);
      const errNum = Number(res.err_code || 0);
      const msgStr = String(res.msg || '').toUpperCase().trim();

      if (codeNum === 0 || errNum === 20000 || msgStr.includes('SUCCESS')) {
        return {
          status: 'SUCCESS',
          message: res.msg || '引き換えに成功しました！',
          raw: res
        };
      } else if (msgStr.includes('RECEIVED') || msgStr.includes('SAME TYPE') || msgStr.includes('CLAIMED') || errNum === 40009 || errNum === 40011) {
        return {
          status: 'ALREADY_CLAIMED',
          message: '既に受け取り済み（受領済み / 同種交換済）です。',
          raw: res
        };
      } else if (msgStr.includes('EXPIRED') || errNum === 40102 || errNum === 40007 || errNum === 40014) {
        return {
          status: 'EXPIRED',
          message: 'ギフトコードの有効期限が切れています。',
          raw: res
        };
      } else if (msgStr.includes('USER INFO') || (msgStr.includes('NOT FOUND') && msgStr.includes('ID')) || errNum === 40004 || errNum === 40020) {
        return {
          status: 'INVALID_ID',
          message: 'プレイヤー情報エラー（FIDまたは王国番号を確認してください）。',
          raw: res
        };
      } else if (msgStr.includes('CDK NOT FOUND') || errNum === 40008) {
        return {
          status: 'INVALID_CODE',
          message: 'ギフトコードが存在しないか無効です。',
          raw: res
        };
      } else {
        return {
          status: 'FAILED',
          message: res.msg || `エラー (err_code: ${errNum || codeNum})`,
          raw: res
        };
      }
    } catch (err) {
      return {
        status: 'FAILED',
        message: `通信エラー: ${err.message}`
      };
    }
  }
}

module.exports = {
  KingShotApiClient,
  appendSign,
  SALT,
  BASE_URL
};
