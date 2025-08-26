#!/usr/bin/env pwsh
<#
.SYNOPSIS
    AWS-Focused AI Assistant Deployment Script

.DESCRIPTION
    This script deploys the AI Assistant stack to AWS including:
    - Multi-Lambda architecture (Telegram Bot, Calendar Fetcher, AI Processor, etc.)
    - DynamoDB tables for users, calendar events, AI memory, and notifications
    - EventBridge rules for scheduling
    - Secrets Manager for API keys
    - API Gateway for webhook

.PARAMETER Environment
    Deployment environment (dev/prod). Defaults to 'dev'

.PARAMETER BotToken
    Telegram Bot Token (optional - can be set in .env file)

.EXAMPLE
    .\deploy-enhanced.ps1 -Environment dev
    .\deploy-enhanced.ps1 -Environment prod -BotToken "YOUR_BOT_TOKEN"
#>

param(
    [Parameter(Mandatory = $false)]
    [ValidateSet("dev", "prod")]
    [string]$Environment = "dev",
    
    [Parameter(Mandatory = $false)]
    [string]$BotToken
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

function Read-EnvironmentFile {
    Write-ColorOutput "Reading environment configuration..." "Info"
    
    $envFile = ".env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match "^([^#][^=]+)=(.*)$") {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                Set-Item -Path "env:$name" -Value $value
                Write-ColorOutput "  Loaded: $name" "Info"
            }
        }
        Write-ColorOutput "✓ Environment file loaded successfully" "Success"
    } else {
        Write-ColorOutput "  No .env file found, using command line parameters" "Warning"
    }
}

function Get-BotToken {
    # Priority: Command line parameter > Environment variable > .env file
    if ($BotToken) {
        return $BotToken
    }
    
    if ($env:BOT_TOKEN) {
        return $env:BOT_TOKEN
    }
    
    Write-ColorOutput "✗ Bot Token not found. Please provide it via -BotToken parameter or set BOT_TOKEN in .env file" "Error"
    Write-ColorOutput "  You can also check env.template for the required format" "Info"
    exit 1
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
    param(
        [string]$BotToken
    )
    
    Write-ColorOutput "Deploying AI Assistant stack to AWS..." "Info"
    
    try {
        # Deploy using SAM
        $deployArgs = @(
            "deploy",
            "--guided",
            "--parameter-overrides",
            "Environment=$Environment",
            "BotToken=$BotToken"
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
        
        $botToken = Get-BotToken
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
    
    Write-ColorOutput "`n1. Set up Google Calendar API credentials in AWS Secrets Manager:" "Info"
    Write-ColorOutput "   - Go to Google Cloud Console" "Info"
    Write-ColorOutput "   - Enable Calendar API" "Info"
    Write-ColorOutput "   - Create OAuth 2.0 credentials" "Info"
    Write-ColorOutput "   - Update the secret in AWS Secrets Manager" "Info"
    
    Write-ColorOutput "`n2. Set up OpenAI API key in AWS Secrets Manager:" "Info"
    Write-ColorOutput "   - Get API key from OpenAI" "Info"
    Write-ColorOutput "   - Update the secret in AWS Secrets Manager" "Info"
    
    Write-ColorOutput "`n3. Test the system:" "Info"
    Write-ColorOutput "   - Send a message to your Telegram bot" "Info"
    Write-ColorOutput "   - Check CloudWatch logs for any errors" "Info"
    
    Write-ColorOutput "`n4. Monitor scheduled functions in AWS:" "Info"
    Write-ColorOutput "   - Calendar sync runs every hour via EventBridge" "Info"
    Write-ColorOutput "   - AI processing runs at 8 AM daily via EventBridge" "Info"
    Write-ColorOutput "   - Regular checks run every 30 minutes via EventBridge" "Info"
    
    Write-ColorOutput "`n5. AWS Resources created:" "Info"
    Write-ColorOutput "   - Lambda Functions: 5 functions for different purposes" "Info"
    Write-ColorOutput "   - DynamoDB Tables: 4 tables for data storage" "Info"
    Write-ColorOutput "   - EventBridge Rules: 3 rules for scheduling" "Info"
    Write-ColorOutput "   - Secrets Manager: 3 secrets for API keys" "Info"
    Write-ColorOutput "   - API Gateway: Webhook endpoint for Telegram" "Info"
    
    Write-ColorOutput "`n📚 Documentation: Check the PROJECT_STRUCTURE.md file for detailed information" "Info"
}

# Main execution
try {
    Write-ColorOutput "🚀 AWS AI Assistant Deployment Script" "Success"
    Write-ColorOutput "Environment: $Environment" "Info"
    Write-ColorOutput "Mode: AWS Cloud Deployment Only" "Info"
    Write-ColorOutput "Dependencies: Automatic via SAM Container Build" "Info"
    Write-ColorOutput "===============================================" "Info"
    
    # Check prerequisites
    Test-Prerequisites
    
    # Read environment configuration
    Read-EnvironmentFile
    
    # Get bot token
    $botToken = Get-BotToken
    
    # Build project
    Build-Project
    
    # Deploy stack
    Deploy-Stack -BotToken $botToken
    
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
