'use strict';

const { EmbedBuilder } = require('discord.js');
const { RedeemStatus } = require('./sgr_redeem_engine');

/**
 * Creates a Discord Embed for successful registration.
 */
function createRegisterEmbed(member, isNew = true, totalAccounts = 1) {
  const kidText = member.kingshot_kingdom_id ? `#${member.kingshot_kingdom_id}` : '未設定';
  const accountNote = totalAccounts > 1 ? ` (現在 **${totalAccounts}** アカウント連携中)` : '';
  return new EmbedBuilder()
    .setColor('#10b981') // Emerald green
    .setTitle(isNew ? `✅ 【KingShot】アカウント登録完了${accountNote}` : `🔄 【KingShot】アカウント情報更新完了`)
    .setDescription(`DiscordアカウントとKingShotプレイヤーID（FID）の連携が完了しました！今後のギフトコード自動引き換えの対象となります。`)
    .addFields(
      { name: '👤 Discordユーザー', value: `<@${member.discord_user_id}> (${member.discord_username})`, inline: true },
      { name: '👑 KingShot FID', value: `\`${member.kingshot_player_id}\``, inline: true },
      { name: '🏰 所属王国 (KID)', value: `\`${kidText}\``, inline: true },
      { name: '🕒 登録日時', value: new Date(member.registered_at).toLocaleString('ja-JP', { timeZone: 'Asia/Tokyo' }), inline: false }
    )
    .setFooter({ text: 'KingShot Gift Code Automation Bot • メイン＆サブ複数登録対応' })
    .setTimestamp();
}

/**
 * Creates a Discord Embed for viewing my ID(s) (supports multiple accounts).
 */
function createMyIdEmbed(members) {
  const memberList = Array.isArray(members) ? members : (members ? [members] : []);

  if (memberList.length === 0) {
    return new EmbedBuilder()
      .setColor('#f59e0b') // Amber
      .setTitle('⚠️ 【KingShot】未登録アカウント')
      .setDescription('あなたのDiscordアカウントにはまだKingShotのプレイヤーIDが登録されていません。\n`/ks_register fid:あなたのFID kid:あなたの王国番号` コマンドで登録してください。')
      .setFooter({ text: 'KingShot Gift Code Automation Bot' });
  }

  const embed = new EmbedBuilder()
    .setColor('#3b82f6') // Blue
    .setTitle(`👑 【KingShot】登録アカウント確認 (${memberList.length} アカウント連携中)`)
    .setDescription(`現在あなたのDiscordアカウントに連携されているKingShotアカウント一覧です。\n**登録されているすべてのアカウント宛てに、最新ギフトコードが自動で配布されます！**`)
    .setFooter({ text: '追加登録: /ks_register fid:[FID] kid:[王国] | 解除: /ks_unregister' })
    .setTimestamp();

  memberList.forEach((m, idx) => {
    const kidText = m.kingshot_kingdom_id ? `#${m.kingshot_kingdom_id}` : '未設定';
    const tag = idx === 0 ? '👑 [メイン]' : `🛡️ [サブ ${idx}]`;
    embed.addFields({
      name: `${tag} プレイヤーID (FID): \`${m.kingshot_player_id}\``,
      value: `🏰 所属王国: \`${kidText}\` | 🟢 ステータス: 有効 (自動受取対象)\n📅 登録日: ${new Date(m.registered_at).toLocaleDateString('ja-JP', { timeZone: 'Asia/Tokyo' })}`,
      inline: false
    });
  });

  return embed;
}

/**
 * Creates a Discord Embed for SGR Member List (Admin/Officer).
 */
function createMemberListEmbed(members, page = 1, pageSize = 15) {
  const total = members.length;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));
  const currentPage = Math.min(Math.max(1, page), maxPage);
  const start = (currentPage - 1) * pageSize;
  const pageMembers = members.slice(start, start + pageSize);

  const embed = new EmbedBuilder()
    .setColor('#8b5cf6') // Purple
    .setTitle(`🛡️ 【SGR同盟】登録メンバー名簿 (全 ${total} 名)`)
    .setDescription(`ギフトコード一括受け取り対象のアクティブメンバー一覧です。\nページ: **${currentPage} / ${maxPage}**`)
    .setFooter({ text: 'SGR Alliance Commander Bot • 幹部専用' })
    .setTimestamp();

  if (pageMembers.length === 0) {
    embed.addFields({ name: '登録メンバー', value: '登録されたメンバーはいません。' });
    return embed;
  }

  let text = '```text\n#   | Discord Username    | KingShot FID \n----+---------------------+--------------\n';
  pageMembers.forEach((m, idx) => {
    const num = String(start + idx + 1).padStart(3, ' ');
    const uname = (m.discord_username || 'Unknown').substring(0, 19).padEnd(19, ' ');
    const fid = (m.kingshot_player_id || '').substring(0, 12).padEnd(12, ' ');
    text += `${num} | ${uname} | ${fid}\n`;
  });
  text += '```';

  embed.addFields({ name: 'メンバーリスト', value: text });
  return embed;
}

/**
 * Generate a visual text progress bar.
 */
function generateProgressBar(percent, length = 15) {
  const filled = Math.min(length, Math.max(0, Math.round((percent / 100) * length)));
  const empty = length - filled;
  return '█'.repeat(filled) + '░'.repeat(empty);
}

/**
 * Creates an in-progress redemption embed.
 */
function createRedeemProgressEmbed(code, progressInfo) {
  const { processed, total, percent, counts, latest } = progressInfo;
  const bar = generateProgressBar(percent, 16);

  return new EmbedBuilder()
    .setColor('#f59e0b') // Amber/Gold
    .setTitle(`⏳ 【SGR同盟】ギフトコード一括受け取り処理中...`)
    .setDescription(`コード: **\`${code}\`**\nAPI負荷防止のため、2〜3秒間隔で順次処理しています。\n\n進捗: **[${bar}] ${percent}%** (${processed} / ${total})`)
    .addFields(
      { name: '🟢 成功', value: `${counts[RedeemStatus.SUCCESS]} 件`, inline: true },
      { name: '🟡 獲得済み', value: `${counts[RedeemStatus.ALREADY_CLAIMED]} 件`, inline: true },
      { name: '🔴 期限切れ', value: `${counts[RedeemStatus.EXPIRED]} 件`, inline: true },
      { name: '⚠️ 無効ID', value: `${counts[RedeemStatus.INVALID_ID]} 件`, inline: true },
      { name: '❌ エラー', value: `${counts[RedeemStatus.FAILED]} 件`, inline: true },
      { name: '🕒 最新処理', value: latest ? `<@${latest.discord_user_id}> (${latest.fid}): ${latest.status}` : '開始中...', inline: false }
    )
    .setFooter({ text: '同盟員への一括還元中 • SGR Commander' })
    .setTimestamp();
}

/**
 * Creates final summary report embed for batch redemption.
 */
function createRedeemSummaryEmbed(report) {
  const { code, total, counts, startTime, endTime } = report;
  const successCount = counts[RedeemStatus.SUCCESS];
  const claimedCount = counts[RedeemStatus.ALREADY_CLAIMED];
  const expiredCount = counts[RedeemStatus.EXPIRED];
  const invalidIdCount = counts[RedeemStatus.INVALID_ID];
  const failedCount = counts[RedeemStatus.FAILED];

  const durationSec = Math.round((new Date(endTime) - new Date(startTime)) / 1000);

  return new EmbedBuilder()
    .setColor(successCount > 0 ? '#10b981' : (expiredCount > 0 ? '#ef4444' : '#6b7280'))
    .setTitle(`🎉 【SGR同盟】ギフトコード一括受け取り 完了レポート`)
    .setDescription(`対象ギフトコード: **\`${code}\`**\n全 **${total}** 名のSGRメンバーに対する配布処理が完了しました！`)
    .addFields(
      { name: '🟢 引き換え成功', value: `**${successCount}** 名`, inline: true },
      { name: '🟡 すでに獲得済み', value: `**${claimedCount}** 名`, inline: true },
      { name: '🔴 コード期限切れ', value: `**${expiredCount}** 名`, inline: true },
      { name: '⚠️ 存在しないFID', value: `**${invalidIdCount}** 名`, inline: true },
      { name: '❌ 失敗・通信エラー', value: `**${failedCount}** 名`, inline: true },
      { name: '⏱️ 総所要時間', value: `${durationSec} 秒 (安全レートリミット適用)`, inline: true }
    )
    .setFooter({ text: 'SGR Alliance Commander Bot • Batch Report' })
    .setTimestamp();
}

/**
 * Permission denied embed.
 */
function createPermissionDeniedEmbed(requiredRoleOrPerm = '同盟幹部 (Officer/Admin)') {
  return new EmbedBuilder()
    .setColor('#ef4444')
    .setTitle('🚫 アクセス権限がありません')
    .setDescription(`このコマンドを実行するには **${requiredRoleOrPerm}** の権限またはロールが必要です。`)
    .setFooter({ text: 'SGR Alliance Security' })
    .setTimestamp();
}

module.exports = {
  createRegisterEmbed,
  createMyIdEmbed,
  createMemberListEmbed,
  createRedeemProgressEmbed,
  createRedeemSummaryEmbed,
  createPermissionDeniedEmbed
};
