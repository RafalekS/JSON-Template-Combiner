#!/usr/bin/env powershell

Write-Host "JSON Template Combiner - GitHub Setup" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

# Check if we're in the right directory
$currentDir = Get-Location
if (-not (Test-Path "main.py")) {
    Write-Host "❌ Error: main.py not found. Make sure you're in the project directory." -ForegroundColor Red
    Write-Host "Expected: C:\Users\r_sta\Downloads\projects\python\JSON Template Combiner" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Found project files in: $currentDir" -ForegroundColor Green

# Check if GitHub CLI is installed
$ghInstalled = Get-Command gh -ErrorAction SilentlyContinue
if (-not $ghInstalled) {
    Write-Host "`n❌ GitHub CLI (gh) not found." -ForegroundColor Red
    Write-Host "Install options:" -ForegroundColor Yellow
    Write-Host "1. winget install --id GitHub.cli" -ForegroundColor White
    Write-Host "2. choco install gh" -ForegroundColor White
    Write-Host "3. scoop install gh" -ForegroundColor White
    Write-Host "`nOr continue with manual method? (y/n)" -ForegroundColor Yellow
    
    $continue = Read-Host
    if ($continue -ne "y") {
        exit 1
    } else {
        # Manual method
        Write-Host "`n🔧 Manual Method:" -ForegroundColor Cyan
        Write-Host "1. Go to: https://github.com/new" -ForegroundColor Yellow
        Write-Host "2. Repository name: JSON-Template-Combiner" -ForegroundColor Yellow
        Write-Host "3. Description: GUI application for combining multiple JSON container templates into Portainer format" -ForegroundColor Yellow
        Write-Host "4. Make it Public" -ForegroundColor Yellow
        Write-Host "5. DON'T initialize with README (you already have files)" -ForegroundColor Yellow
        Write-Host "6. Click 'Create repository'" -ForegroundColor Yellow
        
        $repoUrl = Read-Host "`nAfter creating, paste the repository URL here (e.g., https://github.com/RafalekS/JSON-Template-Combiner.git)"
        
        if ($repoUrl -eq "") {
            Write-Host "❌ No URL provided. Exiting..." -ForegroundColor Red
            exit 1
        }
        
        try {
            Write-Host "`nSetting up git remote..." -ForegroundColor Yellow
            git remote add origin $repoUrl
            git branch -M main
            git push -u origin main
            
            Write-Host "🎉 SUCCESS! Repository created and pushed!" -ForegroundColor Green
            Write-Host "Your repository: $repoUrl" -ForegroundColor Cyan
        } catch {
            Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
        }
        
        exit 0
    }
}

# GitHub CLI method
Write-Host "✓ GitHub CLI found!" -ForegroundColor Green

# Check if authenticated
$authStatus = gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n🔐 Not authenticated with GitHub. Logging in..." -ForegroundColor Yellow
    gh auth login
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Authentication failed" -ForegroundColor Red
        exit 1
    }
}

Write-Host "✓ Authenticated with GitHub!" -ForegroundColor Green

# Check git status
Write-Host "`n📊 Checking git status..." -ForegroundColor Yellow
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "📝 Uncommitted changes found. Committing first..." -ForegroundColor Yellow
    git add .
    git commit -m "Complete JSON Template Combiner project"
}

# Create repository and push
Write-Host "`n🚀 Creating GitHub repository and pushing..." -ForegroundColor Yellow

$repoName = "JSON-Template-Combiner"
$description = "GUI application for combining multiple JSON container templates into Portainer format"

try {
    gh repo create $repoName --public --description $description --source=. --remote=origin --push
    
    Write-Host "`n🎉 SUCCESS!" -ForegroundColor Green
    Write-Host "Repository created: https://github.com/RafalekS/$repoName" -ForegroundColor Cyan
    Write-Host "Local repository connected and code pushed!" -ForegroundColor Green
    
    # Open repository in browser
    $openBrowser = Read-Host "`nOpen repository in browser? (y/n)"
    if ($openBrowser -eq "y") {
        gh repo view --web
    }
    
} catch {
    Write-Host "❌ Error creating repository: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nTrying alternative approach..." -ForegroundColor Yellow
    
    # Alternative: create repo then push
    gh repo create $repoName --public --description $description
    git remote add origin "https://github.com/RafalekS/$repoName.git"
    git branch -M main
    git push -u origin main
    
    Write-Host "✓ Repository created with alternative method!" -ForegroundColor Green
}

Write-Host "`n📋 Next steps:" -ForegroundColor Cyan
Write-Host "• Share your repository URL with others" -ForegroundColor White
Write-Host "• Add topics/tags for discoverability" -ForegroundColor White
Write-Host "• Consider creating releases for easy downloads" -ForegroundColor White

Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
