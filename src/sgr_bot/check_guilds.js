require('dotenv').config();
const { REST, Routes } = require('discord.js');

const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);

async function checkGuilds() {
    console.log('Fetching guilds the bot is currently in...');
    const guilds = await rest.get(Routes.userGuilds());
    console.log(`Bot is in ${guilds.length} guilds:`);
    guilds.forEach(g => {
        console.log(` - Name: "${g.name}", ID: ${g.id}`);
    });
    return guilds;
}

checkGuilds().catch(console.error);
