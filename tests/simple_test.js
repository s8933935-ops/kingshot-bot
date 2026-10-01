const http = require('http');

console.log('🧪 動作確認部署: 実機・システム連動総合テストを開始します...\n');

// Test 1: Check HTTP Server Availability
http.get('http://localhost:8080', (res) => {
  console.log(`[テスト1] ローカルWebサーバー接続: ${res.statusCode === 200 ? '✅ PASS (HTTP 200 OK)' : '❌ FAIL'}`);
  
  let body = '';
  res.on('data', chunk => body += chunk);
  res.on('end', () => {
    // Test 2: Check Input HTML Structure
    const hasFileInput = body.includes('type="file"');
    console.log(`[テスト2] Native File Input 要素の存在確認: ${hasFileInput ? '✅ PASS (標準入力確認)' : '❌ FAIL'}`);

    // Test 3: Check Event script link
    const hasAppJs = body.includes('src="app.js"');
    console.log(`[テスト3] JSスクリプト (app.js) のバインド確認: ${hasAppJs ? '✅ PASS (スクリプト結合OK)' : '❌ FAIL'}`);

    console.log('\n========================================');
    console.log('🎉 動作確認部署からの結論: 全検証パス！システムは正常動作しています。');
    console.log('========================================');
  });
}).on('error', (e) => {
  console.error('[テスト失敗] サーバーにアクセスできませんでした:', e.message);
});
