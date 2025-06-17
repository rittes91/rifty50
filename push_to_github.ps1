# Push Nifty50 Project to GitHub
# Run this script to deploy your code

Write-Host "🚀 Nifty 50 GitHub Deployment Script" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

# Check if we have commits
$commits = git log --oneline 2>$null
if (-not $commits) {
    Write-Host "❌ No commits found. Creating initial commit..." -ForegroundColor Red
    git add .
    git commit -m "🚀 Initial commit: Nifty 50 Technical Analysis Bot"
}

Write-Host "📝 Current commit:" -ForegroundColor Yellow
git log --oneline -1

Write-Host "`n🔑 Authentication Required:" -ForegroundColor Yellow
Write-Host "When prompted for credentials, use:" -ForegroundColor White
Write-Host "Username: rittes91" -ForegroundColor Cyan
Write-Host "Password: [Your GitHub Personal Access Token]" -ForegroundColor Cyan
Write-Host "`n💡 Get token from: https://github.com/settings/tokens" -ForegroundColor Blue
Write-Host "Required permissions: repo, workflow" -ForegroundColor Blue

Write-Host "`n🚀 Pushing to GitHub..." -ForegroundColor Green

# Configure git for this session
git config user.name "rittes91"
git config user.email "rittes91@github.com"

# Push to GitHub
git push -u origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ SUCCESS! Your repository is now live at:" -ForegroundColor Green
    Write-Host "https://github.com/rittes91/rifty50" -ForegroundColor Cyan
    Write-Host "`n🎉 Next steps:" -ForegroundColor Yellow
    Write-Host "1. Set up environment variables for deployment" -ForegroundColor White
    Write-Host "2. Deploy on Render/Heroku/Railway" -ForegroundColor White
    Write-Host "3. Configure your Telegram bot token" -ForegroundColor White
} else {
    Write-Host "`n❌ Push failed. Please check your credentials and try again." -ForegroundColor Red
    Write-Host "💡 Make sure you're using your Personal Access Token as password" -ForegroundColor Yellow
}

Write-Host "`nPress any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

