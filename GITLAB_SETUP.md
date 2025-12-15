# GitLab Setup Guide

**Repository**: ContinuuAI (Private)  
**User**: tiationist  
**Status**: Ready to push

---

## Quick Start (Automated)

```bash
./setup-gitlab.sh
```

The script will guide you through:
1. Creating the repository
2. Setting up authentication
3. Pushing the code

---

## Manual Setup (Alternative)

### Step 1: Create Repository on GitLab

1. Go to: https://gitlab.com/tiationist
2. Click **"New project"** → **"Create blank project"**
3. Set:
   - **Project name**: `ContinuuAI`
   - **Visibility**: **Private**
   - **Initialize with README**: ❌ Uncheck
4. Click **"Create project"**

---

### Step 2: Choose Authentication Method

#### Option A: Personal Access Token (Recommended)

1. Go to: https://gitlab.com/-/user_settings/personal_access_tokens
2. Click **"Add new token"**
3. Set:
   - **Name**: `ContinuuAI-push`
   - **Scopes**: ✅ `write_repository`
   - **Expiration**: Your choice (e.g., 1 year)
4. Click **"Create personal access token"**
5. **Copy the token** (save it securely)

#### Option B: SSH Key

1. Generate SSH key (if not exists):
   ```bash
   ssh-keygen -t ed25519 -C "your.email@example.com"
   ```

2. Copy public key:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```

3. Add to GitLab:
   - Go to: https://gitlab.com/-/user_settings/ssh_keys
   - Paste key, add title, save

---

### Step 3: Add Remote and Push

#### Using HTTPS (with token):

```bash
cd /home/adminator/projects/ContinuuAI

# Add remote
git remote add origin https://gitlab.com/tiationist/ContinuuAI.git

# Push (use token as password when prompted)
git push -u origin main
```

**Credentials**:
- Username: `tiationist`
- Password: `[your-token-here]`

#### Using SSH:

```bash
cd /home/adminator/projects/ContinuuAI

# Add remote
git remote add origin git@gitlab.com:tiationist/ContinuuAI.git

# Push
git push -u origin main
```

---

## Verify Setup

After pushing, check:

1. **Repository URL**: https://gitlab.com/tiationist/ContinuuAI
2. **Visibility**: Should show 🔒 Private
3. **Files**: Should see README.md, docs/, scripts/, etc.

---

## Current Repository State

**Branch**: `main`  
**Commits**: 2 (initial + v1.0.0)  
**Files**: 60+ files including:
- Complete test suite (6 suites)
- Observability endpoints
- Diátaxis documentation structure
- CI/CD workflow

---

## Next Steps (After Push)

### 1. Configure CI/CD (Optional)

The repository includes `.github/workflows/greenfield-ci.yml`.

For GitLab CI, create `.gitlab-ci.yml`:

```yaml
image: python:3.12

stages:
  - test

test:
  stage: test
  services:
    - postgres:16
    - qdrant/qdrant:v1.9.1
  variables:
    POSTGRES_DB: continuuai
    POSTGRES_USER: continuuai
    POSTGRES_PASSWORD: continuuai
  script:
    - pip install -r services/retrieval/requirements.txt
    - cd services/retrieval && python migrate.py
    - cd ../.. && ./scripts/run_all_tests.sh
```

### 2. Invite Collaborators

1. Go to: https://gitlab.com/tiationist/ContinuuAI/-/project_members
2. Click **"Invite members"**
3. Add users with appropriate roles

### 3. Set Up Branch Protection

1. Go to: Settings → Repository → Branch rules
2. Protect `main` branch:
   - Require merge requests
   - Require CI to pass

---

## Troubleshooting

### "Remote already exists"

```bash
git remote remove origin
# Then add the new remote again
```

### "Authentication failed"

**Token**: Verify token has `write_repository` scope  
**SSH**: Check key added to GitLab and SSH agent running

```bash
ssh -T git@gitlab.com  # Test SSH connection
```

### "Repository not found"

- Verify repository exists: https://gitlab.com/tiationist/ContinuuAI
- Check repository name matches exactly

### "Push rejected"

Repository might have existing content. To force push:
```bash
git push -u origin main --force
```
**⚠️ Warning**: Only use `--force` on first push to empty repo

---

## Repository Information

**Clone URLs**:
- HTTPS: `https://gitlab.com/tiationist/ContinuuAI.git`
- SSH: `git@gitlab.com:tiationist/ContinuuAI.git`

**Size**: ~2MB (excluding dependencies)  
**Language**: Python  
**License**: MIT (recommended)

---

## Security Notes

1. **Never commit secrets** - Use `.env` files (already in `.gitignore`)
2. **Rotate tokens regularly** - Set expiration dates
3. **Use SSH keys** - More secure than tokens for daily use
4. **Enable 2FA** - On your GitLab account

---

## Quick Commands Reference

```bash
# Check remote
git remote -v

# Check current branch
git branch --show-current

# View commit history
git log --oneline -5

# Push new changes
git add -A
git commit -m "feat: your message"
git push

# Pull latest changes
git pull origin main
```

---

**Ready to push?** Run: `./setup-gitlab.sh`
