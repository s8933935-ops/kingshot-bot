$WshShell = New-Object -ComObject WScript.Shell
$desktopPaths = @(
    [Environment]::GetFolderPath('Desktop'),
    "$HOME\Desktop"
) | Select-Object -Unique

$targetBat = "c:\Users\s8933\.gemini\antigravity\scratch\multi-agent-designer\start_app.bat"
$workingDir = "c:\Users\s8933\.gemini\antigravity\scratch\multi-agent-designer"

foreach ($dp in $desktopPaths) {
    if (Test-Path $dp) {
        $shortcutPath = Join-Path $dp "仮想投資AIプラットフォーム.lnk"
        $shortcut = $WshShell.CreateShortcut($shortcutPath)
        $shortcut.TargetPath = $targetBat
        $shortcut.WorkingDirectory = $workingDir
        $shortcut.Description = "仮想投資＆AI予想プラットフォーム起動"
        $shortcut.IconLocation = "shell32.dll,220"
        $shortcut.Save()
        Write-Output "Created: $shortcutPath"
    }
}
