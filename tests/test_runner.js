const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  console.log('🧪 動作確認部署: 実機・ブラウザ自動検証テストを開始します...');

  // Create dummy sample image for testing
  const dummyImgPath = path.join(__dirname, 'test_screenshot.png');
  // Simple 1x1 png pixel in base64
  const base64Png = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
  fs.writeFileSync(dummyImgPath, Buffer.from(base64Png, 'base64'));

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  try {
    console.log('📡 1. ローカルサーバー (http://localhost:8080) に接続中...');
    await page.goto('http://localhost:8080');

    // Test 1: Native File Picker Selection
    console.log('🧪 2. 【テスト1】ファイル選択ボタン (input type=file) のテスト...');
    const fileInput = await page.$('#fileInput');
    await fileInput.setInputFiles(dummyImgPath);
    await page.waitForTimeout(1000);
    const isPreviewVisible1 = await page.$eval('#previewContainer', el => !el.classList.contains('hidden'));
    console.log(`   └─ 結果: ${isPreviewVisible1 ? '✅ PASS (成功)' : '❌ FAIL (失敗)'}`);

    // Test 2: Mode Toggle Switching
    console.log('🧪 3. 【テスト2】「合計値」「左列」「右列」の切り替え連動テスト...');
    await page.click('#btnSelectLeft');
    const leftText = await page.textContent('#statsSummaryGrid');
    console.log(`   └─ 左列モード表示: ${leftText.includes('左列') ? '✅ PASS (連動成功)' : '❌ FAIL'}`);

    await page.click('#btnSelectRight');
    const rightText = await page.textContent('#statsSummaryGrid');
    console.log(`   └─ 右列モード表示: ${rightText.includes('右列') ? '✅ PASS (連動成功)' : '❌ FAIL'}`);

    await page.click('#btnSelectSum');
    const sumText = await page.textContent('#statsSummaryGrid');
    console.log(`   └─ 合計モード表示: ${sumText.includes('合計') ? '✅ PASS (連動成功)' : '❌ FAIL'}`);

    console.log('\n🎉 全自動ブラウザ検証が正常完了しました！');
  } catch (err) {
    console.error('❌ テストエラー発生:', err);
  } finally {
    await browser.close();
    if (fs.existsSync(dummyImgPath)) fs.unlinkSync(dummyImgPath);
  }
})();
