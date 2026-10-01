'use strict';

const { SlashCommandBuilder, PermissionFlagsBits, AttachmentBuilder } = require('discord.js');
const {
  createRegisterEmbed,
  createMyIdEmbed,
  createMemberListEmbed,
  createRedeemProgressEmbed,
  createRedeemSummaryEmbed,
  createPermissionDeniedEmbed
} = require('./sgr_embeds');

/**
 * Build Slash Command Definitions for Discord REST Registration.
 */
function getSgrSlashCommands() {
  // --- Universal KingShot (ks_) Commands ---
  const ksRegisterCmd = new SlashCommandBuilder()
    .setName('ks_register')
    .setDescription('KingShotプレイヤーID（FID）と王国番号を連携します（ギフト自動受取用）')
    .addStringOption(option =>
      option.setName('fid')
        .setDescription('あなたのKingShotプレイヤーID（数字・英数字）')
        .setRequired(true)
    )
    .addStringOption(option =>
      option.setName('kid')
        .setDescription('あなたの所属王国番号（Kingdom ID。例: 898, 101）')
        .setRequired(false)
    );

  const ksMyIdCmd = new SlashCommandBuilder()
    .setName('ks_myid')
    .setDescription('現在連携されているKingShotプレイヤーID（FID）と王国番号を確認します');

  const ksUnregisterCmd = new SlashCommandBuilder()
    .setName('ks_unregister')
    .setDescription('登録済みのKingShotプレイヤーIDの連携を解除します');

  const ksListCmd = new SlashCommandBuilder()
    .setName('ks_list')
    .setDescription('【管理者】登録されているKingShotメンバー名簿を一覧表示します')
    .addIntegerOption(option =>
      option.setName('page')
        .setDescription('表示するページ番号（1〜）')
        .setRequired(false)
    );

  const ksRedeemCmd = new SlashCommandBuilder()
    .setName('ks_redeem')
    .setDescription('【管理者】登録メンバー全員に対してギフトコードを一括受取・適用します')
    .addStringOption(option =>
      option.setName('code')
        .setDescription('配布するギフトコード')
        .setRequired(true)
    );

  const ksExportCmd = new SlashCommandBuilder()
    .setName('ks_export')
    .setDescription('【管理者】登録メンバーのバックアップデータをCSV形式でエクスポートします')
    .addStringOption(option =>
      option.setName('format')
        .setDescription('出力フォーマット（csv または json）')
        .setRequired(false)
        .addChoices(
          { name: 'CSV (Excel対応)', value: 'csv' },
          { name: 'JSON (生データ)', value: 'json' }
        )
    );

  const ksPatrolCmd = new SlashCommandBuilder()
    .setName('ks_patrol')
    .setDescription('【管理者】Webを巡回して最新ギフトコードを自動検知し、全メンバーへ自動一括引き換えします')
    .addBooleanOption(option =>
      option.setName('force')
        .setDescription('処理済みコードも含めて強制再チェックするか（初期値: false）')
        .setRequired(false)
    );

  // --- Legacy / Alias (sgr_) Commands for backwards compatibility ---
  const registerCmd = new SlashCommandBuilder()
    .setName('sgr_register')
    .setDescription('【旧コマンド】KingShotプレイヤーID（FID）と王国番号を連携します')
    .addStringOption(option =>
      option.setName('fid')
        .setDescription('あなたのKingShotプレイヤーID')
        .setRequired(true)
    )
    .addStringOption(option =>
      option.setName('kid')
        .setDescription('あなたの所属王国番号')
        .setRequired(false)
    );

  const myIdCmd = new SlashCommandBuilder()
    .setName('sgr_myid')
    .setDescription('【旧コマンド】連携されているKingShotプレイヤーIDを確認します');

  const unregisterCmd = new SlashCommandBuilder()
    .setName('sgr_unregister')
    .setDescription('【旧コマンド】連携を解除します');

  const listCmd = new SlashCommandBuilder()
    .setName('sgr_list')
    .setDescription('【旧コマンド】登録メンバー名簿を一覧表示します')
    .addIntegerOption(option =>
      option.setName('page')
        .setDescription('表示するページ番号')
        .setRequired(false)
    );

  const redeemCmd = new SlashCommandBuilder()
    .setName('sgr_redeem')
    .setDescription('【旧コマンド】登録メンバー全員にギフトコードを一括受取します')
    .addStringOption(option =>
      option.setName('code')
        .setDescription('配布するギフトコード')
        .setRequired(true)
    );

  const exportCmd = new SlashCommandBuilder()
    .setName('sgr_export')
    .setDescription('【旧コマンド】登録メンバー名簿をエクスポートします')
    .addStringOption(option =>
      option.setName('format')
        .setDescription('出力フォーマット')
        .setRequired(false)
        .addChoices(
          { name: 'CSV (Excel対応)', value: 'csv' },
          { name: 'JSON (生データ)', value: 'json' }
        )
    );

  const patrolCmd = new SlashCommandBuilder()
    .setName('sgr_patrol')
    .setDescription('【旧コマンド】Webを巡回して最新ギフトコードを全員に自動一括引き換えします')
    .addBooleanOption(option =>
      option.setName('force')
        .setDescription('強制再チェック')
        .setRequired(false)
    );

  return [
    ksRegisterCmd, ksMyIdCmd, ksUnregisterCmd, ksListCmd, ksRedeemCmd, ksExportCmd, ksPatrolCmd,
    registerCmd, myIdCmd, unregisterCmd, listCmd, redeemCmd, exportCmd, patrolCmd
  ];
}

/**
 * Access Control: Check if user is an Officer or Admin.
 */
function isOfficerOrAdmin(interaction) {
  const authorizedUsers = (process.env.AUTHORIZED_USERS || '').split(',').map(s => s.trim()).filter(Boolean);
  if (authorizedUsers.includes(interaction.user.id)) return true;

  // Discord Guild Administrator permission
  if (interaction.memberPermissions && interaction.memberPermissions.has(PermissionFlagsBits.Administrator)) {
    return true;
  }

  // Guild Role check
  if (interaction.member && interaction.member.roles) {
    const officerRoleId = process.env.SGR_OFFICER_ROLE_ID;
    const roleNames = ['officer', 'leader', 'sgr幹部', 'sgr officer', 'admin', 'administrator', '幹部', '盟主'];

    // If specific role ID is configured
    if (officerRoleId && interaction.member.roles.cache.has(officerRoleId)) {
      return true;
    }

    // Role name search (case-insensitive)
    const roleValues = typeof interaction.member.roles.cache.values === 'function'
      ? Array.from(interaction.member.roles.cache.values())
      : (Array.isArray(interaction.member.roles.cache) ? interaction.member.roles.cache : []);

    const hasOfficerRole = roleValues.some(r =>
      roleNames.includes((r.name || '').toLowerCase().trim())
    );
    if (hasOfficerRole) return true;
  }

  return false;
}

/**
 * Access Control: Check if user has SGR member role.
 */
function isSgrMember(interaction) {
  // If role check is not strictly enforced by config, allow all guild members
  if (process.env.SGR_REQUIRE_ROLE === 'false') return true;

  // Officers are always members
  if (isOfficerOrAdmin(interaction)) return true;

  if (interaction.member && interaction.member.roles && interaction.member.roles.cache) {
    const sgrRoleId = process.env.SGR_ROLE_ID;
    if (sgrRoleId && typeof interaction.member.roles.cache.has === 'function' && interaction.member.roles.cache.has(sgrRoleId)) {
      return true;
    }

    const roleValues = typeof interaction.member.roles.cache.values === 'function'
      ? Array.from(interaction.member.roles.cache.values())
      : (Array.isArray(interaction.member.roles.cache) ? interaction.member.roles.cache : []);

    // Check for role named SGR or containing SGR
    const hasSgrRole = roleValues.some(r =>
      (r.name || '').toUpperCase().includes('SGR')
    );
    if (hasSgrRole) return true;
  }

  return false;
}

/**
 * Main Interaction Handler for SGR Slash Commands.
 * 
 * @param {import('discord.js').ChatInputCommandInteraction} interaction 
 * @param {import('./sgr_member_store')} memberStore 
 * @param {import('./sgr_redeem_engine').SgrRedeemEngine} redeemEngine 
 */
async function handleSgrCommand(interaction, memberStore, redeemEngine, giftPatrolService) {
  const { commandName } = interaction;
  const normCmd = commandName.replace(/^(sgr|ks)_/, '');

  // 1. /ks_register or /sgr_register [fid] [kid]
  if (normCmd === 'register') {
    // Only enforce SGR role if explicitly called with legacy /sgr_register AND role checking is enabled
    if (commandName.startsWith('sgr_') && !isSgrMember(interaction)) {
      return interaction.reply({
        embeds: [createPermissionDeniedEmbed('@SGR ロール')],
        ephemeral: true
      });
    }

    const rawFid = interaction.options.getString('fid', true).trim();
    const rawKid = (interaction.options.getString('kid') || '').trim();
    const username = interaction.user.tag || interaction.user.username;

    // Smart parameter extraction
    const combined = `${rawFid} ${rawKid}`.trim();
    let fid = '';
    let kid = '';

    const fidMatch = combined.match(/fid[:=\s]+([0-9a-zA-Z_]+)/i);
    const kidMatch = combined.match(/kid[:=\s]+([0-9a-zA-Z_]+)/i);

    if (fidMatch) fid = fidMatch[1];
    if (kidMatch) kid = kidMatch[1];

    if (!fid || !kid) {
      const tokens = combined.replace(/fid:|kid:/gi, ' ').split(/\s+/).filter(Boolean);
      if (!fid && tokens.length > 0) fid = tokens[0];
      if (!kid && tokens.length > 1) kid = tokens[1];
    }

    const result = memberStore.registerMember({
      discord_user_id: interaction.user.id,
      discord_username: username,
      kingshot_player_id: fid,
      kingshot_kingdom_id: kid
    });

    if (!result.success) {
      return interaction.reply({
        content: `❌ **登録エラー**: ${result.message || result.error}`,
        ephemeral: true
      });
    }

    return interaction.reply({
      embeds: [createRegisterEmbed(result.member, result.isNew, result.totalAccounts)],
      ephemeral: true
    });
  }

  // 2. /ks_myid or /sgr_myid
  if (normCmd === 'myid') {
    const userAccounts = memberStore.getMembersByDiscordId(interaction.user.id);
    return interaction.reply({
      embeds: [createMyIdEmbed(userAccounts)],
      ephemeral: true
    });
  }

  // 3. /ks_unregister or /sgr_unregister
  if (normCmd === 'unregister') {
    const fidOption = interaction.options.getString('fid') || '';
    const result = memberStore.unregister(interaction.user.id, fidOption);
    if (!result.success) {
      return interaction.reply({
        content: `⚠️ ${result.message}`,
        ephemeral: true
      });
    }
    return interaction.reply({
      content: `✅ ${result.message}`,
      ephemeral: true
    });
  }

  // 4. /ks_list or /sgr_list [page] (Officer/Admin only)
  if (normCmd === 'list') {
    if (!isOfficerOrAdmin(interaction)) {
      return interaction.reply({
        embeds: [createPermissionDeniedEmbed('同盟幹部 (Officer/Admin)')],
        ephemeral: true
      });
    }

    const page = interaction.options.getInteger('page') || 1;
    const members = memberStore.getAllActiveMembers();

    return interaction.reply({
      embeds: [createMemberListEmbed(members, page)],
      ephemeral: true
    });
  }

  // 5. /ks_redeem or /sgr_redeem [code] (Officer only)
  if (normCmd === 'redeem') {
    if (!isOfficerOrAdmin(interaction)) {
      return interaction.reply({
        embeds: [createPermissionDeniedEmbed('同盟幹部 (Officer/Admin)')],
        ephemeral: true
      });
    }

    const code = interaction.options.getString('code', true).trim().toUpperCase();
    const members = memberStore.getAllActiveMembers();

    if (members.length === 0) {
      return interaction.reply({
        content: '⚠️ 登録されているアクティブなKingShotメンバーが0名です。まずは `/ks_register` でメンバー登録を行ってください。',
        ephemeral: true
      });
    }

    // Defer reply so Discord won't time out (can take 1-3 minutes for batch processing)
    await interaction.deferReply();

    let lastEditTime = Date.now();

    try {
      const report = await redeemEngine.executeBatch(members, code, {
        onProgress: async (progressInfo) => {
          // Throttle Discord editReply to once every 3 seconds to stay well within Discord API limits
          const now = Date.now();
          if (now - lastEditTime > 3000 || progressInfo.processed === progressInfo.total) {
            lastEditTime = now;
            try {
              const progressEmbed = createRedeemProgressEmbed(code, progressInfo);
              await interaction.editReply({ embeds: [progressEmbed] });
            } catch (editErr) {
              console.error('[KS Redeem] Failed to update progress embed:', editErr.message);
            }
          }
        }
      });

      // Final report embed
      const summaryEmbed = createRedeemSummaryEmbed(report);
      await interaction.editReply({ embeds: [summaryEmbed] });

    } catch (batchErr) {
      await interaction.editReply({
        content: `❌ **一括引き換え実行エラー**: ${batchErr.message}`
      });
    }
    return;
  }

  // 6. /ks_export or /sgr_export [format] (Officer/Admin only)
  if (normCmd === 'export') {
    if (!isOfficerOrAdmin(interaction)) {
      return interaction.reply({
        embeds: [createPermissionDeniedEmbed('同盟幹部 (Officer/Admin)')],
        ephemeral: true
      });
    }

    const format = interaction.options.getString('format') || 'csv';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);

    if (format === 'json') {
      const jsonContent = memberStore.exportToJSON(true);
      const buffer = Buffer.from(jsonContent, 'utf-8');
      const attachment = new AttachmentBuilder(buffer, { name: `kingshot_members_${timestamp}.json` });
      return interaction.reply({
        content: `📁 **KingShotメンバーデータ (JSONバックアップ)**:`,
        files: [attachment],
        ephemeral: true
      });
    } else {
      const csvContent = memberStore.exportToCSV();
      // Add UTF-8 BOM so Excel opens it with correct Japanese encoding
      const buffer = Buffer.concat([Buffer.from([0xEF, 0xBB, 0xBF]), Buffer.from(csvContent, 'utf-8')]);
      const attachment = new AttachmentBuilder(buffer, { name: `kingshot_members_${timestamp}.csv` });
      return interaction.reply({
        content: `📊 **KingShotメンバー名簿 (CSVエクスポート)**:`,
        files: [attachment],
        ephemeral: true
      });
    }
  }

  // 7. /ks_patrol or /sgr_patrol [force] (Officer/Admin only)
  if (normCmd === 'patrol') {
    if (!isOfficerOrAdmin(interaction)) {
      return interaction.reply({
        embeds: [createPermissionDeniedEmbed('同盟幹部 (Officer/Admin)')],
        ephemeral: true
      });
    }

    if (!giftPatrolService) {
      return interaction.reply({
        content: '⚠️ 自動パトロールサービスが準備中または初期化されていません。',
        ephemeral: true
      });
    }

    const force = interaction.options.getBoolean('force') || false;
    await interaction.deferReply();

    try {
      const result = await giftPatrolService.runPatrol({ forceAll: force });
      if (result.inProgress) {
        return interaction.editReply('⏳ 現在別のパトロール処理が実行中です。完了までしばらくお待ちください。');
      }

      if (result.newCodes.length === 0) {
        return interaction.editReply({
          content: `🔍 **パトロール完了**: 最新のギフトコード（\`${result.foundCodes.join(', ')}\`）を巡回・検知しました。未受取の新規コードはありませんでした。\nメンバー全員への引き換えは完了しています！`
        });
      }

      return interaction.editReply({
        content: `🎉 **パトロール＆自動引き換え完了**: 新規コード [**${result.newCodes.join(', ')}**] を検知し、全メンバーへ自動一括引き換えを実行しました！\nゲーム内メールをご確認ください。`
      });
    } catch (err) {
      return interaction.editReply(`❌ **パトロール実行エラー**: ${err.message}`);
    }
  }
}

module.exports = {
  getSgrSlashCommands,
  isOfficerOrAdmin,
  isSgrMember,
  handleSgrCommand
};
