# Scheduler Toggle Script - Like a Light Switch!
# Usage: .\toggle-scheduler.ps1 [on|off|status]

param(
    [string]$Action = "status"
)

$RuleName = "aihelper-scheduler-dev"
$Region = "us-west-2"

function Get-SchedulerStatus {
    try {
        $status = aws events describe-rule --name $RuleName --region $Region --query "State" --output text 2>$null
        return $status
    }
    catch {
        return "ERROR"
    }
}

function Set-SchedulerStatus {
    param([string]$State)
    
    try {
        if ($State -eq "ENABLED") {
            aws events enable-rule --name $RuleName --region $Region
            Write-Host "✅ Scheduler ENABLED - Messages will be sent every minute!" -ForegroundColor Green
        } else {
            aws events disable-rule --name $RuleName --region $Region
            Write-Host "⏸️ Scheduler DISABLED - No more messages will be sent!" -ForegroundColor Yellow
        }
    }
    catch {
        Write-Host "❌ Failed to change scheduler status: $_" -ForegroundColor Red
    }
}

# Main logic
Write-Host "🔌 AI Helper Scheduler Toggle" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""

$currentStatus = Get-SchedulerStatus

if ($Action -eq "status") {
    Write-Host "📊 Current Status:" -ForegroundColor Yellow
    if ($currentStatus -eq "ENABLED") {
        Write-Host "🟢 Scheduler is ENABLED (running every minute)" -ForegroundColor Green
        Write-Host "   Use: .\toggle-scheduler.ps1 off" -ForegroundColor Gray
    } elseif ($currentStatus -eq "DISABLED") {
        Write-Host "🔴 Scheduler is DISABLED (paused)" -ForegroundColor Red
        Write-Host "   Use: .\toggle-scheduler.ps1 on" -ForegroundColor Gray
    } else {
        Write-Host "❓ Status unknown: $currentStatus" -ForegroundColor Red
    }
}
elseif ($Action -eq "on" -or $Action -eq "enable") {
    if ($currentStatus -eq "ENABLED") {
        Write-Host "ℹ️ Scheduler is already ENABLED" -ForegroundColor Blue
    } else {
        Write-Host "🔄 Enabling scheduler..." -ForegroundColor Yellow
        Set-SchedulerStatus "ENABLED"
    }
}
elseif ($Action -eq "off" -or $Action -eq "disable") {
    if ($currentStatus -eq "DISABLED") {
        Write-Host "ℹ️ Scheduler is already DISABLED" -ForegroundColor Blue
    } else {
        Write-Host "🔄 Disabling scheduler..." -ForegroundColor Yellow
        Set-SchedulerStatus "DISABLED"
    }
}
else {
    Write-Host "❓ Invalid action. Use: on, off, or status" -ForegroundColor Red
    Write-Host "Examples:" -ForegroundColor Gray
    Write-Host "  .\toggle-scheduler.ps1 on     # Enable scheduler" -ForegroundColor Gray
    Write-Host "  .\toggle-scheduler.ps1 off    # Disable scheduler" -ForegroundColor Gray
    Write-Host "  .\toggle-scheduler.ps1 status # Check current status" -ForegroundColor Gray
}

Write-Host ""
Write-Host "💡 Tip: You can also use AWS CLI directly:" -ForegroundColor Cyan
Write-Host "   Enable:  aws events enable-rule --name $RuleName --region $Region" -ForegroundColor Gray
Write-Host "   Disable: aws events disable-rule --name $RuleName --region $Region" -ForegroundColor Gray
