# GitHub CI/CD Setup Guide

This guide will help you configure your GitHub repository to automatically run tests on pull requests and require them to pass before merging.

## ✅ What's Already Done

1. **GitHub Actions workflow created** (`.github/workflows/ci.yml`)
   - Automatically runs on all pull requests to `main`/`master`
   - Runs all tests using pytest
   - Reports pass/fail status

## 🔧 What You Need to Configure in GitHub

### Step 1: Enable GitHub Actions (if not already enabled)

1. Go to your repository on GitHub
2. Click **Settings** → **Actions** → **General**
3. Under "Workflow permissions", select:
   - ✅ **Read and write permissions** (or Read-only if you prefer)
   - ✅ **Allow GitHub Actions to create and approve pull requests** (if needed)
4. Click **Save**

### Step 2: Set Up Branch Protection Rules

This is **required** to enforce that tests must pass before merging.

1. Go to your repository on GitHub
2. Click **Settings** → **Branches**
3. Click **Add branch protection rule**
4. Under **Branch name pattern**, enter: `main` (or `master` if that's your default branch)
5. Enable the following settings:

#### Required Settings:

✅ **Require a pull request before merging**
   - ✅ Require approvals: `1` (optional, but recommended)
   - ✅ Dismiss stale pull request approvals when new commits are pushed (optional)

✅ **Require status checks to pass before merging**
   - ✅ Require branches to be up to date before merging
   - ✅ In the status check list, select: **`CI Tests / Run Tests`**
     - This is the name of the job from `ci.yml`
     - It will appear after the first workflow run

✅ **Do not allow bypassing the above settings** (recommended)
   - This prevents even admins from merging without passing tests

#### Optional but Recommended:

✅ **Require conversation resolution before merging**
   - Ensures all PR comments are addressed

✅ **Require linear history** (optional)
   - Prevents merge commits, requires rebasing

6. Click **Create** or **Save changes**

### Step 3: Verify It Works

1. Create a test branch:
   ```bash
   git checkout -b test-ci-setup
   ```

2. Make a small change (e.g., add a comment to a file)

3. Commit and push:
   ```bash
   git add .
   git commit -m "Test CI workflow"
   git push origin test-ci-setup
   ```

4. Create a Pull Request on GitHub

5. Go to the **Actions** tab in your repository
   - You should see a workflow run starting
   - Wait for it to complete (usually 1-2 minutes)

6. Check the PR:
   - If tests pass: ✅ Green checkmark appears
   - If tests fail: ❌ Red X appears, merge button is disabled

## 📋 Checklist

- [ ] GitHub Actions enabled in repository settings
- [ ] Branch protection rule created for `main`/`master`
- [ ] "Require status checks" enabled
- [ ] "CI Tests / Run Tests" selected as required check
- [ ] "Require branches to be up to date" enabled
- [ ] Test PR created and workflow runs successfully

## 🐛 Troubleshooting

### Workflow doesn't appear in status checks

- **Wait for first run**: The status check name appears after the first workflow completes
- **Check workflow file**: Ensure `.github/workflows/ci.yml` is in your repository
- **Check branch**: Workflow triggers on PRs to `main`/`master` only

### Tests pass locally but fail in CI

- **Python version**: CI uses Python 3.12, ensure your local matches
- **Dependencies**: Ensure `requirements.txt` is committed and up to date
- **Environment variables**: CI sets safe defaults, but check if your code needs specific values

### Can't merge even though tests pass

- **Check branch protection**: Ensure "Require branches to be up to date" is enabled
- **Update PR branch**: Merge or rebase `main` into your PR branch
- **Check other requirements**: Ensure approvals, reviews, etc. are satisfied

### Workflow not running at all

- **Check Actions tab**: Look for any error messages
- **Check file location**: Must be `.github/workflows/ci.yml`
- **Check YAML syntax**: Use a YAML validator
- **Check repository settings**: Ensure Actions are enabled

## 📚 Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Branch Protection Rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [Required Status Checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches#require-status-checks-before-merging)

