#!/usr/bin/env pwsh

$ErrorActionPreference = "Stop"

function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    $Colors = @{
        Info = "Cyan"
        Success = "Green"
        Warning = "Yellow"
        Error = "Red"
    }
    Write-Host $Message -ForegroundColor $Colors[$Color]
}

function Test-Prerequisites {
    Write-ColorOutput "Checking prerequisites..." "Info"
    
    try {
        $awsVersion = aws --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "OK AWS CLI: $awsVersion" "Success"
        } else {
            throw "AWS CLI not found"
        }
    } catch {
        Write-ColorOutput "ERROR AWS CLI not found" "Error"
        exit 1
    }
    
    try {
        $samVersion = sam --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "OK SAM CLI: $samVersion" "Success"
        } else {
            throw "SAM CLI not found"
        }
    } catch {
        Write-ColorOutput "ERROR SAM CLI not found" "Error"
        exit 1
    }
    
    # Docker is optional - we'll use local builds if not available
    try {
        $dockerVersion = docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "OK Docker: $dockerVersion (Container builds enabled)" "Success"
            $script:DockerAvailable = $true
        } else {
            throw "Docker not found"
        }
    } catch {
        Write-ColorOutput "WARNING Docker not found - will use local builds" "Warning"
        Write-ColorOutput "  Note: Local builds may cause deployment issues" "Warning"
        $script:DockerAvailable = $false
    }
}

function Test-ExistingSecrets {
    Write-ColorOutput "Checking AWS Secrets..." "Info"
    
    $requiredSecrets = @("telegram-bot-token-dev", "google-calendar-credentials-dev")
    
    foreach ($secretName in $requiredSecrets) {
        try {
            $secret = aws secretsmanager describe-secret --secret-id $secretName 2>$null
            if ($LASTEXITCODE -eq 0) {
                Write-ColorOutput "OK Secret: $secretName" "Success"
            } else {
                Write-ColorOutput "ERROR Secret missing: $secretName" "Error"
                return $false
            }
        } catch {
            Write-ColorOutput "ERROR Secret missing: $secretName" "Error"
            return $false
        }
    }
    
    Write-ColorOutput "OK All secrets available" "Success"
    return $true
}

function Build-Project {
    Write-ColorOutput "Building SAM project..." "Info"
    
    try {
        if ($script:DockerAvailable) {
            Write-ColorOutput "  Using Docker container build (recommended)" "Info"
            sam build --use-container
        } else {
            Write-ColorOutput "  Using local build (Docker not available)" "Warning"
            Write-ColorOutput "  This may cause deployment issues" "Warning"
            sam build
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw "SAM build failed"
        }
        Write-ColorOutput "OK Build successful" "Success"
    } catch {
        Write-ColorOutput "ERROR Build failed: $_" "Error"
        exit 1
    }
}

function Deploy-Stack {
    Write-ColorOutput "Deploying to AWS..." "Info"
    
    try {
        $deployArgs = @("deploy", "--guided")
        sam @deployArgs
        
        if ($LASTEXITCODE -ne 0) {
            throw "Deployment failed"
        }
        Write-ColorOutput "OK Deployment successful" "Success"
    } catch {
        Write-ColorOutput "ERROR Deployment failed: $_" "Error"
        exit 1
    }
}

function Test-Deployment {
    Write-ColorOutput "Verifying deployment..." "Info"
    
    try {
        $stackName = "aihelper"
        $stackStatus = aws cloudformation describe-stacks --stack-name $stackName --query "Stacks[0].StackStatus" --output text 2>$null
        
        if ($stackStatus -eq "CREATE_COMPLETE" -or $stackStatus -eq "UPDATE_COMPLETE") {
            Write-ColorOutput "OK Stack: $stackStatus" "Success"
        } else {
            Write-ColorOutput "WARNING Stack: $stackStatus" "Warning"
        }
    } catch {
        Write-ColorOutput "WARNING Could not verify deployment" "Warning"
    }
}

function Set-Webhook {
    Write-ColorOutput "Setting Telegram webhook..." "Info"
    
    try {
        $stackName = "aihelper"
        $apiUrl = aws cloudformation describe-stacks --stack-name $stackName --query "Stacks[0].Outputs[?OutputKey=='TelegramBotApiUrl'].OutputValue" --output text 2>$null
        
        if (-not $apiUrl) {
            Write-ColorOutput "WARNING Could not get API URL" "Warning"
            return
        }
        
        $botToken = aws secretsmanager get-secret-value --secret-id "telegram-bot-token-dev" --query "SecretString" --output text 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "ERROR Could not get bot token" "Error"
            return
        }
        
        $webhookUrl = "$apiUrl"
        Write-ColorOutput "Setting webhook to: $webhookUrl" "Info"
        
        $response = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" -Method POST -Body (@{url = $webhookUrl} | ConvertTo-Json) -ContentType "application/json"
        
        if ($response.ok) {
            Write-ColorOutput "OK Webhook set successfully" "Success"
        } else {
            Write-ColorOutput "ERROR Webhook failed: $($response.description)" "Error"
        }
    } catch {
        Write-ColorOutput "ERROR Webhook failed: $_" "Error"
    }
}

function Show-NextSteps {
    Write-ColorOutput "Deployment Complete!" "Success"
    Write-ColorOutput "Next steps:" "Info"
    Write-ColorOutput "1. Test Telegram bot" "Info"
    Write-ColorOutput "2. Check CloudWatch logs" "Info"
    Write-ColorOutput "3. Monitor calendar sync" "Info"
    Write-ColorOutput "4. Verify DynamoDB tables" "Info"
    
    if (-not $script:DockerAvailable) {
        Write-ColorOutput "" "Warning"
        Write-ColorOutput "IMPORTANT: Docker was not available during build" "Warning"
        Write-ColorOutput "If you encounter Lambda runtime errors:" "Warning"
        Write-ColorOutput "1. Install Docker Desktop" "Warning"
        Write-ColorOutput "2. Rebuild with: sam build --use-container" "Warning"
        Write-ColorOutput "3. Redeploy with: sam deploy" "Warning"
    }
}

try {
    Write-ColorOutput "AWS AI Assistant Deployment" "Success"
    Write-ColorOutput "================================" "Info"
    
    Test-Prerequisites
    
    if (-not (Test-ExistingSecrets)) {
        Write-ColorOutput "ERROR Required secrets missing" "Error"
        exit 1
    }
    
    Build-Project
    Deploy-Stack
    Test-Deployment
    Set-Webhook
    Show-NextSteps
    
} catch {
    Write-ColorOutput "ERROR Deployment failed: $_" "Error"
    exit 1
}
