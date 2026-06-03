$WshShell = New-Object -ComObject WScript.Shell
$BatchFile = Join-Path $PSScriptRoot "start-dashboard.bat"

# Desktop shortcut
$DesktopPath = [System.Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "Stundenerfassung.lnk"))
$Shortcut.TargetPath = $BatchFile
$Shortcut.WorkingDirectory = $PSScriptRoot
$Shortcut.Description = "Stundenerfassung"
$Shortcut.IconLocation = "shell32.dll,144"
$Shortcut.WindowStyle = 7
$Shortcut.Save()

# Startup shortcut
$StartupPath = [System.Environment]::GetFolderPath("Startup")
$StartupLink = $WshShell.CreateShortcut((Join-Path $StartupPath "Stundenerfassung.lnk"))
$StartupLink.TargetPath = $BatchFile
$StartupLink.WorkingDirectory = $PSScriptRoot
$StartupLink.Description = "Stundenerfassung"
$StartupLink.IconLocation = "shell32.dll,144"
$StartupLink.WindowStyle = 7
$StartupLink.Save()

Write-Host "Desktop + Startup shortcuts created for Stundenerfassung"
