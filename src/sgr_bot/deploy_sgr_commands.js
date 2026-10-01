'use strict';

require('dotenv').config();
const { REST, Routes } = require('discord.js');
const { getSgrSlashCommands } = require('./sgr_commands');

async function deployCommands() {
  const token = process.env.DISCORD_TOKEN;
  const clientId = process.env.DISCORD_CLIENT_ID;
  const guildId = process.env.DISCORD_GUILD_ID;

  if (!token || token === 'your_discord_bot_token_here') {
    console.error('❌ Error: DISCORD_TOKEN is missing or default in .env');
    process.exit(1);
  }

  if (!clientId || clientId === 'your_discord_client_id_here') {
    console.error('❌ Error: DISCORD_CLIENT_ID is missing in .env');
    process.exit(1);
  }

  const commands = getSgrSlashCommands().map(cmd => cmd.toJSON());
  const rest = new REST({ version: '10' }).setToken(token);

  console.log(`📡 Registering ${commands.length} SGR Slash Commands...`);
  commands.forEach(cmd => console.log(`   - /${cmd.name}: ${cmd.description}`));

  try {
    // 1. Deploy globally so the bot works in ANY server it is invited to
    console.log('🌐 Deploying global commands (enables bot in ANY server it joins)...');
    const globalData = await rest.put(
      Routes.applicationCommands(clientId),
      { body: commands }
    );
    console.log(`✅ Successfully deployed ${globalData.length} global commands!`);

    // 2. Deploy to specific guild for instant propagation without cache wait
    if (guildId) {
      console.log(`⚡ Deploying guild-specific commands to Guild ID: ${guildId} (Instant propagation)...`);
      const guildData = await rest.put(
        Routes.applicationGuildCommands(clientId, guildId),
        { body: commands }
      );
      console.log(`✅ Successfully deployed ${guildData.length} guild commands!`);
    }
  } catch (error) {
    console.error('❌ Failed to deploy slash commands:', error);
    process.exit(1);
  }
}

if (require.main === module) {
  deployCommands();
}

module.exports = deployCommands;
