# Push to GitHub - Instructions

## Step 1: Create a GitHub Repository

1. Go to [GitHub](https://github.com) and sign in
2. Click the "+" icon in the top right corner
3. Select "New repository"
4. Repository name: `import-export-orchestrator` (or your preferred name)
5. Description: "Cloud-agnostic import/export orchestration service for SaaS applications"
6. Choose visibility: **Public** or **Private**
7. **DO NOT** initialize with README, .gitignore, or license (we already have these)
8. Click "Create repository"

## Step 2: Add Remote and Push

After creating the repository, GitHub will show you commands. Use these:

```bash
# Add the remote (replace USERNAME with your GitHub username)
git remote add origin https://github.com/USERNAME/import-export-orchestrator.git

# Or if using SSH:
git remote add origin git@github.com:USERNAME/import-export-orchestrator.git

# Rename default branch to main (if needed)
git branch -M main

# Push to GitHub
git push -u origin main
```

## Step 3: Verify

Visit your repository on GitHub to verify all files were pushed correctly.

## Alternative: Using GitHub CLI

If you have GitHub CLI installed:

```bash
# Create repository and push in one command
gh repo create import-export-orchestrator --public --source=. --remote=origin --push
```

## Troubleshooting

### Authentication Issues

If you get authentication errors:

**HTTPS:**
- Use a Personal Access Token instead of password
- Or use GitHub CLI: `gh auth login`

**SSH:**
- Ensure your SSH key is added to GitHub
- Test: `ssh -T git@github.com`

### Large Files

If you have large files, consider using Git LFS:
```bash
git lfs install
git lfs track "*.csv"
git lfs track "*.json"
git add .gitattributes
```

### Exclude Sensitive Files

Before pushing, ensure:
- No `.env` files with secrets
- No API keys or credentials
- No database passwords
- Check `.gitignore` is up to date

