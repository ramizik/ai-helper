# AI Assistant Deployment Script
# This script automates the deployment of your AI assistant to AWS

param(
    [Parameter(Mandatory=$true)]
    [string]$BotToken,
    
    [Parameter(Mandatory=$false)]
    [string]$StackName = "aihelper-dev",
    
    [Parameter(Mandatory=$false)]
    [string]$Region = "us-east-1"
)

Write-Host "🚀 Deploying Basic Telegram Bot to AWS..." -ForegroundColor Green
Write-Host "Stack Name: $StackName" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow

# Check prerequisites
Write-Host "✅ Checking prerequisites..." -ForegroundColor Blue

# Check AWS CLI
try {
    aws --version | Out-Null
    Write-Host "   ✓ AWS CLI found" -ForegroundColor Green
} catch {
    Write-Host "   ❌ AWS CLI not found. Please install it first." -ForegroundColor Red
    exit 1
}

# Check SAM CLI
try {
    sam --version | Out-Null
    Write-Host "   ✓ SAM CLI found" -ForegroundColor Green
} catch {
    Write-Host "   ❌ SAM CLI not found. Please install it first." -ForegroundColor Red
    Write-Host "   Install with: choco install aws-sam-cli" -ForegroundColor Yellow
    exit 1
}

# Check AWS credentials
try {
    aws sts get-caller-identity | Out-Null
    Write-Host "   ✓ AWS credentials configured" -ForegroundColor Green
} catch {
    Write-Host "   ❌ AWS credentials not configured. Run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Build the application
Write-Host "🔨 Building SAM application..." -ForegroundColor Blue
sam build

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}

Write-Host "   ✓ Build completed" -ForegroundColor Green

# Deploy the application
Write-Host "📦 Deploying to AWS..." -ForegroundColor Blue
sam deploy --stack-name $StackName --region $Region --parameter-overrides BotToken=$BotToken --capabilities CAPABILITY_IAM --resolve-s3

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    exit 1
}

# Get the webhook URL from stack outputs
Write-Host "🔍 Getting webhook URL..." -ForegroundColor Blue
$WebhookUrl = aws cloudformation describe-stacks --stack-name $StackName --region $Region --query 'Stacks[0].Outputs[?OutputKey==`WebhookUrl`].OutputValue' --output text

if ($WebhookUrl) {
    Write-Host "   ✓ Webhook URL: $WebhookUrl" -ForegroundColor Green
    
    # Set the webhook
    Write-Host "🌐 Setting Telegram webhook..." -ForegroundColor Blue
    $WebhookResult = curl -s -X POST "https://api.telegram.org/bot$BotToken/setWebhook" -d "url=$WebhookUrl"
    
    if ($WebhookResult -like "*true*") {
        Write-Host "   ✓ Webhook set successfully" -ForegroundColor Green
    } else {
        Write-Host "   ⚠️ Webhook setup may have failed. Check manually:" -ForegroundColor Yellow
        Write-Host "   curl -X POST `"https://api.telegram.org/bot$BotToken/setWebhook`" -d `"url=$WebhookUrl`"" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ❌ Could not retrieve webhook URL" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 Deployment completed!" -ForegroundColor Green
Write-Host "📱 Test your bot by sending /start on Telegram" -ForegroundColor Cyan
Write-Host ""
Write-Host "🧪 Basic Bot Testing:" -ForegroundColor Blue
Write-Host "   • Send /start → Should reply 'Hi {your_name}!'" -ForegroundColor Gray
Write-Host "   • Send /help → Should reply 'Help!'" -ForegroundColor Gray
Write-Host "   • Send any text → Should echo it back" -ForegroundColor Gray
Write-Host ""
Write-Host "📊 Monitor your deployment:" -ForegroundColor Blue
Write-Host "   • CloudWatch Logs: https://console.aws.amazon.com/cloudwatch/home?region=$Region#logsV2:log-groups" -ForegroundColor Gray
Write-Host "   • DynamoDB Table: aihelper-users-dev" -ForegroundColor Gray
Write-Host ""
Write-Host "💰 Estimated monthly cost: $3-15 for moderate usage" -ForegroundColor Green
Write-Host ""
Write-Host "🛠️ To update your deployment:" -ForegroundColor Blue
Write-Host "   sam build && sam deploy" -ForegroundColor Gray
Write-Host ""
Write-Host "🗑️ To delete everything:" -ForegroundColor Blue
Write-Host "   sam delete --stack-name $StackName --region $Region" -ForegroundColor Gray
