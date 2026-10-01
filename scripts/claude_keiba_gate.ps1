param(
    [Parameter(Mandatory=$true)]
    [string]$Prompt
)

$SESSION_ID = "533b4982-120f-4baa-b810-9c4dfe42570c"
$PROJECT_DIR = "C:\Users\s8933\projects\keiba-ai-simulator"

Write-Host "[claude_keiba_gate] 競馬予想シミュレーター基盤構築 ($SESSION_ID) へ問い合わせ中..." -ForegroundColor Cyan

$tempFile = [System.IO.Path]::GetTempFileName()
try {
    # UTF-8でプロンプトを一時保存
    [System.IO.File]::WriteAllText($tempFile, $Prompt, [System.Text.Encoding]::UTF8)
    
    # claude コマンドを実行
    $output = & claude --resume $SESSION_ID -p (Get-Content -Raw $tempFile) 2>&1
    
    Write-Host "`n======================================================" -ForegroundColor Green
    Write-Host "🏛️ Claude（競馬予想シミュレーター基盤構築）からの監査回答" -ForegroundColor Green
    Write-Host "======================================================`n" -ForegroundColor Green
    Write-Host $output
    Write-Host "`n======================================================" -ForegroundColor Green
} finally {
    if (Test-Path $tempFile) {
        Remove-Item $tempFile -Force
    }
}
