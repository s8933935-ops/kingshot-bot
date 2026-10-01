'use strict';

const fs = require('fs');
const path = require('path');
const https = require('https');
const { EmbedBuilder } = require('discord.js');

const DEFAULT_CACHE_PATH = path.join(__dirname, 'data', 'processed_codes.json');

// Built-in seed / fallback codes (always monitored)
const DEFAULT_SEED_CODES = [
  'VIP777',
  'Kingshot888',
  'MIDAUTUMN26',
  'EXPLORETHEWORLD'
];

// Sources for gift codes scraping
const SCRAPE_SOURCES = [
  {
    name: 'PocketTactics',
    url: 'https://www.pockettactics.com/kingshot/codes',
    parser: (html) => {
      const codes = new Set();
      // Look for list items like <li><strong>Kingshot888</strong>
      const liMatches = html.match(/<li><strong>([A-Za-z0-9_]{4,20})<\/strong>/g) || [];
      for (const m of liMatches) {
        const code = m.replace(/<\/?strong>|<\/?li>/g, '').trim();
        if (code && !['DISCORD', 'FACEBOOK', 'UPDATE'].includes(code.toUpperCase())) {
          codes.add(code);
        }
      }
      return Array.from(codes);
    }
  }
];

class GiftPatrolService {
  /**
   * @param {Object} options
   * @param {Object} options.redeemEngine - SgrRedeemEngine instance
   * @param {Object} options.memberStore - SgrMemberStore instance
   * @param {Object} [options.discordClient] - Discord Client instance
   * @param {string} [options.cacheFilePath] - Path to processed_codes.json
   * @param {number} [options.checkIntervalMs=3600000] - 1 hour default
   * @param {string} [options.notifyChannelId] - Target Discord Channel ID for auto-reports
   */
  constructor(options = {}) {
    this.redeemEngine = options.redeemEngine;
    this.memberStore = options.memberStore;
    this.discordClient = options.discordClient;
    this.cacheFilePath = options.cacheFilePath || DEFAULT_CACHE_PATH;
    this.checkIntervalMs = options.checkIntervalMs || (60 * 60 * 1000); // 1 hour
    this.notifyChannelId = options.notifyChannelId || process.env.SGR_NOTIFY_CHANNEL_ID || '';

    this.timer = null;
    this.isChecking = false;
    this.processedCodes = {}; // { [code]: { firstSeen, lastChecked, status, results } }
  }

  /**
   * Initialize and load history cache
   */
  init() {
    const dir = path.dirname(this.cacheFilePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    if (fs.existsSync(this.cacheFilePath)) {
      try {
        const raw = fs.readFileSync(this.cacheFilePath, 'utf-8');
        this.processedCodes = JSON.parse(raw);
      } catch (err) {
        console.error('[GIFT_PATROL] Failed to load cache file, starting fresh:', err.message);
        this.processedCodes = {};
      }
    } else {
      this.processedCodes = {};
      this._saveCache();
    }

    console.log(`[GIFT_PATROL] Initialized. Known codes in cache: ${Object.keys(this.processedCodes).length}`);
  }

  _saveCache() {
    try {
      fs.writeFileSync(this.cacheFilePath, JSON.stringify(this.processedCodes, null, 2), 'utf-8');
    } catch (err) {
      console.error('[GIFT_PATROL] Failed to save cache file:', err.message);
    }
  }

  /**
   * Fetch HTML content with safe user-agent
   */
  async _fetchHtml(url) {
    return new Promise((resolve) => {
      const req = https.get(url, {
        headers: {
          'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        },
        timeout: 10000
      }, (res) => {
        if (res.statusCode < 200 || res.statusCode >= 300) {
          return resolve('');
        }
        let data = '';
        res.on('data', chunk => data += chunk);
        res.on('end', () => resolve(data));
      });

      req.on('error', () => resolve(''));
      req.on('timeout', () => {
        req.destroy();
        resolve('');
      });
    });
  }

  /**
   * Scrape and collect active codes from all sources
   */
  async collectAllCodes() {
    const discovered = new Set(DEFAULT_SEED_CODES);

    for (const src of SCRAPE_SOURCES) {
      try {
        const html = await this._fetchHtml(src.url);
        if (html) {
          const parsed = src.parser(html);
          for (const c of parsed) {
            discovered.add(c);
          }
        }
      } catch (err) {
        console.warn(`[GIFT_PATROL] Failed to scrape from ${src.name}:`, err.message);
      }
    }

    return Array.from(discovered);
  }

  /**
   * Execute single patrol sweep:
   * 1. Collect codes
   * 2. Find new/unprocessed codes
   * 3. Redeem for all active SGR members
   * 4. Notify Discord
   * @param {Object} [options]
   * @param {boolean} [options.forceAll=false] - If true, re-check even if already processed
   * @returns {Promise<{ foundCodes: string[], newCodes: string[], batchResults: Object[] }>}
   */
  async runPatrol(options = {}) {
    if (this.isChecking) {
      console.log('[GIFT_PATROL] Patrol already in progress. Skipping concurrent run.');
      return { foundCodes: [], newCodes: [], batchResults: [], inProgress: true };
    }

    this.isChecking = true;
    console.log('[GIFT_PATROL] 🚀 Starting Gift Code Patrol sweep...');

    try {
      const allFound = await this.collectAllCodes();
      const activeMembers = this.memberStore ? this.memberStore.getAllActiveMembers() : [];
      const newCodes = [];
      const batchResults = [];

      for (const code of allFound) {
        const record = this.processedCodes[code];
        // If already marked as COMPLETED and not forceAll, skip
        if (!options.forceAll && record && record.status === 'COMPLETED') {
          continue;
        }

        newCodes.push(code);
      }

      console.log(`[GIFT_PATROL] Scanned ${allFound.length} codes. New/pending codes: ${newCodes.length} (${newCodes.join(', ') || 'None'})`);

      if (newCodes.length > 0 && activeMembers.length > 0 && this.redeemEngine) {
        for (const code of newCodes) {
          console.log(`[GIFT_PATROL] 🎁 Auto-redeeming detected new code: [${code}] for ${activeMembers.length} members...`);
          
          const batchPromise = this.redeemEngine.startBatchRedemption(code, activeMembers);
          const summary = await batchPromise;

          const counts = summary.counts || summary.statusCounts || {};
          const durationSec = summary.durationSeconds !== undefined
            ? summary.durationSeconds
            : Math.max(1, Math.round((new Date(summary.endTime || Date.now()) - new Date(summary.startTime || Date.now())) / 1000));

          // Record in cache
          this.processedCodes[code] = {
            code,
            firstSeen: this.processedCodes[code]?.firstSeen || new Date().toISOString(),
            lastProcessed: new Date().toISOString(),
            status: 'COMPLETED',
            totalMembers: summary.total,
            counts
          };
          this._saveCache();

          batchResults.push({ code, summary });

          // Send Discord notification
          await this._broadcastReport(code, summary);
        }
      } else if (newCodes.length > 0 && activeMembers.length === 0) {
        console.log('[GIFT_PATROL] No active SGR members registered. Skipping auto-redeem execution.');
      }

      return {
        foundCodes: allFound,
        newCodes,
        batchResults
      };
    } finally {
      this.isChecking = false;
    }
  }

  /**
   * Broadcast rich Embed report to Discord
   */
  async _broadcastReport(code, summary) {
    if (!this.discordClient || !this.discordClient.isReady()) {
      return;
    }

    const counts = summary.counts || summary.statusCounts || {};
    const durationSec = summary.durationSeconds !== undefined
      ? summary.durationSeconds
      : Math.max(1, Math.round((new Date(summary.endTime || Date.now()) - new Date(summary.startTime || Date.now())) / 1000));

    const embed = new EmbedBuilder()
      .setColor('#10b981')
      .setTitle(`🎁 【SGR自動パトロール】新規ギフトコード自動受け取り完了`)
      .setDescription(`WEBパトロールにより新しいギフトコード **\`${code}\`** を検知し、全SGRメンバーへ自動で一括引き換えを行いました！\nゲーム内メールをご確認ください。`)
      .addFields(
        { name: '🟢 引き換え成功', value: `${counts.SUCCESS || 0} 名`, inline: true },
        { name: '🟡 既に獲得済 (同種受取済)', value: `${counts.ALREADY_CLAIMED || 0} 名`, inline: true },
        { name: '🔴 期限切れ', value: `${counts.EXPIRED || 0} 名`, inline: true },
        { name: '⚠️ ID/王国エラー', value: `${counts.INVALID_ID || 0} 名`, inline: true },
        { name: '❌ 失敗・通信エラー', value: `${counts.FAILED || 0} 名`, inline: true },
        { name: '⏱️ 総所要時間', value: `${durationSec} 秒 (安全レートリミット)`, inline: true }
      )
      .setFooter({ text: 'SGR Alliance Autonomous Gift Patrol • Fully Automated' })
      .setTimestamp();

    // 1. If explicit notifyChannelId is provided
    if (this.notifyChannelId) {
      try {
        const channel = await this.discordClient.channels.fetch(this.notifyChannelId);
        if (channel && channel.isTextBased()) {
          await channel.send({ embeds: [embed] });
          return;
        }
      } catch (e) {
        console.warn(`[GIFT_PATROL] Could not send to notifyChannelId (${this.notifyChannelId}):`, e.message);
      }
    }

    // 2. Broadcast to default text channel of all guilds the bot belongs to
    try {
      const guilds = this.discordClient.guilds.cache;
      for (const [guildId, guild] of guilds) {
        // Find systemChannel or first available text channel
        const targetChannel = guild.systemChannel || 
          guild.channels.cache.find(c => c.isTextBased() && c.permissionsFor(guild.members.me)?.has('SendMessages'));

        if (targetChannel) {
          await targetChannel.send({ embeds: [embed] }).catch(err => {
            console.warn(`[GIFT_PATROL] Failed to send report to guild ${guild.name}:`, err.message);
          });
        }
      }
    } catch (err) {
      console.error('[GIFT_PATROL] Broadcast error:', err.message);
    }
  }

  /**
   * Start periodic background patrol
   */
  start(runImmediate = false) {
    if (this.timer) {
      clearInterval(this.timer);
    }

    console.log(`[GIFT_PATROL] Periodic patrol started (Interval: ${Math.round(this.checkIntervalMs / 60000)} mins)`);

    if (runImmediate) {
      this.runPatrol().catch(err => {
        console.error('[GIFT_PATROL] Error in initial patrol run:', err);
      });
    }

    this.timer = setInterval(() => {
      this.runPatrol().catch(err => {
        console.error('[GIFT_PATROL] Error in periodic patrol sweep:', err);
      });
    }, this.checkIntervalMs);
  }

  /**
   * Stop background patrol
   */
  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
      console.log('[GIFT_PATROL] Periodic patrol stopped.');
    }
  }
}

module.exports = {
  GiftPatrolService,
  DEFAULT_SEED_CODES
};
