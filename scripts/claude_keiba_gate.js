#!/usr/bin/env node
/**
 * claude_keiba_gate.js
 * Claude個別プロジェクト「競馬予想シミュレーター基盤構築」直接接続＆自動監査ゲート
 *
 * セッションID: 533b4982-120f-4baa-b810-9c4dfe42570c
 * プロジェクトDir: C:\Users\s8933\projects\keiba-ai-simulator
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const SESSION_ID = '533b4982-120f-4baa-b810-9c4dfe42570c';
const PROJECT_DIR = 'C:\\Users\\s8933\\projects\\keiba-ai-simulator';

async function queryClaude(prompt) {
  return new Promise((resolve, reject) => {
    // Windowsのcmd実行セキュリティパッチに対応するため shell: true を指定し、引数を確実にクォート
    const child = spawn('claude.cmd', ['--resume', SESSION_ID, '-p', JSON.stringify(prompt)], {
      cwd: PROJECT_DIR,
      shell: true,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';

    child.stdout.on('data', (d) => { stdout += d.toString(); });
    child.stderr.on('data', (d) => { stderr += d.toString(); });

    child.on('close', (code) => {
      if (code === 0) {
        resolve(stdout.trim());
      } else {
        reject(new Error(`Claude process exited with code ${code}\nStderr: ${stderr}\nStdout: ${stdout}`));
      }
    });

    child.on('error', (err) => reject(err));
  });
}

async function main() {
  const prompt = process.argv.slice(2).join(' ');
  if (!prompt) {
    console.error('使用法: node claude_keiba_gate.js "<確認・監査プロンプト>"');
    process.exit(1);
  }

  console.log(`[claude_keiba_gate] 競馬予想シミュレーター基盤構築 セッション (${SESSION_ID}) へ問い合わせ中...`);
  try {
    const response = await queryClaude(prompt);
    console.log(`\n======================================================`);
    console.log(`🏛️ Claude（競馬予想シミュレーター基盤構築）からの監査回答`);
    console.log(`======================================================\n`);
    console.log(response);
    console.log(`\n======================================================`);
  } catch (e) {
    console.error(`[claude_keiba_gate] エラー発生:`, e.message);
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = { queryClaude, SESSION_ID, PROJECT_DIR };
