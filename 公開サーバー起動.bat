@echo off
chcp 65001 > nul
title クオンツ投資シミュレーター Web公開サーバー
echo ======================================================
echo  クオンツ投資シミュレーター Web公開サーバーを起動中...
echo ======================================================
cd /d "%~dp0"
python scripts\run_public_server.py
pause
