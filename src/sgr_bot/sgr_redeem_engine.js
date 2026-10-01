'use strict';

const ConcurrencyQueue = require('./ConcurrencyQueue');

/**
 * Result Status Enum
 */
const RedeemStatus = {
  SUCCESS: 'SUCCESS',                   // 引き換え成功
  ALREADY_CLAIMED: 'ALREADY_CLAIMED',   // 既に受け取り済み
  EXPIRED: 'EXPIRED',                   // コード期限切れ
  INVALID_ID: 'INVALID_ID',             // プレイヤーIDが存在しない
  INVALID_CODE: 'INVALID_CODE',         // コード不正
  FAILED: 'FAILED'                      // ネットワーク・サーバーエラー
};

/**
 * SgrRedeemEngine
 * 
 * Throttled batch redemption engine using ConcurrencyQueue.
 * Ensures 2-3s delay per request to safeguard against IP rate-limiting.
 */
class SgrRedeemEngine {
  /**
   * @param {Object} [options]
   * @param {number} [options.intervalMs=2500] Throttling interval per member (ms)
   * @param {number} [options.timeoutMs=10000] Per-member request timeout
   * @param {Function} [options.redeemHandler] Custom API caller: async (fid, code) => status
   */
  constructor(options = {}) {
    this.intervalMs = Number.isInteger(options.intervalMs) ? options.intervalMs : 2500;
    this.timeoutMs = options.timeoutMs || 10000;
    this.redeemHandler = options.redeemHandler || this._defaultMockRedeemHandler.bind(this);

    this.queue = new ConcurrencyQueue({
      concurrency: 1, // Single-threaded queue to ensure strict sequential requests
      timeout: this.timeoutMs + this.intervalMs + 1000,
      retries: 1,
      retryDelay: () => 2000
    });

    this.isProcessing = false;
  }

  /**
   * Default mock redemption logic (for testing & offline preview)
   * @private
   */
  async _defaultMockRedeemHandler(fid, code) {
    // Simulates network latency (100-200ms)
    await new Promise(r => setTimeout(r, 100));

    if (code === 'INVALID_CODE') {
      return { status: RedeemStatus.INVALID_CODE, message: '無効なギフトコードです。' };
    }
    if (code === 'EXPIRED_CODE') {
      return { status: RedeemStatus.EXPIRED, message: 'このギフトコードは有効期限が切れています。' };
    }
    if (fid.startsWith('999')) {
      return { status: RedeemStatus.INVALID_ID, message: '存在しないプレイヤーIDです。' };
    }
    if (fid.endsWith('0')) {
      return { status: RedeemStatus.ALREADY_CLAIMED, message: '既に獲得済みです。' };
    }

    return { status: RedeemStatus.SUCCESS, message: 'ギフト引き換えに成功しました！' };
  }

  /**
   * Execute batch redemption for all provided members.
   * 
   * @param {Array<Object>} members Array of member objects { kingshot_player_id, discord_user_id, discord_username }
   * @param {string} code Gift code to redeem
   * @param {Object} [callbacks]
   * @param {Function} [callbacks.onProgress] Called after each member is processed: (progressInfo) => void
   * @returns {Promise<Object>} Final summary report
   */
  async executeBatch(members, code, callbacks = {}) {
    if (this.isProcessing) {
      throw new Error('Another batch redemption is currently in progress. Please wait.');
    }

    this.isProcessing = true;
    const cleanCode = String(code || '').trim().toUpperCase();
    const total = members.length;

    const report = {
      code: cleanCode,
      startTime: new Date().toISOString(),
      endTime: null,
      total,
      processed: 0,
      counts: {
        [RedeemStatus.SUCCESS]: 0,
        [RedeemStatus.ALREADY_CLAIMED]: 0,
        [RedeemStatus.EXPIRED]: 0,
        [RedeemStatus.INVALID_ID]: 0,
        [RedeemStatus.INVALID_CODE]: 0,
        [RedeemStatus.FAILED]: 0
      },
      details: []
    };

    if (total === 0) {
      report.endTime = new Date().toISOString();
      this.isProcessing = false;
      return report;
    }

    const tasks = members.map((member, index) => {
      return async () => {
        const itemResult = {
          fid: member.kingshot_player_id,
          discord_user_id: member.discord_user_id,
          discord_username: member.discord_username,
          status: RedeemStatus.FAILED,
          message: '',
          timestamp: new Date().toISOString()
        };

        try {
          const res = await this.redeemHandler(member.kingshot_player_id, cleanCode, member);
          itemResult.status = res.status || RedeemStatus.SUCCESS;
          itemResult.message = res.message || '';
        } catch (err) {
          itemResult.status = RedeemStatus.FAILED;
          itemResult.message = err.message || 'Network error';
        }

        // Update counts
        report.processed++;
        if (report.counts[itemResult.status] !== undefined) {
          report.counts[itemResult.status]++;
        } else {
          report.counts[RedeemStatus.FAILED]++;
        }
        report.details.push(itemResult);

        // Notify progress callback
        if (typeof callbacks.onProgress === 'function') {
          try {
            callbacks.onProgress({
              processed: report.processed,
              total: report.total,
              percent: Math.round((report.processed / report.total) * 100),
              latest: itemResult,
              counts: { ...report.counts }
            });
          } catch (cbErr) {
            console.error('[SgrRedeemEngine] Error in onProgress callback:', cbErr);
          }
        }

        // Throttle interval before next member request (except last member)
        if (index < total - 1 && this.intervalMs > 0) {
          await new Promise(r => setTimeout(r, this.intervalMs));
        }

        return itemResult;
      };
    });

    try {
      await this.queue.addAll(tasks);
    } finally {
      report.endTime = new Date().toISOString();
      this.isProcessing = false;
    }

    return report;
  }

  /**
   * Alias for executeBatch with (code, members) or (members, code) parameter order
   */
  async startBatchRedemption(arg1, arg2, callbacks = {}) {
    if (Array.isArray(arg1)) {
      return this.executeBatch(arg1, arg2, callbacks);
    } else {
      return this.executeBatch(arg2, arg1, callbacks);
    }
  }
}

module.exports = {
  SgrRedeemEngine,
  RedeemStatus
};
