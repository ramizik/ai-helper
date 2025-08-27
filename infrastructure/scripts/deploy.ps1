#!/usr/bin/env pwsh
<#
.SYNOPSIS
    AWS-Focused AI Assistant Deployment Script

.DESCRIPTION
    This script deploys the AI Assistant stack to AWS including:
    - Working Telegram Bot with webhook handling
    - Working Calendar Fetcher with Google Calendar integration
    - DynamoDB tables for users and calendar events
    - EventBridge rule for hourly calendar sync
    - Uses existing AWS Secrets Manager secrets
    - API Gateway for webhook

.PARAMETER Environment
    Deployment environment (dev/prod). Defaults to 'dev'

.EXAMPLE
    .\deploy.ps1 -Environment dev
    .\deploy.ps1 -Environment prod
#>

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev"
)

# Set error action preference
$ErrorActionPreference = "Stop"

# Colors for output
$Colors = @{
    Info = "Cyan"
    Success = "Green"
    Warning = "Yellow"
    Error = "Red"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Colors[$Color]
}

function Test-Prerequisites {
    Write-ColorOutput "Checking AWS deployment prerequisites..." "Info"
    
    # Check if AWS CLI is installed
    try {
        $awsVersion = aws --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ AWS CLI found: $awsVersion" "Success"
        } else {
            throw "AWS CLI not found"
        }
    } catch {
        Write-ColorOutput "✗ AWS CLI not found. Please install AWS CLI first." "Error"
        exit 1
    }
    
    # Check if SAM CLI is installed
    try {
        $samVersion = sam --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ SAM CLI found: $samVersion" "Success"
        } else {
            throw "SAM CLI not found"
        }
    } catch {
        Write-ColorOutput "✗ SAM CLI not found. Please install AWS SAM CLI first." "Error"
        exit 1
    }
    
    # Check if Docker is available (for container builds)
    try {
        $dockerVersion = docker --version 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✓ Docker found: $dockerVersion" "Success"
            Write-ColorOutput "  → SAM container builds will work automatically" "Info"
        } else {
            throw "Docker not found"
        }
    } catch {
        Write-ColorOutput "✗ Docker not found. Container builds won't work." "Error"
        Write-ColorOutput "  → Please install Docker for reliable dependency management" "Error"
        exit 1
    }
}

function Test-ExistingSecrets {
    Write-ColorOutput "Checking existing AWS Secrets Manager secrets..." "Info"
    
    try {
        # Check if required secrets exist
        $requiredSecrets = @(
            "telegram-bot-token-dev",
            "google-calendar-credentials-dev"
        )
        
        foreach ($secretName in $requiredSecrets) {
            try {
                $secret = aws secretsmanager describe-secret --secret-id $secretName 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-ColorOutput "  ✓ Secret found: $secretName" "Success"
                } else {
                    Write-ColorOutput "  ❌ Secret missing: $secretName" "Error"
                    Write-ColorOutput "    → Create it manually: aws secretsmanager create-secret --name '$secretName' --secret-string '{\"key\":\"value\"}'" "Warning"
                    return $false
                }
            } catch {
                Write-ColorOutput "  ❌ Secret missing: $secretName" "Error"
                return $false
            }
        }
        
        Write-ColorOutput "✓ All required secrets are available" "Success"
        return $true
        
    } catch {
        Write-ColorOutput "✗ Failed to check secrets: $_" "Error"
        return $false
    }
}

function Build-Project {
    Write-ColorOutput "Building SAM project with container support..." "Info"
    
    try {
        # Build the project with container support for automatic dependency management
        Write-ColorOutput "  Running: sam build --use-container" "Info"
        sam build --use-container
        
        if ($LASTEXITCODE -ne 0) {
            throw "SAM build failed"
        }
        Write-ColorOutput "✓ SAM build completed successfully" "Success"
        Write-ColorOutput "  → All Lambda dependencies automatically installed" "Info"
    } catch {
        Write-ColorOutput "✗ SAM build failed: $_" "Error"
        exit 1
    }
}

function Deploy-Stack {
    Write-ColorOutput "Deploying AI Assistant stack to AWS..." "Info"
    
    try {
        # Deploy using SAM
        $deployArgs = @(
            "deploy",
            "--guided",
            "--parameter-overrides",
            "Environment=$Environment"
        )
        
        Write-ColorOutput "Running: sam $($deployArgs -join ' ')" "Info"
        sam @deployArgs
        
        if ($LASTEXITCODE -ne 0) {
            throw "SAM deployment failed"
        }
        
        Write-ColorOutput "✓ AI Assistant deployed successfully to AWS!" "Success"
        
    } catch {
        Write-ColorOutput "✗ Deployment failed: $_" "Error"
        exit 1
    }
}

function Test-Deployment {
    Write-ColorOutput "Verifying AWS deployment..." "Info"
    
    try {
        $stackName = "aihelper-$Environment"
        
        # Check if stack exists
        $stackStatus = aws cloudformation describe-stacks --stack-name $stackName --query 'Stacks[0].StackStatus' --output text 2>$null
        
        if ($stackStatus -eq "CREATE_COMPLETE" -or $stackStatus -eq "UPDATE_COMPLETE") {
            Write-ColorOutput "✓ CloudFormation stack deployed successfully: $stackStatus" "Success"
            
            # Check Lambda functions
            $lambdaFunctions = aws lambda list-functions --query "Functions[?contains(FunctionName, 'aihelper-$Environment')].FunctionName" --output text 2>$null
            if ($lambdaFunctions) {
                $functionCount = ($lambdaFunctions -split "`t").Count
                Write-ColorOutput "✓ $functionCount Lambda functions deployed to AWS" "Success"
            }
            
            # Check DynamoDB tables
            $dynamoTables = aws dynamodb list-tables --query "TableNames[?contains(@, 'aihelper-$Environment')]" --output text 2>$null
            if ($dynamoTables) {
                $tableCount = ($dynamoTables -split "`t").Count
                Write-ColorOutput "✓ $tableCount DynamoDB tables created in AWS" "Success"
            }
            
        } else {
            Write-ColorOutput "⚠️  Stack status: $stackStatus" "Warning"
        }
        
    } catch {
        Write-ColorOutput "⚠️  Could not verify deployment status" "Warning"
    }
}

function Set-Webhook {
    Write-ColorOutput "Setting Telegram webhook to AWS API Gateway..." "Info"
    
    try {
        # Get the API Gateway URL from CloudFormation outputs
        $stackName = "aihelper-$Environment"
        $apiUrl = aws cloudformation describe-stacks --stack-name $stackName --query "Stacks[0].Outputs[?OutputKey=='TelegramBotApiUrl'].OutputValue" --output text 2>$null
        
        if (-not $apiUrl) {
            Write-ColorOutput "  Warning: Could not retrieve API Gateway URL. Please set webhook manually." "Warning"
            return
        }
        
        # Get bot token from existing secret
        $botTokenSecret = aws secretsmanager get-secret-value --secret-id "telegram-bot-token-dev" --query 'SecretString' --output text 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-ColorOutput "  ❌ Could not retrieve bot token from secret" "Error"
            return
        }
        
        $botTokenData = $botTokenSecret | ConvertFrom-Json
        $botToken = $botTokenData.bot_token
        
        $webhookUrl = "$apiUrl"
        
        Write-ColorOutput "  Setting webhook to AWS API Gateway: $webhookUrl" "Info"
        
        # Set the webhook
        $response = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/setWebhook" -Method POST -Body @{url = $webhookUrl} -ContentType "application/json"
        
        if ($response.ok) {
            Write-ColorOutput "✓ Webhook set successfully to AWS" "Success"
        } else {
            Write-ColorOutput "✗ Failed to set webhook: $($response.description)" "Error"
        }
        
    } catch {
        Write-ColorOutput "✗ Failed to set webhook: $_" "Error"
    }
}

function Show-NextSteps {
    Write-ColorOutput "`n🎉 AWS Deployment Complete! Next Steps:" "Success"
    
    Write-ColorOutput "`n1. Verify your existing AWS Secrets Manager secrets:" "Info"
    Write-ColorOutput "   - telegram-bot-token-dev (should contain your bot token)" "Info"
    Write-ColorOutput "   - google-calendar-credentials-dev (should contain Google OAuth credentials)" "Info"
    
    Write-ColorOutput "`n2. Test the system:" "Info"
    Write-ColorOutput "   - Send a message to your Telegram bot" "Info"
    Write-ColorOutput "   - Check CloudWatch logs for any errors" "Info"
    
    Write-ColorOutput "`n3. Monitor calendar integration:" "Info"
    Write-ColorOutput "   - Calendar sync runs every hour via EventBridge" "Info"
    Write-ColorOutput "   - Check CloudWatch logs for calendar fetcher function" "Info"
    Write-ColorOutput "   - Verify events are stored in DynamoDB" "Info"
    
    Write-ColorOutput "`n4. AWS Resources created:" "Info"
    Write-ColorOutput "   - Lambda Functions: 2 functions (Telegram Bot + Calendar Fetcher)" "Info"
    Write-ColorOutput "   - DynamoDB Tables: 2 tables (Users + Calendar Events)" "Info"
    Write-ColorOutput "   - EventBridge Rule: 1 rule for hourly calendar sync" "Info"
    Write-ColorOutput "   - API Gateway: Webhook endpoint for Telegram" "Info"
    
    Write-ColorOutput "`n📚 Documentation: Check the PROJECT_STRUCTURE.md file for detailed information" "Info"
}

# Main execution
try {
    Write-ColorOutput "🚀 AWS AI Assistant Deployment Script" "Success"
    Write-ColorOutput "Environment: $Environment" "Info"
    Write-ColorOutput "Mode: AWS Cloud Deployment Only" "Info"
    Write-ColorOutput "Dependencies: Automatic via SAM Container Build" "Info"
    Write-ColorOutput "Functions: Telegram Bot + Calendar Fetcher (Working Only)" "Info"
    Write-ColorOutput "Secrets: Using existing AWS Secrets Manager secrets" "Info"
    Write-ColorOutput "===============================================" "Info"
    
    # Check prerequisites
    Test-Prerequisites
    
    # Check existing secrets
    if (-not (Test-ExistingSecrets)) {
        Write-ColorOutput "❌ Required secrets are missing. Please create them first." "Error"
        exit 1
    }
    
    # Build project
    Build-Project
    
    # Deploy stack
    Deploy-Stack
    
    # Test deployment
    Test-Deployment
    
    # Set webhook
    Set-Webhook
    
    # Show next steps
    Show-NextSteps
    
} catch {
    Write-ColorOutput "✗ AWS deployment script failed: $_" "Error"
    exit 1
}
