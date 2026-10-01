const { execSync } = require('child_process');
const path = require('path');

const targetBat = path.resolve(__dirname, '../Satisfactory_Bot_起動.bat');
const script = `
$WshShell = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath('Desktop')
$targetBat = '${targetBat.replace(/\\/g, '\\\\')}'
$shortcutPath = Join-Path $desktop 'Satisfactory_Bot.lnk'
$shortcut = $WshShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetBat
$shortcut.WorkingDirectory = '${path.dirname(targetBat).replace(/\\/g, '\\\\')}'
$shortcut.IconLocation = 'shell32.dll,14'
$shortcut.Save()
Write-Output $shortcutPath
`;

const res = execSync(`powershell -NoProfile -Command "${script.replace(/\r?\n/g, ' ')}"`, { encoding: 'utf8' });
console.log('Shortcut created successfully at:', res.trim());
