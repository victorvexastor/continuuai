#!/usr/bin/env bash
set -euo pipefail

echo "=== ContinuuAI GitLab Setup ==="
echo ""
echo "This script will help you push ContinuuAI to GitLab."
echo ""

# Configuration
GITLAB_USER="tiationist"
REPO_NAME="ContinuuAI"
GITLAB_URL="https://gitlab.com"

echo "📋 Repository Details:"
echo "   GitLab User: ${GITLAB_USER}"
echo "   Repository:  ${REPO_NAME}"
echo "   Visibility:  Private"
echo ""

# Check if remote already exists
if git remote get-url origin &>/dev/null; then
    CURRENT_REMOTE=$(git remote get-url origin)
    echo "⚠️  Remote 'origin' already exists: ${CURRENT_REMOTE}"
    echo ""
    read -p "Remove existing remote and continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git remote remove origin
        echo "✅ Removed existing remote"
    else
        echo "❌ Aborted"
        exit 1
    fi
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 STEP 1: Create GitLab Repository"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Please follow these steps in your browser:"
echo ""
echo "1. Go to: ${GITLAB_URL}/${GITLAB_USER}"
echo "2. Click 'New project' > 'Create blank project'"
echo "3. Set:"
echo "   - Project name: ${REPO_NAME}"
echo "   - Visibility: Private"
echo "   - Initialize with README: NO (uncheck)"
echo "4. Click 'Create project'"
echo ""
read -p "Press ENTER when repository is created..."
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔐 STEP 2: Authentication Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Choose authentication method:"
echo ""
echo "Option A: Personal Access Token (Recommended)"
echo "   1. Go to: ${GITLAB_URL}/-/user_settings/personal_access_tokens"
echo "   2. Create token with 'write_repository' scope"
echo "   3. Copy the token"
echo ""
echo "Option B: SSH Key"
echo "   1. Go to: ${GITLAB_URL}/-/user_settings/ssh_keys"
echo "   2. Add your SSH public key (~/.ssh/id_rsa.pub)"
echo ""
read -p "Which method? (token/ssh): " AUTH_METHOD
echo ""

if [[ "$AUTH_METHOD" == "token" ]]; then
    echo "Using HTTPS with Personal Access Token"
    REMOTE_URL="${GITLAB_URL}/${GITLAB_USER}/${REPO_NAME}.git"
    echo ""
    echo "⚠️  When you push, use your token as the password"
    echo "   Username: ${GITLAB_USER}"
    echo "   Password: [your-token-here]"
elif [[ "$AUTH_METHOD" == "ssh" ]]; then
    echo "Using SSH authentication"
    REMOTE_URL="git@gitlab.com:${GITLAB_USER}/${REPO_NAME}.git"
else
    echo "❌ Invalid choice. Aborted."
    exit 1
fi

echo ""
echo "Adding remote: ${REMOTE_URL}"
git remote add origin "${REMOTE_URL}"
echo "✅ Remote added"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📤 STEP 3: Push to GitLab"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Current branch: $(git branch --show-current)"
echo "Ready to push? This will upload all code to GitLab."
echo ""
read -p "Push to GitLab now? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Push cancelled"
    echo ""
    echo "To push later, run:"
    echo "  git push -u origin main"
    exit 0
fi

echo ""
echo "Pushing to GitLab..."
if git push -u origin main; then
    echo ""
    echo "✅ Successfully pushed to GitLab!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🎉 Setup Complete!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Repository URL:"
    echo "  ${GITLAB_URL}/${GITLAB_USER}/${REPO_NAME}"
    echo ""
    echo "Clone URL:"
    echo "  ${REMOTE_URL}"
    echo ""
    echo "Next steps:"
    echo "  1. View your repository in GitLab"
    echo "  2. Configure CI/CD (optional)"
    echo "  3. Invite collaborators (Settings > Members)"
    echo ""
else
    echo ""
    echo "❌ Push failed"
    echo ""
    echo "Common issues:"
    echo "  - Invalid credentials"
    echo "  - Repository doesn't exist"
    echo "  - Network issues"
    echo ""
    echo "To retry:"
    echo "  git push -u origin main"
    echo ""
    exit 1
fi
