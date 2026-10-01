/**
 * Antigravity Mobile Controller - Bot Bridge (Prototype)
 * 
 * Supports:
 * 1. Discord Bot with interactive buttons (Approve / Reject) for task authorization.
 * 2. Express Web Server to receive webhook events and task approval requests from Antigravity Core.
 */

require('dotenv').config();
const express = require('express');
const { Client, GatewayIntentBits, ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder, ModalBuilder, TextInputBuilder, TextInputStyle, StringSelectMenuBuilder, StringSelectMenuOptionBuilder } = require('discord.js');

const app = express();
app.use(express.json());
app.use(express.static(__dirname));

const PORT = process.env.PORT || 3000;
const AUTHORIZED_USERS = (process.env.AUTHORIZED_USERS || '').split(',');

const pendingApprovals = new Map();

const fs = require('fs');
const path = require('path');

const BRAIN_DIR = "C:\\Users\\s8933\\.gemini\\antigravity\\brain\\90887a3f-a9a3-4c23-b3b6-f2b33c34c88b";
const TRANSCRIPT_PATH = path.join(BRAIN_DIR, ".system_generated", "logs", "transcript.jsonl");
const MOBILE_CHAT_INPUTS_PATH = "c:\\Users\\s8933\\.gemini\\antigravity\\scratch\\multi-agent-designer\\mobile_chat_inputs.txt";
const TASK_PATH = path.join(BRAIN_DIR, "task.md");
const PLAN_PATH = path.join(BRAIN_DIR, "remote_control_design.md");
const WALKTHROUGH_PATH = path.join(BRAIN_DIR, "walkthrough.md");

// --- SGR Alliance Management Subsystem ---
const SgrMemberStore = require('./sgr_member_store');
const { SgrRedeemEngine } = require('./sgr_redeem_engine');
const { handleSgrCommand } = require('./sgr_commands');
const { KingShotApiClient } = require('./kingshot_api_client');
const { GiftPatrolService } = require('./gift_patrol_service');

const sgrStore = new SgrMemberStore();
sgrStore.init();
const kingShotApi = new KingShotApiClient();
const sgrRedeemEngine = new SgrRedeemEngine({
    intervalMs: 2500,
    redeemHandler: async (fid, code, member) => {
        if (process.env.SGR_SIMULATION_MODE === 'true') {
            return sgrRedeemEngine._defaultMockRedeemHandler(fid, code);
        }
        return kingShotApi.handleRedeemForEngine(fid, code, member);
    }
});

let giftPatrolService = null; // Will be initialized when discordClient is ready or created

function getRealTasksEmbed(filePath = TASK_PATH) {
    try {
        if (!fs.existsSync(filePath)) {
            return new EmbedBuilder()
                .setColor('#ef4444')
                .setTitle('📋 Antigravity タスクリスト')
                .setDescription('⚠️ タスクリストファイルが見つかりません。');
        }

        const data = fs.readFileSync(filePath, 'utf-8');
        const lines = data.split('\n');
        
        let title = '📋 Antigravity タスクリスト';
        let description = '';

        lines.forEach(line => {
            const cleanLine = line.trim();
            if (cleanLine.startsWith('# ')) {
                title = cleanLine.substring(2);
            } else if (cleanLine.startsWith('- [ ]')) {
                description += `⚪ ${cleanLine.substring(5).trim()}\n`;
            } else if (cleanLine.startsWith('- [/]')) {
                description += `🟡 ${cleanLine.substring(5).trim()}\n`;
            } else if (cleanLine.startsWith('- [x]') || cleanLine.startsWith('- [X]')) {
                description += `🟢 ${cleanLine.substring(5).trim()}\n`;
            } else if (cleanLine && !cleanLine.startsWith('-')) {
                description += `${cleanLine}\n`;
            }
        });

        return new EmbedBuilder()
            .setColor('#3b82f6')
            .setTitle(title)
            .setDescription(description || 'タスク項目がありません。')
            .setTimestamp();
    } catch (e) {
        return new EmbedBuilder()
            .setColor('#ef4444')
            .setTitle('📋 Antigravity タスクリスト')
            .setDescription(`⚠️ 読み込みエラー: ${e.message}`);
    }
}

function getRealFileEmbed(filePath, title, color) {
    try {
        if (!fs.existsSync(filePath)) {
            return new EmbedBuilder()
                .setColor('#ef4444')
                .setTitle(title)
                .setDescription('⚠️ ファイルが見つかりません。');
        }

        let content = fs.readFileSync(filePath, 'utf-8');
        // Clean up markdown title if any
        content = content.replace(/^#\s+.*$/m, '').trim();

        // Truncate to fit Discord description limit
        if (content.length > 2000) {
            content = content.substring(0, 1900) + '\n\n... (出力が長いため省略されました。詳細はPCで確認してください)';
        }

        return new EmbedBuilder()
            .setColor(color)
            .setTitle(title)
            .setDescription(content || '内容が空です。')
            .setTimestamp();
    } catch (e) {
        return new EmbedBuilder()
            .setColor('#ef4444')
            .setTitle(title)
            .setDescription(`⚠️ 読み込みエラー: ${e.message}`);
    }
}

function getLatestChatHistory(filePath = TRANSCRIPT_PATH) {
    try {
        if (!fs.existsSync(filePath)) {
            return "⚠️ チャット履歴ファイルが見つかりません。";
        }

        const data = fs.readFileSync(filePath, 'utf-8');
        const lines = data.trim().split('\n');
        const chatLogs = [];

        for (const line of lines) {
            if (!line) continue;
            try {
                const step = JSON.parse(line);
                if (step.type === 'USER_INPUT') {
                    let cleanContent = step.content || '';
                    const requestMatch = cleanContent.match(/<USER_REQUEST>([\s\S]*?)<\/USER_REQUEST>/);
                    if (requestMatch) {
                        cleanContent = requestMatch[1].trim();
                    } else {
                        cleanContent = cleanContent.replace(/<[\s\S]*?>/g, '').trim();
                    }
                    if (cleanContent) {
                        chatLogs.push({ sender: '👤 ユーザー', text: cleanContent });
                    }
                } else if (step.type === 'PLANNER_RESPONSE' && step.content) {
                    chatLogs.push({ sender: '🤖 Antigravity', text: step.content.trim() });
                }
            } catch (e) {
                // Ignore parse errors
            }
        }

        // Take last 5 messages
        const recentLogs = chatLogs.slice(-5);
        if (recentLogs.length === 0) {
            return "💬 チャット履歴はまだありません。";
        }

        return recentLogs.map(log => `**${log.sender}**:\n${log.text.substring(0, 500)}${log.text.length > 500 ? '...' : ''}\n`).join('\n────────────────\n\n');
    } catch (error) {
        console.error("Error reading chat history:", error);
        return `⚠️ チャット履歴の読み込み中にエラーが発生しました: ${error.message}`;
    }
}

function getAvailableProjects() {
    const parentDir = "C:\\Users\\s8933\\.gemini\\antigravity\\brain";
    if (!fs.existsSync(parentDir)) return [];

    const dirs = fs.readdirSync(parentDir).filter(name => {
        const fullPath = path.join(parentDir, name);
        return fs.statSync(fullPath).isDirectory() && name !== 'tempmediaStorage';
    });

    const projects = [];
    dirs.forEach(dirName => {
        const dirPath = path.join(parentDir, dirName);
        const taskPath = path.join(dirPath, 'task.md');
        let label = dirName.substring(0, 15) + '...'; // Fallback label
        
        if (fs.existsSync(taskPath)) {
            try {
                const content = fs.readFileSync(taskPath, 'utf-8');
                const firstLine = content.split('\n')[0].trim();
                if (firstLine.startsWith('# ')) {
                    label = firstLine.substring(2).trim();
                }
            } catch (e) {
                // Ignore errors
            }
        }

        // Limit label length for Discord limits (max 100 chars)
        if (label.length > 50) {
            label = label.substring(0, 47) + '...';
        }

        projects.push({
            id: dirName,
            label: label,
            path: dirPath
        });
    });

    return projects;
}

// --- Express Server (To receive requests from Antigravity local core) ---

/**
 * Endpoint called by Antigravity Core when a task requires user authorization.
 * POST /api/request-approval
 * Body: { taskId: "task_123", taskName: "Build & Test", description: "ビルドと単体テストを実行します", estimatedTime: "5分" }
 */
app.post('/api/request-approval', async (req, res) => {
    const { taskId, taskName, description, estimatedTime } = req.body;
    
    if (!taskId || !taskName) {
        return res.status(400).json({ error: "Missing taskId or taskName" });
    }

    console.log(`[APPROVAL REQUEST] Task: ${taskName} (ID: ${taskId})`);

    // Store the response object so we can reply later when the user clicks approve/reject on Discord
    pendingApprovals.set(taskId, res);

    // Send notification to Discord if Discord Bot is active
    if (discordClient && discordClient.isReady()) {
        try {
            // For prototype demo, we send to the first guild/channel the bot is in, or a designated channel ID
            const channel = discordClient.channels.cache.find(c => c.isTextBased());
            if (channel) {
                const embed = new EmbedBuilder()
                    .setColor('#8b5cf6')
                    .setTitle('🤖 Antigravity 承認要求')
                    .setDescription(`以下のタスクを実行してもよろしいですか？`)
                    .addFields(
                        { name: 'タスク名', value: taskName, inline: true },
                        { name: '想定時間', value: estimatedTime || '不明', inline: true },
                        { name: '説明', value: description || 'なし' }
                    )
                    .setTimestamp();

                const row = new ActionRowBuilder()
                    .addComponents(
                        new ButtonBuilder()
                            .setCustomId(`approve_${taskId}`)
                            .setLabel('👍 承認して実行')
                            .setStyle(ButtonStyle.Success),
                        new ButtonBuilder()
                            .setCustomId(`reject_${taskId}`)
                            .setLabel('🚷 却下・中止')
                            .setStyle(ButtonStyle.Danger)
                    );

                await channel.send({ embeds: [embed], components: [row] });
            }
        } catch (err) {
            console.error("Failed to send Discord approval message:", err);
        }
    }
});

/**
 * Test endpoint to simulate user clicking "Approve" via browser or curl.
 * GET /api/test-approve/:taskId
 */
app.get('/api/test-approve/:taskId', (req, res) => {
    const { taskId } = req.params;
    const pendingRes = pendingApprovals.get(taskId);
    if (!pendingRes) {
        return res.status(404).send(`Task ${taskId} not found or already approved/rejected.`);
    }
    pendingRes.json({ status: "APPROVED", authorizedBy: "TestUser(Simulated)" });
    pendingApprovals.delete(taskId);
    res.send(`Successfully simulated APPROVAL for task ${taskId}`);
});

// --- SGR Alliance Management Express Endpoints ---
app.get('/api/sgr/members', (req, res) => {
    res.json({
        stats: sgrStore.getStats(),
        members: sgrStore.getAllActiveMembers()
    });
});

app.get('/api/sgr/export', (req, res) => {
    const format = req.query.format || 'csv';
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    if (format === 'json') {
        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Content-Disposition', `attachment; filename="sgr_members_${timestamp}.json"`);
        return res.send(sgrStore.exportToJSON(true));
    }
    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="sgr_members_${timestamp}.csv"`);
    res.send('\uFEFF' + sgrStore.exportToCSV());
});

app.post('/api/sgr/patrol', async (req, res) => {
    if (!giftPatrolService) {
        return res.status(503).json({ error: 'Gift patrol service not initialized yet.' });
    }
    const forceAll = req.body && req.body.force === true;
    try {
        const result = await giftPatrolService.runPatrol({ forceAll });
        res.json({ success: true, ...result });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.post('/api/sgr/push-code', async (req, res) => {
    const { code } = req.body || {};
    if (!code) {
        return res.status(400).json({ error: 'Field "code" is required.' });
    }
    const activeMembers = sgrStore.getAllActiveMembers();
    if (activeMembers.length === 0) {
        return res.status(400).json({ error: 'No active members registered in SGR store.' });
    }
    try {
        const summary = await sgrRedeemEngine.startBatchRedemption(code, activeMembers);
        if (giftPatrolService) {
            await giftPatrolService._broadcastReport(code, summary);
        }
        res.json({ success: true, code, summary });
    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});


// --- Discord Bot Setup ---
let discordClient = null;

if (process.env.DISCORD_TOKEN && process.env.DISCORD_TOKEN !== 'your_discord_bot_token_here') {
    discordClient = new Client({
        intents: [
            GatewayIntentBits.Guilds,
            GatewayIntentBits.GuildMessages,
            GatewayIntentBits.MessageContent
        ]
    });

    discordClient.once('ready', () => {
        console.log(`[DISCORD] Logged in as ${discordClient.user.tag}`);
        console.log(`[SGR] Alliance subsystem ready. Registered active members: ${sgrStore.getAllActiveMembers().length}`);

        // Initialize and launch autonomous Gift Code Patrol
        giftPatrolService = new GiftPatrolService({
            redeemEngine: sgrRedeemEngine,
            memberStore: sgrStore,
            discordClient: discordClient,
            checkIntervalMs: 60 * 60 * 1000 // 1 hour interval
        });
        giftPatrolService.init();
        giftPatrolService.start(true); // Immediate initial check on startup
    });

    // Memory store for active tasks (Simulated database)
    const activeTasks = [
        {
            id: "task_001",
            name: "イベント情報スクレイピング",
            steps: [
                { text: "イベントWikiの解析", status: "completed" },
                { text: "レポート要約の作成", status: "running" },
                { text: "PDF書き出し", status: "pending" }
            ]
        },
        {
            id: "task_002",
            name: "コードのビルドとテスト",
            steps: [
                { text: "依存関係のダウンロード", status: "completed" },
                { text: "コードビルド", status: "completed" },
                { text: "単体テスト実行", status: "running" }
            ]
        }
    ];

    // Helper function to show reply modal popup
    function showReplyModal(interaction, taskId) {
        let taskName = taskId === 'main_chat' ? 'メイン対話' : taskId;
        const task = activeTasks.find(t => t.id === taskId);
        if (task) {
            taskName = task.name;
        } else {
            const projects = getAvailableProjects();
            const proj = projects.find(p => p.id === taskId);
            if (proj) taskName = proj.label;
        }

        const modal = new ModalBuilder()
            .setCustomId(`modal_reply_chat_${taskId}`)
            .setTitle(`${taskName.substring(0, 30)} への送信`);

        const chatMsgInput = new TextInputBuilder()
            .setCustomId('chat_msg_input')
            .setLabel("送信する指示・メッセージ")
            .setStyle(TextInputStyle.Paragraph)
            .setPlaceholder("例: 今のタスク状況を教えて / 一時停止して")
            .setRequired(true);

        const firstActionRow = new ActionRowBuilder().addComponents(chatMsgInput);
        modal.addComponents(firstActionRow);

        return interaction.showModal(modal);
    }

    // Handle button clicks, Select menus, & Modal submissions
    discordClient.on('interactionCreate', async interaction => {
        // KingShot & SGR Slash Commands (delegated to Command Handler with its own RBAC)
        if (interaction.isChatInputCommand() && (interaction.commandName.startsWith('ks_') || interaction.commandName.startsWith('sgr_'))) {
            try {
                return await handleSgrCommand(interaction, sgrStore, sgrRedeemEngine, giftPatrolService);
            } catch (err) {
                console.error('[KS/SGR Command Error]:', err);
                const replyMethod = (interaction.replied || interaction.deferred) ? 'followUp' : 'reply';
                return interaction[replyMethod]({
                    content: `❌ コマンド実行中にエラーが発生しました: \`${err.message}\``,
                    ephemeral: true
                }).catch(() => {});
            }
        }

        // Simple security check: Ensure the user is authorized
        if (AUTHORIZED_USERS.length > 0 && !AUTHORIZED_USERS.includes(interaction.user.id)) {
            return interaction.reply({ content: "⚠️ あなたはこの操作を行う権限がありません。", ephemeral: true });
        }

        // Handle Select Menu selections
        if (interaction.isStringSelectMenu()) {
            if (interaction.customId === 'select_task_view') {
                const selectedId = interaction.values[0];

                if (selectedId.startsWith('proj_')) {
                    const projectId = selectedId.replace('proj_', '');
                    
                    const fileSelectMenu = new StringSelectMenuBuilder()
                        .setCustomId(`select_file_view_${projectId}`)
                        .setPlaceholder('表示するデータを選択してください')
                        .addOptions(
                            new StringSelectMenuOptionBuilder()
                                .setLabel('💬 対話履歴 (transcript.jsonl)')
                                .setValue('chat'),
                            new StringSelectMenuOptionBuilder()
                                .setLabel('📋 タスクリスト (task.md)')
                                .setValue('tasks'),
                            new StringSelectMenuOptionBuilder()
                                .setLabel('📝 設計・計画')
                                .setValue('design'),
                            new StringSelectMenuOptionBuilder()
                                .setLabel('✨ 成果ウォークスルー')
                                .setValue('walkthrough')
                        );

                    const row = new ActionRowBuilder().addComponents(fileSelectMenu);
                    return interaction.reply({ content: `📁 プロジェクト [**${projectId.substring(0, 8)}**] のどのデータを確認しますか？`, components: [row], ephemeral: true });
                }

                if (selectedId === 'main_chat') {
                    const chatHistory = getLatestChatHistory();
                    const embed = new EmbedBuilder()
                        .setColor('#8b5cf6')
                        .setTitle('💬 メイン対話の履歴')
                        .setDescription(chatHistory)
                        .setTimestamp();
                    const replyRow = new ActionRowBuilder().addComponents(
                        new ButtonBuilder()
                            .setCustomId(`panel_reply_chat_main_chat`)
                            .setLabel(`✍️ メイン対話に返信する`)
                            .setStyle(ButtonStyle.Success)
                    );
                    return interaction.reply({ embeds: [embed], components: [replyRow], ephemeral: true });
                }

                if (selectedId === 'real_tasks') {
                    const embed = getRealTasksEmbed();
                    const replyRow = new ActionRowBuilder().addComponents(
                        new ButtonBuilder()
                            .setCustomId(`panel_reply_chat_real_tasks`)
                            .setLabel(`✍️ 新規タスクを PC に追加`)
                            .setStyle(ButtonStyle.Success)
                    );
                    return interaction.reply({ embeds: [embed], components: [replyRow], ephemeral: true });
                }

                if (selectedId === 'real_design') {
                    const embed = getRealFileEmbed(PLAN_PATH, "📝 設計プラン (remote_control_design.md)", "#10b981");
                    const replyRow = new ActionRowBuilder().addComponents(
                        new ButtonBuilder()
                            .setCustomId(`panel_reply_chat_real_design`)
                            .setLabel(`✍️ 設計にフィードバックを送る`)
                            .setStyle(ButtonStyle.Success)
                    );
                    return interaction.reply({ embeds: [embed], components: [replyRow], ephemeral: true });
                }

                if (selectedId === 'real_walkthrough') {
                    const embed = getRealFileEmbed(WALKTHROUGH_PATH, "✨ 変更点ウォークスルー (walkthrough.md)", "#f59e0b");
                    const replyRow = new ActionRowBuilder().addComponents(
                        new ButtonBuilder()
                            .setCustomId(`panel_reply_chat_real_walkthrough`)
                            .setLabel(`✍️ ウォークスルーにコメント送る`)
                            .setStyle(ButtonStyle.Success)
                    );
                    return interaction.reply({ embeds: [embed], components: [replyRow], ephemeral: true });
                }

                // Simulated tasks fallback
                const task = activeTasks.find(t => t.id === selectedId);
                if (task) {
                    let chatHistory = `🔥 **タスク名**: ${task.name}\n\n`;
                    task.steps.forEach(step => {
                        if (step.status === 'completed') {
                            chatHistory += `👤 **ユーザー**: ${step.text}をお願い。\n🤖 **エージェント**: 了解しました。\n🤖 **エージェント**: ✅ 「${step.text}」が完了しました。\n\n`;
                        } else if (step.status === 'running') {
                            chatHistory += `👤 **ユーザー**: 現在の状況を教えて。\n🤖 **エージェント**: 🟡 現在、「${step.text}」を自律処理中です。\n\n`;
                        }
                    });

                    const embed = new EmbedBuilder()
                        .setColor('#8b5cf6')
                        .setTitle(`💬 ${task.name.substring(0, 30)} の履歴`)
                        .setDescription(chatHistory)
                        .setTimestamp();

                    const replyRow = new ActionRowBuilder().addComponents(
                        new ButtonBuilder()
                            .setCustomId(`panel_reply_chat_${selectedId}`)
                            .setLabel(`✍️ このタスクにメッセージ送信`)
                            .setStyle(ButtonStyle.Success)
                    );
                    return interaction.reply({ embeds: [embed], components: [replyRow], ephemeral: true });
                }

                return interaction.reply({ content: "⚠️ 指定されたタスクが見つかりません。", ephemeral: true });
            }

            if (interaction.customId === 'select_task_reply') {
                const selectedId = interaction.values[0];
                if (selectedId.startsWith('proj_')) {
                    const projectId = selectedId.replace('proj_', '');
                    return showReplyModal(interaction, projectId);
                }
                return showReplyModal(interaction, selectedId);
            }

            if (interaction.customId.startsWith('select_file_view_')) {
                const projectId = interaction.customId.replace('select_file_view_', '');
                const fileType = interaction.values[0];
                const projPath = path.join("C:\\Users\\s8933\\.gemini\\antigravity\\brain", projectId);
                
                let embed;
                if (fileType === 'chat') {
                    const transcriptPath = path.join(projPath, '.system_generated', 'logs', 'transcript.jsonl');
                    const chatHistory = getLatestChatHistory(transcriptPath);
                    embed = new EmbedBuilder()
                        .setColor('#8b5cf6')
                        .setTitle(`💬 プロジェクト [${projectId.substring(0, 8)}] の履歴`)
                        .setDescription(chatHistory)
                        .setTimestamp();
                } else if (fileType === 'tasks') {
                    const taskPath = path.join(projPath, 'task.md');
                    embed = getRealTasksEmbed(taskPath);
                } else if (fileType === 'design') {
                    let designPath = path.join(projPath, 'implementation_plan.md');
                    if (!fs.existsSync(designPath)) {
                        designPath = path.join(projPath, 'remote_control_design.md');
                    }
                    embed = getRealFileEmbed(designPath, `📝 プロジェクト [${projectId.substring(0, 8)}] 設計プラン`, '#10b981');
                } else if (fileType === 'walkthrough') {
                    const wtPath = path.join(projPath, 'walkthrough.md');
                    embed = getRealFileEmbed(wtPath, `✨ プロジェクト [${projectId.substring(0, 8)}] ウォークスルー`, '#f59e0b');
                }

                const replyRow = new ActionRowBuilder().addComponents(
                    new ButtonBuilder()
                        .setCustomId(`panel_reply_chat_${projectId}`)
                        .setLabel(`✍️ メッセージ送信`)
                        .setStyle(ButtonStyle.Success)
                );

                return interaction.reply({ embeds: [embed], components: [replyRow], ephemeral: true });
            }
            return;
        }

        // Handle Modal submission
        if (interaction.isModalSubmit()) {
            if (interaction.customId === 'modal_add_task') {
                const taskName = interaction.fields.getTextInputValue('task_name_input');
                if (!taskName) {
                    return interaction.reply({ content: "⚠️ タスク名を入力してください。", ephemeral: true });
                }

                // Add to both activeTasks (simulated) and task.md (real)
                try {
                    if (fs.existsSync(TASK_PATH)) {
                        const taskContent = fs.readFileSync(TASK_PATH, 'utf-8');
                        const updatedContent = taskContent.trim() + `\n- [ ] 遠隔登録タスク: "${taskName}"\n`;
                        fs.writeFileSync(TASK_PATH, updatedContent, 'utf-8');
                    }
                } catch (err) {
                    console.error("Failed to append to task.md:", err);
                }

                const newTaskId = 'task_' + Math.random().toString(36).substr(2, 5);
                const newTask = {
                    id: newTaskId,
                    name: taskName,
                    steps: [
                        { text: "タスクの初期化", status: "completed" },
                        { text: "遠隔登録完了", status: "running" },
                        { text: "メイン処理待ち", status: "pending" }
                    ]
                };
                activeTasks.push(newTask);

                return interaction.reply({ 
                    content: `✅ 新しいタスクを追加しました！\n- **タスク名**: ${taskName}\n- **ID**: ${newTaskId}\n\nPC側の \`task.md\` にも書き込みました。「📋 タスク一覧」ボタンを押して進捗を確認してください。`,
                    ephemeral: true 
                });
            }

            if (interaction.customId.startsWith('modal_reply_chat_')) {
                const taskId = interaction.customId.replace('modal_reply_chat_', '');
                const chatMsg = interaction.fields.getTextInputValue('chat_msg_input');
                if (!chatMsg) {
                    return interaction.reply({ content: "⚠️ メッセージを入力してください。", ephemeral: true });
                }

                // Append message to local file
                const timestamp = new Date().toISOString();
                const logLine = `[${timestamp}] User (Discord) [Task: ${taskId}]: ${chatMsg}\n`;
                fs.appendFileSync(MOBILE_CHAT_INPUTS_PATH, logLine);

                // Dynamically update task.md (real) and activeTasks (simulated)
                const task = activeTasks.find(t => t.id === taskId);
                if (task) {
                    task.steps.push({ text: `遠隔指示: "${chatMsg}"`, status: "completed" });
                    task.steps.push({ text: `指示に基づきエージェントが自律処理中`, status: "running" });
                }

                // Write to target project's task.md & input file
                if (taskId === 'real_tasks' || taskId === 'main_chat' || taskId.length > 10) {
                    const targetProjId = (taskId === 'real_tasks' || taskId === 'main_chat') ? '90887a3f-a9a3-4c23-b3b6-f2b33c34c88b' : taskId;
                    const projPath = path.join("C:\\Users\\s8933\\.gemini\\antigravity\\brain", targetProjId);
                    
                    try {
                        const targetTaskPath = path.join(projPath, 'task.md');
                        if (fs.existsSync(targetTaskPath)) {
                            const taskContent = fs.readFileSync(targetTaskPath, 'utf-8');
                            const updatedContent = taskContent.trim() + `\n- [/] 遠隔指示の実行: "${chatMsg}"\n`;
                            fs.writeFileSync(targetTaskPath, updatedContent, 'utf-8');
                        }
                        
                        // Append to project specific chat input
                        const targetInputsPath = (targetProjId === '90887a3f-a9a3-4c23-b3b6-f2b33c34c88b') 
                            ? MOBILE_CHAT_INPUTS_PATH 
                            : path.join("c:\\Users\\s8933\\.gemini\\antigravity\\scratch", `mobile_chat_inputs_${targetProjId}.txt`);
                        fs.appendFileSync(targetInputsPath, logLine);
                    } catch (err) {
                        console.error("Failed to append to target project files:", err);
                    }
                }

                return interaction.reply({ 
                    content: `✅ メッセージをプロジェクト [${taskId.substring(0, 8)}] のエージェントに送信しました！\n\`\`\`text\n${chatMsg}\n\`\`\``,
                    ephemeral: true 
                });
            }
            return;
        }

        if (!interaction.isButton()) return;

        const customId = interaction.customId;

        // Remote Control Panel Handlers
        if (customId.startsWith('panel_')) {
            if (customId === 'panel_tasks') {
                const embed = getRealTasksEmbed();
                return interaction.reply({ embeds: [embed], ephemeral: true });
            }

            if (customId === 'panel_add_task') {
                const modal = new ModalBuilder()
                    .setCustomId('modal_add_task')
                    .setTitle('➕ 新規タスクの追加');

                const taskNameInput = new TextInputBuilder()
                    .setCustomId('task_name_input')
                    .setLabel("タスクの名前を入力してください")
                    .setStyle(TextInputStyle.Short)
                    .setPlaceholder("例: ドキュメント生成, ビルドテスト")
                    .setRequired(true);

                const firstActionRow = new ActionRowBuilder().addComponents(taskNameInput);
                modal.addComponents(firstActionRow);

                return interaction.showModal(modal);
            }

            if (customId === 'panel_view_chat') {
                const projects = getAvailableProjects();
                
                const selectMenu = new StringSelectMenuBuilder()
                    .setCustomId('select_task_view')
                    .setPlaceholder('のぞき込みたいプロジェクトを選択してください');

                // Add the current session at the top
                selectMenu.addOptions(
                    new StringSelectMenuOptionBuilder()
                        .setLabel('⭐ 現在の対話 (Antigravity)')
                        .setDescription('現在のこの開発セッションを表示します')
                        .setValue('proj_90887a3f-a9a3-4c23-b3b6-f2b33c34c88b')
                );

                projects.forEach(proj => {
                    if (proj.id !== '90887a3f-a9a3-4c23-b3b6-f2b33c34c88b') {
                        selectMenu.addOptions(
                            new StringSelectMenuOptionBuilder()
                                .setLabel(proj.label)
                                .setDescription(`ID: ${proj.id.substring(0, 8)}...`)
                                .setValue(`proj_${proj.id}`)
                        );
                    }
                });

                const row = new ActionRowBuilder().addComponents(selectMenu);
                return interaction.reply({ content: '🔍 **どのプロジェクトの状況を確認しますか？**', components: [row], ephemeral: true });
            }

            if (customId === 'panel_reply_chat') {
                const projects = getAvailableProjects();
                
                const selectMenu = new StringSelectMenuBuilder()
                    .setCustomId('select_task_reply')
                    .setPlaceholder('返信するプロジェクトを選択してください');

                // Add current session at the top
                selectMenu.addOptions(
                    new StringSelectMenuOptionBuilder()
                        .setLabel('⭐ 現在の対話 (Antigravity)')
                        .setValue('proj_90887a3f-a9a3-4c23-b3b6-f2b33c34c88b')
                );

                projects.forEach(proj => {
                    if (proj.id !== '90887a3f-a9a3-4c23-b3b6-f2b33c34c88b') {
                        selectMenu.addOptions(
                            new StringSelectMenuOptionBuilder()
                                .setLabel(proj.label)
                                .setValue(`proj_${proj.id}`)
                        );
                    }
                });

                const row = new ActionRowBuilder().addComponents(selectMenu);
                return interaction.reply({ content: '✍️ **どのプロジェクトにメッセージを送信しますか？**', components: [row], ephemeral: true });
            }

            if (customId.startsWith('panel_reply_chat_')) {
                const taskId = customId.replace('panel_reply_chat_', '');
                return showReplyModal(interaction, taskId);
            }

            if (customId === 'panel_hostname') {
                const { exec } = require('child_process');
                exec('hostname', (error, stdout, stderr) => {
                    const host = stdout ? stdout.trim() : "不明なホスト";
                    interaction.reply({ content: `💻 **PCホスト名**: \`${host}\` (接続正常)`, ephemeral: true });
                });
                return;
            }

            if (customId === 'panel_run_demo') {
                const mockTaskId = 'task_' + Math.random().toString(36).substr(2, 9);
                interaction.reply({ content: "🚀 承認デモを開始します。以下にボタンが届きます...", ephemeral: true });

                const http = require('http');
                const postData = JSON.stringify({
                    taskId: mockTaskId,
                    taskName: "リモコン起動デモ",
                    description: "スマホ遠隔ボタンによるデモタスクの開始",
                    estimatedTime: "5分"
                });

                const reqOpts = {
                    hostname: 'localhost',
                    port: PORT,
                    path: '/api/request-approval',
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(postData)
                    }
                };

                const req = http.request(reqOpts, (res) => {});
                req.on('error', err => console.error(err));
                req.write(postData);
                req.end();
                return;
            }
            return;
        }

        // Original task approval handlers
        const parts = customId.split('_');
        const action = parts[0];
        const taskId = parts.slice(1).join('_');
        const res = pendingApprovals.get(taskId);

        if (!res) {
            return interaction.reply({ content: "⚠️ このタスクの承認要求は既に期限切れか、存在しません。", ephemeral: true });
        }

        if (action === 'approve') {
            res.json({ status: "APPROVED", authorizedBy: interaction.user.tag });
            pendingApprovals.delete(taskId);
            
            await interaction.update({
                content: `✅ **承認されました** (承認者: ${interaction.user.username})`,
                components: []
            });
        } else if (action === 'reject') {
            res.json({ status: "REJECTED", authorizedBy: interaction.user.tag });
            pendingApprovals.delete(taskId);

            await interaction.update({
                content: `❌ **却下されました** (操作者: ${interaction.user.username})`,
                components: []
            });
        }
    });

    // Handle normal text commands
    discordClient.on('messageCreate', async message => {
        if (message.author.bot) return;

        const content = message.content.trim();

        // --- Text Fallback for SGR Commands (e.g. "/sgr_register 12345" or "!sgr_register 12345") ---
        const sgrMatch = content.match(/^[/!]sgr_([a-zA-Z0-9_]+)(?:\s+(.*))?$/i);
        if (sgrMatch) {
            const subCmd = sgrMatch[1].toLowerCase();
            const rawArgs = (sgrMatch[2] || '').trim();

            if (subCmd === 'register') {
                let fid = '';
                let kid = '';

                const fidMatch = rawArgs.match(/fid[:=\s]+([0-9a-zA-Z_]+)/i);
                const kidMatch = rawArgs.match(/kid[:=\s]+([0-9a-zA-Z_]+)/i);

                if (fidMatch) fid = fidMatch[1];
                if (kidMatch) kid = kidMatch[1];

                if (!fid || !kid) {
                    const tokens = rawArgs.replace(/fid:|kid:/gi, ' ').split(/\s+/).filter(Boolean);
                    if (!fid && tokens.length > 0) fid = tokens[0];
                    if (!kid && tokens.length > 1) kid = tokens[1];
                }

                if (!fid) {
                    return message.reply('⚠️ プレイヤーIDと所属王国（Kingdom番号）を指定してください。\n例: `/sgr_register fid:137197289 kid:898` または `!sgr_register 137197289 898`');
                }

                const res = sgrStore.registerMember({
                    discord_user_id: message.author.id,
                    discord_username: message.author.tag || message.author.username,
                    kingshot_player_id: fid,
                    kingshot_kingdom_id: kid
                });
                if (!res.success) {
                    return message.reply(`❌ 登録エラー: ${res.error}`);
                }
                const isUpdate = res.action === 'updated';
                return message.reply({
                    embeds: [
                        new EmbedBuilder()
                            .setColor('#10b981')
                            .setTitle(isUpdate ? '🔄 SGRプレイヤーID更新完了' : '🎉 SGRメンバー登録完了')
                            .setDescription(`KingShotプレイヤー情報を連携しました。\nギフトコード一括受け取りの対象になります！`)
                            .addFields(
                                { name: 'Discordユーザー', value: `<@${message.author.id}>`, inline: true },
                                { name: 'Player ID (FID)', value: `\`${fid}\``, inline: true },
                                { name: '所属王国 (Kingdom)', value: kid ? `\`#${kid}\`` : '⚠️ 未設定 (要kid指定)', inline: true }
                            )
                            .setTimestamp()
                    ]
                });
            } else if (subCmd === 'myid') {
                const member = sgrStore.getMember(message.author.id);
                if (!member || !member.active_flag) {
                    return message.reply('ℹ️ あなたのKingShotプレイヤーIDは未登録です。\n`/sgr_register fid:あなたのID` で登録してください。');
                }
                return message.reply({
                    embeds: [
                        new EmbedBuilder()
                            .setColor('#3b82f6')
                            .setTitle('👤 登録中のKingShotプレイヤーID')
                            .addFields(
                                { name: 'Discordユーザー', value: `<@${message.author.id}>`, inline: true },
                                { name: 'Player ID (FID)', value: `\`${member.kingshot_player_id}\``, inline: true },
                                { name: '登録日時', value: new Date(member.registered_at).toLocaleString('ja-JP') }
                            )
                            .setTimestamp()
                    ]
                });
            } else if (subCmd === 'list') {
                const active = sgrStore.getAllActiveMembers();
                const textList = active.length === 0 
                    ? '登録メンバーはいません。' 
                    : active.map((m, i) => `${i + 1}. <@${m.discord_user_id}> (FID: \`${m.kingshot_player_id}\`)`).join('\n');
                return message.reply({
                    embeds: [
                        new EmbedBuilder()
                            .setColor('#8b5cf6')
                            .setTitle(`📋 SGR登録メンバー名簿 (全${active.length}名)`)
                            .setDescription(textList)
                            .setTimestamp()
                    ]
                });
            } else if (subCmd === 'redeem') {
                const codeMatch = rawArgs.match(/(?:code:)?\s*([0-9a-zA-Z_]+)/i);
                if (!codeMatch) {
                    return message.reply('⚠️ ギフトコードを指定してください。\n例: `/sgr_redeem code:VIP777`');
                }
                const code = codeMatch[1];
                const activeMembers = sgrStore.getAllActiveMembers();
                if (activeMembers.length === 0) {
                    return message.reply('⚠️ 登録されているメンバーがいません。まず `/sgr_register fid:ID` で登録してください。');
                }
                const progressMsg = await message.reply(`🚀 ギフトコード \`${code}\` の一括入力を開始します... (全${activeMembers.length}名)`);
                const summary = await sgrRedeemEngine.startBatchRedemption(code, activeMembers, async (prog) => {
                    await progressMsg.edit(`⏳ 進行中: [${prog.percent}%] (${prog.current}/${prog.total}) ...`);
                });
                return progressMsg.edit({
                    content: '✅ ギフトコード一括入力が完了しました！',
                    embeds: [
                        new EmbedBuilder()
                            .setColor('#10b981')
                            .setTitle('🎁 SGRギフトコード一括受け取り結果レポート')
                            .setDescription(`対象コード: **\`${code}\`**\nメンバー全員のゲーム内メールを確認してください。`)
                            .addFields(
                                { name: '総対象数', value: `${summary.totalCount} 名`, inline: true },
                                { name: '受取成功', value: `🟢 ${summary.statusCounts.SUCCESS} 件`, inline: true },
                                { name: '既に受取済', value: `🟡 ${summary.statusCounts.ALREADY_CLAIMED} 件`, inline: true },
                                { name: '期限切れ', value: `🔴 ${summary.statusCounts.EXPIRED} 件`, inline: true },
                                { name: '無効なID', value: `🟠 ${summary.statusCounts.INVALID_ID} 件`, inline: true },
                                { name: '失敗/エラー', value: `⚪ ${summary.statusCounts.FAILED} 件`, inline: true }
                            )
                            .setTimestamp()
                    ]
                });
            }
        }

        // Command validation for admin panel
        if (AUTHORIZED_USERS.length > 0 && !AUTHORIZED_USERS.includes(message.author.id)) return;
        
        // Remote Control Panel command
        if (content === '!panel') {
            const embed = new EmbedBuilder()
                .setColor('#10b981')
                .setTitle('🎛️ Antigravity 遠隔リモコン')
                .setDescription('スマホからPCのエージェントを操作・監視します。\n下のボタンをタップしてください。')
                .setTimestamp();

            const row1 = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('panel_tasks')
                        .setLabel('📋 タスク一覧')
                        .setStyle(ButtonStyle.Primary),
                    new ButtonBuilder()
                        .setCustomId('panel_add_task')
                        .setLabel('➕ 新規タスク追加')
                        .setStyle(ButtonStyle.Success),
                    new ButtonBuilder()
                        .setCustomId('panel_run_demo')
                        .setLabel('🚀 承認テスト')
                        .setStyle(ButtonStyle.Danger)
                );

            const row2 = new ActionRowBuilder()
                .addComponents(
                    new ButtonBuilder()
                        .setCustomId('panel_view_chat')
                        .setLabel('💬 チャット表示')
                        .setStyle(ButtonStyle.Primary),
                    new ButtonBuilder()
                        .setCustomId('panel_reply_chat')
                        .setLabel('✍️ チャット返信')
                        .setStyle(ButtonStyle.Success),
                    new ButtonBuilder()
                        .setCustomId('panel_hostname')
                        .setLabel('💻 PC名確認')
                        .setStyle(ButtonStyle.Secondary)
                );

            return message.reply({ embeds: [embed], components: [row1, row2] });
        }

        // 1. !tasks - View all active tasks and their progress
        if (content === '!tasks') {
            if (activeTasks.length === 0) {
                return message.reply("📋 現在実行中のタスクはありません。");
            }

            const embed = new EmbedBuilder()
                .setColor('#3b82f6')
                .setTitle('📋 現在進行中のタスク一覧')
                .setTimestamp();

            activeTasks.forEach(task => {
                let stepsText = '';
                task.steps.forEach((step, idx) => {
                    let statusSymbol = '⚪';
                    if (step.status === 'completed') statusSymbol = '🟢 [完了]';
                    if (step.status === 'running') statusSymbol = '🟡 [実行中]';
                    if (step.status === 'pending') statusSymbol = '⚪ [未着手]';
                    stepsText += `${idx + 1}. ${statusSymbol} ${step.text}\n`;
                });

                embed.addFields({
                    name: `🔥 ${task.name} (ID: ${task.id})`,
                    value: stepsText || 'ステップなし'
                });
            });

            return message.reply({ embeds: [embed] });
        }

        // 2. !tasks add [Task Name] - Register a new task from Discord
        if (content.startsWith('!tasks add ')) {
            const newTaskName = content.slice(11);
            if (!newTaskName) return message.reply("⚠️ タスク名を入力してください。例: `!tasks add 新機能のビルド`");

            const newTaskId = 'task_' + Math.random().toString(36).substr(2, 5);
            const newTask = {
                id: newTaskId,
                name: newTaskName,
                steps: [
                    { text: "タスクの初期化", status: "completed" },
                    { text: "実行前チェック", status: "running" },
                    { text: "メイン処理", status: "pending" }
                ]
            };
            activeTasks.push(newTask);

            return message.reply(`✅ 新しいタスクを追加しました！\n- **タスク名**: ${newTaskName}\n- **ID**: ${newTaskId}\n\n詳細を見るには ` + "`!tasks`" + ` を実行してください。`);
        }

        // 3. !cmd [Command] - Run an OS command on the host machine
        if (content.startsWith('!cmd ')) {
            const commandToRun = content.slice(5);
            if (!commandToRun) return message.reply("⚠️ 実行するコマンドを入力してください。例: `!cmd dir`");

            // Security check: simple prevention of dangerous symbols (illustrative)
            if (commandToRun.includes('del ') || commandToRun.includes('rmdir ') || commandToRun.includes('Format-')) {
                return message.reply("❌ セキュリティポリシーにより、そのコマンドの実行は拒否されました。");
            }

            message.reply(`💻 PC上でコマンド 「${commandToRun}」 を実行中...`);

            const { exec } = require('child_process');
            // Execute command on local machine
            exec(commandToRun, { cwd: __dirname }, (error, stdout, stderr) => {
                let responseText = '';
                
                if (stdout) {
                    responseText += `**【標準出力 (stdout)】**\n\`\`\`\n${stdout.substring(0, 1500)}\n\`\`\`\n`;
                }
                if (stderr) {
                    responseText += `**【標準エラー (stderr)】**\n\`\`\`\n${stderr.substring(0, 500)}\n\`\`\`\n`;
                }
                if (error) {
                    responseText += `❌ **実行エラー**: ${error.message}\n`;
                }

                if (!responseText) {
                    responseText = "✅ コマンドは出力なしで正常に完了しました。";
                }

                // If response is too long, split or truncate to fit Discord's 2000 character limit
                if (responseText.length > 2000) {
                    responseText = responseText.substring(0, 1900) + "\n... (出力が長いため省略されました)";
                }

                message.channel.send(responseText);
            });
            return;
        }

        // 5. !view - View the latest pair-programming chat history
        if (content === '!view') {
            const chatHistory = getLatestChatHistory();
            const embed = new EmbedBuilder()
                .setColor('#8b5cf6')
                .setTitle('💬 現在のペアプロチャットログ (最新5件)')
                .setDescription(chatHistory)
                .setTimestamp();
            return message.reply({ embeds: [embed] });
        }

        // 6. !chat [message] - Send a message/instruction to the local agent file
        if (content.startsWith('!chat ')) {
            const chatMsg = content.slice(6);
            if (!chatMsg) return message.reply("⚠️ 送信するメッセージを入力してください。例: `!chat レイアウトを修正して`");

            const timestamp = new Date().toISOString();
            const logLine = `[${timestamp}] User (Discord): ${chatMsg}\n`;
            fs.appendFileSync(MOBILE_CHAT_INPUTS_PATH, logLine);

            return message.reply(`✅ メッセージをPCのエージェントに送信しました！\n\`\`\`text\n${chatMsg}\n\`\`\``);
        }

        // 4. !run [Task Name] - Original simulation flow
        if (content.startsWith('!run ')) {
            const taskName = content.slice(5);
            const mockTaskId = 'task_' + Math.random().toString(36).substr(2, 9);
            
            message.reply(`🚀 タスク 「${taskName}」 の実行プランを構築中...`);

            // Simulate call to /api/request-approval after a delay
            setTimeout(() => {
                const http = require('http');
                const postData = JSON.stringify({
                    taskId: mockTaskId,
                    taskName: taskName,
                    description: "スマホ遠隔指示による自律ビルドタスクの開始",
                    estimatedTime: "3分"
                });

                const reqOpts = {
                    hostname: 'localhost',
                    port: PORT,
                    path: '/api/request-approval',
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Content-Length': Buffer.byteLength(postData)
                    }
                };

                const req = http.request(reqOpts, (res) => {
                    let data = '';
                    res.on('data', chunk => data += chunk);
                    res.on('end', () => {
                        try {
                            const result = JSON.parse(data);
                            message.channel.send(`⚙️ **エージェント通知**: タスク 「${taskName}」 がユーザーにより **${result.status}** されました。`);
                        } catch (e) {
                            console.error("Failed to parse response in mock trigger:", data);
                        }
                    });
                });
                req.on('error', err => console.error("Mock trigger HTTP request error:", err));
                req.write(postData);
                req.end();
            }, 1500);
        }
    });

    discordClient.login(process.env.DISCORD_TOKEN).catch(err => {
        console.error("[DISCORD] Failed to login. Check your token in .env:", err);
    });
} else {
    console.log("[INFO] Discord token not provided or default. Running express server only.");
}

app.listen(PORT, () => {
    console.log(`[SERVER] Antigravity Bot Bridge listening on port ${PORT}`);
    console.log(`[SERVER] Ready to receive approval requests at http://localhost:${PORT}/api/request-approval`);
});

// Guardrails against unhandled process crashes
process.on('uncaughtException', err => {
    console.error('[UNCAUGHT EXCEPTION]:', err);
});
process.on('unhandledRejection', (reason, promise) => {
    console.error('[UNHANDLED REJECTION]:', reason);
});
