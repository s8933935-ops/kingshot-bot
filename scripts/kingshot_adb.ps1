param (
    [Parameter(Mandatory=$true)]
    [string]$Action,
    [int]$X = 0,
    [int]$Y = 0,
    [int]$X2 = 0,
    [int]$Y2 = 0,
    [int]$Duration = 300,
    [string]$OutFile = "docs/guides/images/current_screen.png",
    [string]$Label = ""
)

$adb = "C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
$device = "127.0.0.1:5565"

function Ensure-Connected {
    & $adb connect $device | Out-Null
    Start-Sleep -Milliseconds 500
}

switch ($Action) {
    "capture" {
        Ensure-Connected
        $remotePath = "/sdcard/kingshot_cap.png"
        & $adb -s $device shell screencap -p $remotePath | Out-Null
        $parentDir = Split-Path -Parent $OutFile
        if ($parentDir -and -not (Test-Path $parentDir)) { New-Item -ItemType Directory -Path $parentDir -Force | Out-Null }
        & $adb -s $device pull $remotePath $OutFile | Out-Null
        Write-Output "CAPTURED:$OutFile"
    }
    "tap" {
        Ensure-Connected
        & $adb -s $device shell input tap $X $Y | Out-Null
        Write-Output "TAPPED:$X,$Y Label:$Label"
    }
    "swipe" {
        Ensure-Connected
        & $adb -s $device shell input swipe $X $Y $X2 $Y2 $Duration | Out-Null
        Write-Output "SWIPED:$X,$Y to $X2,$Y2 Duration:$Duration"
    }
    "back" {
        Ensure-Connected
        & $adb -s $device shell input keyevent 4 | Out-Null
        Write-Output "KEYEVENT:BACK"
    }
}
