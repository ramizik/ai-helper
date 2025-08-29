# Simple Lambda Logs Monitor
# Shows real-time logs from all Lambda functions

Write-Host "Simple Lambda Logs Monitor" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
Write-Host ""

# Function names
$functions = @(
    "aihelper-scheduler-dev",
    "aihelper-telegram-bot-dev", 
    "aihelper-calendar-fetcher-dev"
)

Write-Host "To monitor logs in real-time, run these commands in separate terminals:" -ForegroundColor Yellow
Write-Host ""

foreach ($func in $functions) {
    $logGroup = "/aws/lambda/$func"
    Write-Host "aws logs tail `"$logGroup`" --follow --region us-west-2" -ForegroundColor White
    Write-Host ""
}

Write-Host "Press any key to start simple polling, or Ctrl+C to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Write-Host ""
Write-Host "Starting simple log monitoring (checking every 30 seconds)..." -ForegroundColor Green
Write-Host "Press Ctrl+C to stop" -ForegroundColor Red
Write-Host ""

# Simple polling approach - no complex JSON parsing
try {
    while ($true) {
        $currentTime = Get-Date -Format "HH:mm:ss"
        Write-Host "[$currentTime] Checking logs..." -ForegroundColor DarkGray
        
        foreach ($func in $functions) {
            $logGroup = "/aws/lambda/$func"
            
            try {
                # Get latest log stream name
                $streamOutput = aws logs describe-log-streams `
                    --log-group-name $logGroup `
                    --order-by LastEventTime `
                    --descending `
                    --max-items 1 `
                    --region us-west-2 2>$null
                
                if ($streamOutput) {
                    # Extract stream name from output (simple text parsing)
                    $lines = $streamOutput -split "`n"
                    $streamName = $null
                    
                    foreach ($line in $lines) {
                        if ($line -match "logStreamName") {
                            $streamName = ($line -split "`t")[-1]
                            break
                        }
                    }
                    
                    if ($streamName) {
                        # Get recent events (last 5)
                        $eventsOutput = aws logs get-log-events `
                            --log-group-name $logGroup `
                            --log-stream-name $streamName `
                            --region us-west-2 `
                            --start-from-head `
                            --limit 5 2>$null
                        
                        if ($eventsOutput) {
                            $lines = $eventsOutput -split "`n"
                            $foundMessages = $false
                            
                            foreach ($line in $lines) {
                                if ($line -match "message") {
                                    $foundMessages = $true
                                    $message = ($line -split "`t")[-1]
                                    
                                    # Color code by function
                                    $color = switch ($func) {
                                        "aihelper-scheduler-dev" { "Magenta" }
                                        "aihelper-telegram-bot-dev" { "Cyan" }
                                        "aihelper-calendar-fetcher-dev" { "Yellow" }
                                        default { "White" }
                                    }
                                    
                                    Write-Host "[$func] $message" -ForegroundColor $color
                                }
                            }
                            
                            if (-not $foundMessages) {
                                Write-Host "[$func] No recent messages" -ForegroundColor DarkGray
                            }
                        }
                    } else {
                        Write-Host "[$func] No log streams found" -ForegroundColor DarkGray
                    }
                }
            }
            catch {
                Write-Host "[$func] Error: $_" -ForegroundColor Red
            }
        }
        
        Write-Host "---" -ForegroundColor DarkGray
        Start-Sleep -Seconds 30
    }
}
catch {
    Write-Host "Monitoring stopped: $_" -ForegroundColor Red
}
