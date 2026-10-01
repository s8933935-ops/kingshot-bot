Set WshShell = CreateObject("WScript.Shell")
strDesktop = WshShell.SpecialFolders("Desktop")
strTarget = "C:\Users\s8933\.gemini\antigravity\scratch\multi-agent-designer\Satisfactory_Bot_起動.bat"
strWorking = "C:\Users\s8933\.gemini\antigravity\scratch\multi-agent-designer"

Set oShortcut = WshShell.CreateShortcut(strDesktop & "\Satisfactory_Bot.lnk")
oShortcut.TargetPath = strTarget
oShortcut.WorkingDirectory = strWorking
oShortcut.Description = "Satisfactory v1.0 攻略案内 Discord Bot"
oShortcut.IconLocation = "shell32.dll,14"
oShortcut.Save

WScript.Echo "SUCCESS: " & strDesktop & "\Satisfactory_Bot.lnk"
