'use strict';

const fs = require('fs');
const path = require('path');

/**
 * SgrMemberStore
 * 
 * Lightweight persistent JSON store for SGR Alliance KingShot members.
 * Supports atomic writes, duplicate FID checks, soft-delete, and CSV/JSON export.
 */
class SgrMemberStore {
  /**
   * @param {Object} options
   * @param {string} [options.storagePath] - Path to JSON storage file (default: './data/sgr_members.json')
   */
  constructor(options = {}) {
    const defaultPath = path.resolve(__dirname, '../../data', 'sgr_members.json');
    this.storagePath = options.storagePath || defaultPath;
    this.storageDir = path.dirname(this.storagePath);
    
    /** @type {Map<string, Object>} Map keyed by kingshot_player_id */
    this._members = new Map();
    this._isLoaded = false;
  }

  /**
   * Initialize store and load data from disk.
   */
  init() {
    try {
      if (!fs.existsSync(this.storageDir)) {
        fs.mkdirSync(this.storageDir, { recursive: true });
      }

      if (fs.existsSync(this.storagePath)) {
        const raw = fs.readFileSync(this.storagePath, 'utf8');
        if (raw.trim()) {
          const list = JSON.parse(raw);
          this._members.clear();
          if (Array.isArray(list)) {
            for (const item of list) {
              const fid = String(item.kingshot_player_id || item.fid || '').trim();
              if (fid && item.discord_user_id) {
                this._members.set(fid, {
                  discord_user_id: String(item.discord_user_id),
                  discord_username: String(item.discord_username || 'Unknown'),
                  kingshot_player_id: fid,
                  kingshot_kingdom_id: String(item.kingshot_kingdom_id || item.kid || '').trim(),
                  registered_at: item.registered_at || new Date().toISOString(),
                  updated_at: item.updated_at || item.registered_at || new Date().toISOString(),
                  active_flag: item.active_flag !== false,
                  notes: item.notes || ''
                });
              }
            }
          }
        }
      } else {
        // Create initial empty file
        this._saveSync();
      }

      this._isLoaded = true;
      return true;
    } catch (err) {
      console.error(`[SgrMemberStore] Failed to initialize store at ${this.storagePath}:`, err);
      throw err;
    }
  }

  /**
   * Save in-memory data to file atomically via temp file.
   * @private
   */
  _saveSync() {
    if (!fs.existsSync(this.storageDir)) {
      fs.mkdirSync(this.storageDir, { recursive: true });
    }

    const tempPath = `${this.storagePath}.${Date.now()}.${Math.random().toString(36).slice(2, 7)}.tmp`;
    const data = Array.from(this._members.values());
    const jsonString = JSON.stringify(data, null, 2);

    fs.writeFileSync(tempPath, jsonString, 'utf8');
    fs.renameSync(tempPath, this.storagePath);
  }

  /**
   * Validate KingShot Player ID (FID).
   * Typically 4-20 alphanumeric characters or digits.
   * @param {string} fid 
   * @returns {boolean}
   */
  isValidFid(fid) {
    if (typeof fid !== 'string') return false;
    const clean = fid.trim();
    // Allow numeric or alphanumeric IDs, length 4 to 25
    return /^[a-zA-Z0-9_-]{4,25}$/.test(clean);
  }

  /**
   * Register or update a member's KingShot Player ID (multi-account friendly).
   */
  register(discordUserId, kingshotPlayerId, discordUsername = 'Unknown', kingdomId = '', notes = '') {
    if (typeof discordUserId === 'object' && discordUserId !== null) {
      const opts = discordUserId;
      return this.register(
        opts.discord_user_id || opts.discordUserId,
        opts.kingshot_player_id || opts.kingshotPlayerId || opts.fid,
        opts.discord_username || opts.discordUsername || opts.username || 'Unknown',
        opts.kingshot_kingdom_id || opts.kingshotKingdomId || opts.kid || '',
        opts.notes || ''
      );
    }

    if (!this._isLoaded) this.init();

    const uid = String(discordUserId || '').trim();
    const fid = String(kingshotPlayerId || '').trim();
    const username = String(discordUsername || '').trim();
    const kid = String(kingdomId || '').trim();

    if (!uid) {
      return { success: false, error: 'DISCORD_USER_ID_REQUIRED' };
    }

    if (!fid || !this.isValidFid(fid)) {
      return { 
        success: false, 
        error: 'INVALID_FID_FORMAT', 
        message: 'プレイヤーID (FID) は4〜25桁の半角英数字である必要があります。' 
      };
    }

    // Check if FID is already claimed by another active user
    const existing = this._members.get(fid);
    if (existing && existing.discord_user_id !== uid && existing.active_flag) {
      return {
        success: false,
        error: 'FID_ALREADY_REGISTERED',
        conflictUser: existing.discord_username || existing.discord_user_id,
        message: `プレイヤーID「${fid}」は既に他のメンバー (@${existing.discord_username || existing.discord_user_id}) に連携されています。`
      };
    }

    const now = new Date().toISOString();
    let isNew = false;
    let record;

    if (existing && existing.discord_user_id === uid) {
      // Update existing record for this FID
      record = {
        ...existing,
        discord_username: username || existing.discord_username,
        kingshot_player_id: fid,
        kingshot_kingdom_id: kid || existing.kingshot_kingdom_id || '',
        updated_at: now,
        active_flag: true,
        notes: notes !== undefined ? notes : existing.notes
      };
    } else {
      // New registration (can be main, sub, etc.)
      isNew = true;
      record = {
        discord_user_id: uid,
        discord_username: username,
        kingshot_player_id: fid,
        kingshot_kingdom_id: kid,
        registered_at: now,
        updated_at: now,
        active_flag: true,
        notes: notes || ''
      };
    }

    this._members.set(fid, record);
    this._saveSync();

    const userAllAccounts = this.getMembersByDiscordId(uid);

    return {
      success: true,
      isNew,
      updated: !isNew,
      action: isNew ? 'registered' : 'updated',
      member: { ...record },
      totalAccounts: userAllAccounts.length
    };
  }

  /**
   * Alias for register
   */
  registerMember(data) {
    return this.register(data);
  }

  /**
   * Unregister a member account (or all accounts of a user).
   * 
   * @param {string} discordUserId 
   * @param {string} [specificFid] If omitted, unregisters all accounts for this user
   * @returns {{ success: boolean, found: boolean, message?: string }}
   */
  unregister(discordUserId, specificFid = '') {
    if (!this._isLoaded) this.init();

    const uid = String(discordUserId || '').trim();
    const targetFid = String(specificFid || '').trim();

    let count = 0;
    for (const [fid, m] of this._members.entries()) {
      if (m.discord_user_id === uid && m.active_flag) {
        if (!targetFid || m.kingshot_player_id === targetFid) {
          m.active_flag = false;
          m.updated_at = new Date().toISOString();
          count++;
        }
      }
    }

    if (count === 0) {
      return {
        success: false,
        found: false,
        message: targetFid 
          ? `指定されたプレイヤーID (${targetFid}) の登録が見つかりません。`
          : '登録済みのKingShotアカウントが見つかりません。'
      };
    }

    this._saveSync();

    return {
      success: true,
      found: true,
      count,
      message: targetFid 
        ? `プレイヤーID (${targetFid}) の登録解除が完了しました。`
        : `連携されていた ${count} 件のアカウントすべての登録解除が完了しました。`
    };
  }

  /**
   * Get all active accounts owned by a Discord User ID.
   * @param {string} discordUserId 
   * @returns {Array<Object>}
   */
  getMembersByDiscordId(discordUserId) {
    if (!this._isLoaded) this.init();
    const uid = String(discordUserId || '').trim();
    const list = [];
    for (const m of this._members.values()) {
      if (m.discord_user_id === uid && m.active_flag) {
        list.push({ ...m });
      }
    }
    list.sort((a, b) => new Date(a.registered_at) - new Date(b.registered_at));
    return list;
  }

  /**
   * Get active member by Discord User ID (Returns first account for backward compatibility).
   * @param {string} discordUserId 
   * @returns {Object|null}
   */
  getMember(discordUserId) {
    const list = this.getMembersByDiscordId(discordUserId);
    return list.length > 0 ? list[0] : null;
  }

  /**
   * Get member by KingShot Player ID (FID).
   * 
   * @param {string} fid 
   * @param {boolean} [activeOnly=true]
   * @returns {Object|null}
   */
  getMemberByFid(fid, activeOnly = true) {
    if (!this._isLoaded) this.init();
    const targetFid = String(fid || '').trim();
    for (const member of this._members.values()) {
      if (member.kingshot_player_id === targetFid) {
        if (!activeOnly || member.active_flag) {
          return { ...member };
        }
      }
    }
    return null;
  }

  /**
   * Get all active members.
   * 
   * @returns {Array<Object>}
   */
  getAllActiveMembers() {
    if (!this._isLoaded) this.init();
    const list = [];
    for (const member of this._members.values()) {
      if (member.active_flag) {
        list.push({ ...member });
      }
    }
    // Sort by registered_at ascending
    list.sort((a, b) => new Date(a.registered_at) - new Date(b.registered_at));
    return list;
  }

  /**
   * Get summary statistics.
   * 
   * @returns {{ total: number, active: number, inactive: number }}
   */
  getStats() {
    if (!this._isLoaded) this.init();
    let active = 0;
    let inactive = 0;
    for (const member of this._members.values()) {
      if (member.active_flag) active++;
      else inactive++;
    }
    return {
      total: this._members.size,
      active,
      inactive
    };
  }

  /**
   * Export all active members to CSV format.
   * 
   * @returns {string} CSV string
   */
  exportToCSV() {
    const members = this.getAllActiveMembers();
    const headers = ['Discord_ID', 'Discord_Username', 'KingShot_Player_ID(fid)', 'Registered_At', 'Status'];
    const lines = [headers.join(',')];

    for (const m of members) {
      const escapedName = `"${(m.discord_username || '').replace(/"/g, '""')}"`;
      const row = [
        `'${m.discord_user_id}`,
        escapedName,
        m.kingshot_player_id,
        m.registered_at,
        m.active_flag ? 'Active' : 'Inactive'
      ];
      lines.push(row.join(','));
    }

    return lines.join('\n');
  }

  /**
   * Export all members to JSON string.
   * 
   * @param {boolean} [pretty=true] 
   * @returns {string}
   */
  exportToJSON(pretty = true) {
    if (!this._isLoaded) this.init();
    const data = Array.from(this._members.values());
    return pretty ? JSON.stringify(data, null, 2) : JSON.stringify(data);
  }

  /**
   * Bulk import members (e.g. from existing roster).
   * 
   * @param {Array<Object>} list 
   * @returns {{ imported: number, errors: Array<string> }}
   */
  bulkImport(list) {
    if (!Array.isArray(list)) throw new TypeError('Expected an array of member objects');
    if (!this._isLoaded) this.init();

    let imported = 0;
    const errors = [];

    for (let i = 0; i < list.length; i++) {
      const item = list[i];
      if (!item || !item.discord_user_id || !item.kingshot_player_id) {
        errors.push(`Row ${i + 1}: Missing discord_user_id or kingshot_player_id`);
        continue;
      }
      const res = this.register(item.discord_user_id, item.kingshot_player_id, item.discord_username || 'Unknown', item.notes || '');
      if (res.success) {
        imported++;
      } else {
        errors.push(`Row ${i + 1} (${item.discord_user_id}): ${res.error || res.message}`);
      }
    }

    return { imported, errors };
  }
}

module.exports = SgrMemberStore;
