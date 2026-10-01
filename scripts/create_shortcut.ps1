$WshShell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$targetBat = "c:\Users\s8933\.gemini\antigravity\scratch\multi-agent-designer\Satisfactory_Bot_起動.bat"
$shortcutPath = Join-Path $desktop "Satisfactory Bot 起動.lnk"

$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetBat
$shortcut.WorkingDirectory = "c:\Users\s8933\.gemini\antigravity\scratch\multi-agent-designer"
$shortcut.Description = "Satisfactory v1.0 攻略案内 Discord Bot 起動"
$shortcut.Save()

Write-Host "✅ デスクトップにショートカットを作成しました: $shortcutPath"
