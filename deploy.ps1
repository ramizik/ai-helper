# AI Assistant Deployment Script
# This script automates the deployment of your AI assistant to AWS
# Bot token is automatically read from .env file

param(
    [Parameter(Mandatory=$false)]
    [string]$StackName = "aihelper-dev",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1"
)

# Read BOT_TOKEN from .env file
Write-Host "Reading BOT_TOKEN from .env file..." -ForegroundColor Blue

if (-not (Test-Path ".env")) {
    Write-Host "   ERROR: .env file not found!" -ForegroundColor Red
    Write-Host "   Create a .env file with: BOT_TOKEN=your_token_here" -ForegroundColor Yellow
    Write-Host "   Make sure .env file is in the same directory as this script" -ForegroundColor Yellow
    exit 1
}

$BotToken = ""
try {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^BOT_TOKEN=(.+)$") {
            $BotToken = $matches[1].Trim('"').Trim("'").Trim()
        }
    }
} catch {
    Write-Host "   ERROR: Failed to read .env file!" -ForegroundColor Red
    Write-Host "   Check that .env file is readable and properly formatted" -ForegroundColor Yellow
    exit 1
}

if (-not $BotToken -or $BotToken -eq "") {
    Write-Host "   ERROR: BOT_TOKEN not found in .env file!" -ForegroundColor Red
    Write-Host "   Add this line to your .env file: BOT_TOKEN=your_actual_telegram_token" -ForegroundColor Yellow
    Write-Host "   Example: BOT_TOKEN=1234567890:ABCDEFghijklmnopqrstuvwxyz123456789" -ForegroundColor Yellow
    exit 1
}

Write-Host "   SUCCESS: BOT_TOKEN found: $($BotToken.Substring(0,[Math]::Min(10,$BotToken.Length)))..." -ForegroundColor Green

Write-Host ""
Write-Host "Deploying Basic Telegram Bot to AWS..." -ForegroundColor Green
Write-Host "Stack Name: $StackName" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Blue

# Check AWS CLI
try {
    aws --version | Out-Null
    Write-Host "   SUCCESS: AWS CLI found" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: AWS CLI not found. Please install it first." -ForegroundColor Red
    exit 1
}

# Check SAM CLI
try {
    sam --version | Out-Null
    Write-Host "   SUCCESS: SAM CLI found" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: SAM CLI not found. Please install it first." -ForegroundColor Red
    Write-Host "   Install with: choco install aws-sam-cli" -ForegroundColor Yellow
    exit 1
}

# Check AWS credentials
try {
    aws sts get-caller-identity | Out-Null
    Write-Host "   SUCCESS: AWS credentials configured" -ForegroundColor Green
} catch {
    Write-Host "   ERROR: AWS credentials not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Build the application
Write-Host "Building SAM application..." -ForegroundColor Blue
sam build

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "   SUCCESS: Build completed" -ForegroundColor Green

# Deploy the application
Write-Host "Deploying to AWS..." -ForegroundColor Blue
sam deploy --stack-name $StackName --region $Region --parameter-overrides BotToken=$BotToken --capabilities CAPABILITY_IAM --resolve-s3

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Deployment failed!" -ForegroundColor Red
    exit 1
}

# Get the webhook URL from stack outputs
Write-Host "Getting webhook URL..." -ForegroundColor Blue
$WebhookUrl = aws cloudformation describe-stacks --stack-name $StackName --region $Region --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' --output text

if ($WebhookUrl) {
    Write-Host "   SUCCESS: Webhook URL: $WebhookUrl" -ForegroundColor Green
    
    # Set the webhook
    Write-Host "Setting Telegram webhook..." -ForegroundColor Blue
    $WebhookResult = curl -s -X POST "https://api.telegram.org/bot$BotToken/setWebhook" -d "url=$WebhookUrl"
    
    if ($WebhookResult -like "*true*") {
        Write-Host "   SUCCESS: Webhook set successfully" -ForegroundColor Green
    } else {
        Write-Host "   WARNING: Webhook setup may have failed. Check manually:" -ForegroundColor Yellow
        Write-Host "   curl -X POST `"https://api.telegram.org/bot$BotToken/setWebhook`" -d `"url=$WebhookUrl`"" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ERROR: Could not retrieve webhook URL" -ForegroundColor Red
}

Write-Host ""
Write-Host "Deployment completed!" -ForegroundColor Green
Write-Host "Test your bot by sending /start on Telegram" -ForegroundColor Cyan
Write-Host ""
Write-Host "Basic Bot Testing:" -ForegroundColor Blue
Write-Host "   • Send /start -> Should reply 'Hi {your_name}!'" -ForegroundColor Gray
Write-Host "   • Send /help -> Should reply 'Help!'" -ForegroundColor Gray
Write-Host "   • Send any text -> Should echo it back" -ForegroundColor Gray
Write-Host ""
Write-Host "Monitor your deployment:" -ForegroundColor Blue
Write-Host "   • CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=$Region#logsV2:log-groups" -ForegroundColor Gray
Write-Host "   • DynamoDB Table: aihelper-users-dev" -ForegroundColor Gray
Write-Host ""
Write-Host "Estimated monthly cost: $2-13 for moderate usage" -ForegroundColor Green
Write-Host ""
Write-Host "To update your deployment:" -ForegroundColor Blue
Write-Host "   .\deploy_fixed.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "To delete everything:" -ForegroundColor Blue
Write-Host "   sam delete --stack-name $StackName --region $Region" -ForegroundColor Gray
Write-Host ""
Write-Host "Usage examples:" -ForegroundColor Blue
Write-Host "   .\deploy_fixed.ps1                                    # Deploy with default settings" -ForegroundColor Gray
Write-Host "   .\deploy_fixed.ps1 -StackName 'my-bot'               # Custom stack name" -ForegroundColor Gray
Write-Host "   .\deploy_fixed.ps1 -Region 'eu-west-1'               # Different AWS region" -ForegroundColor Gray
Write-Host "   BOT_TOKEN is always read from .env file automatically" -ForegroundColor Gray
