import os
import subprocess

def create_desktop_shortcuts():
    target_bat = os.path.abspath("公開サーバー起動.bat")
    workdir = os.path.abspath(".")
    shortcut_name = "【切れた時用】Web公開サーバー再開.lnk"

    # PowerShell script to create Windows shortcut safely with UTF-8
    ps_content = f"""
$target = '{target_bat}'
$workdir = '{workdir}'
$wsh = New-Object -ComObject WScript.Shell

$desktops = @(
    [Environment]::GetFolderPath('Desktop'),
    'C:\\Users\\s8933\\Desktop'
) | Select-Object -Unique

foreach ($d in $desktops) {{
    if (Test-Path $d) {{
        $lnkPath = Join-Path $d '{shortcut_name}'
        $s = $wsh.CreateShortcut($lnkPath)
        $s.TargetPath = $target
        $s.WorkingDirectory = $workdir
        $s.Description = '切断時にダブルクリックでクオンツWebサーバーを即座に再起動します'
        $s.IconLocation = 'shell32.dll,14'
        $s.Save()
        Write-Host "Created: $lnkPath"
    }}
}}
"""
    ps_file = os.path.abspath("scratch/create_shortcut.ps1")
    with open(ps_file, "w", encoding="utf-8-sig") as f:
        f.write(ps_content)

    res = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_file],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    print("STDOUT:", res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)

if __name__ == "__main__":
    create_desktop_shortcuts()
