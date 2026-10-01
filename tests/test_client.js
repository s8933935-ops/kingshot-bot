/**
 * Antigravity Mobile Controller - Test Client (Prototype Sim)
 * 
 * This script simulates the Antigravity local agent core sending an approval request
 * to the bot bridge server. It then waits for the server to reply with the user's decision.
 */

const http = require('http');

const payload = JSON.stringify({
    taskId: "task_test_999",
    taskName: "プロダクション環境へのデプロイ",
    description: "ソースコードをAWS本番サーバーに配置し、マイグレーションを実行します。",
    estimatedTime: "8分"
});

const options = {
    hostname: 'localhost',
    port: 3000,
    path: '/api/request-approval',
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload)
    }
};

console.log("🚀 [Agent Sim] 送信準備中: 承認要求をボットサーバーに送信します...");
console.log(`- タスク: デプロイ実行 (ID: task_test_999)`);

const req = http.request(options, (res) => {
    let data = '';

    res.on('data', (chunk) => {
        data += chunk;
    });

    res.on('end', () => {
        console.log(`\n📥 [Agent Sim] レスポンス受信 (ステータスコード: ${res.statusCode})`);
        try {
            const result = JSON.parse(data);
            console.log("-----------------------------------------");
            console.log(`🤖 承認判定結果: ${result.status}`);
            console.log(`👤 操作ユーザー: ${result.authorizedBy || 'なし'}`);
            console.log("-----------------------------------------");
            if (result.status === 'APPROVED') {
                console.log("✅ [Agent Sim] 承認されました。デプロイ処理を開始します！");
            } else {
                console.log("❌ [Agent Sim] 却下されました。処理を中断します。");
            }
        } catch (e) {
            console.error("❌ レスポンスの解析に失敗しました:", data);
        }
    });
});

req.on('error', (error) => {
    console.error(`\n❌ ボットサーバーへの接続エラー: ${error.message}`);
    console.log("💡 サーバー(bot_controller.js)が起動しているか確認してください（ポート: 3000）");
});

req.write(payload);
req.end();
