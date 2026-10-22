[CmdletBinding()]
param(
    [string]$TaskName = "GmailOrganizer",
    [string]$Time = "08:00",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$wrapper = Join-Path $scriptDir "run_organizer.bat"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$token = Join-Path $repoRoot ".secrets\token.json"

if (-not (Test-Path $wrapper)) {
    throw "Wrapper not found: $wrapper"
}
if (-not (Test-Path $python)) {
    throw "Virtualenv interpreter not found: $python. Create .venv first."
}
if (-not (Test-Path $token)) {
    throw "Gmail token not found: $token. Run gmail-organizer auth first."
}

$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$wrapper`"" `
    -WorkingDirectory $repoRoot

$trigger = New-ScheduledTaskTrigger -Daily -At $Time

$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

$description = "Run Gmail Organizer daily and apply Auto/* labels."

if ($DryRun) {
    [pscustomobject]@{
        TaskName = $TaskName
        Execute = $action.Execute
        Arguments = $action.Arguments
        WorkingDirectory = $action.WorkingDirectory
        DailyAt = $Time
        MultipleInstances = $settings.MultipleInstances
        StartWhenAvailable = $settings.StartWhenAvailable
        ExecutionTimeLimitMinutes = 30
        RunAs = $principal.UserId
        LogonType = $principal.LogonType
    } | Format-List
    return
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description $description `
    -Force | Out-Null

Write-Host "Registered '$TaskName' to run daily at $Time."
Write-Host "Run it now:    Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Check result:  Get-ScheduledTaskInfo -TaskName '$TaskName'"
Write-Host "Task output:   $repoRoot\logs\task.log"
Write-Host "Remove it:     Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
