#!/bin/bash

# TraceTrack One-Click Deployment Script
# This script handles: Git setup, GitHub repo creation, secrets, and AWS deployment

set -e

echo "🚀 TraceTrack One-Click Deployment"
echo "=================================="

# Check required tools
command -v git >/dev/null 2>&1 || { echo "Git is required but not installed. Aborting." >&2; exit 1; }
command -v gh >/dev/null 2>&1 || { echo "GitHub CLI is required. Install with: brew install gh" >&2; exit 1; }
command -v aws >/dev/null 2>&1 || { echo "AWS CLI is required. Install with: pip install awscli" >&2; exit 1; }

# Get user inputs
read -p "Enter your GitHub username: " GITHUB_USER
read -p "Enter repository name (default: tracetrack): " REPO_NAME
REPO_NAME=${REPO_NAME:-tracetrack}

echo ""
echo "📋 AWS Credentials Setup"
echo "You can find these in AWS Console > IAM > Users > Security Credentials"
read -p "Enter AWS Access Key ID: " AWS_ACCESS_KEY
read -s -p "Enter AWS Secret Access Key: " AWS_SECRET_KEY
echo ""

# Initialize git if not already
if [ ! -d ".git" ]; then
    echo "📁 Initializing Git repository..."
    git init
    git add .
    git commit -m "Initial commit - TraceTrack application"
fi

# Login to GitHub CLI
echo "🔐 Logging into GitHub..."
gh auth login --web

# Create GitHub repository
echo "📦 Creating GitHub repository..."
gh repo create $REPO_NAME --public --source=. --remote=origin --push

# Add AWS secrets to repository
echo "🔑 Adding AWS secrets to GitHub repository..."
echo $AWS_ACCESS_KEY | gh secret set AWS_ACCESS_KEY_ID
echo $AWS_SECRET_KEY | gh secret set AWS_SECRET_ACCESS_KEY

# Trigger GitHub Actions deployment
echo "🚀 Triggering deployment..."
gh workflow run deploy.yml

echo ""
echo "✅ Setup Complete!"
echo "📖 Repository: https://github.com/$GITHUB_USER/$REPO_NAME"
echo "⚡ Deployment started automatically"
echo ""
echo "📱 Monitor deployment:"
echo "   gh run list"
echo "   gh run watch"
echo ""
echo "🌐 Your app will be live at the URL shown in the deployment logs"
echo "   (Usually takes 5-10 minutes)"

# Optional: Watch the deployment
read -p "Watch deployment progress? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "👀 Watching deployment..."
    gh run watch
fi