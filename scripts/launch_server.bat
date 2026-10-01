@echo off
chcp 65001 > nul
echo ===================================================
echo 🚀 仮想投資AIプラットフォーム (AI Investment Platform)
echo ===================================================
echo サーバーを起動しています...
cd /d "C:\Users\s8933\.gemini\antigravity\scratch\multi-agent-designer"
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
pause
