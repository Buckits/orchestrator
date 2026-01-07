---
name: git-commits
description: Orchestrate git commits with conventional message formatting, HEREDOC syntax, and human approval requirements
---

# Skill: Git Commits

Use this skill for commit orchestration and message formatting. This ensures consistent, meaningful commit history.

---

## ⚠️ CRITICAL: Human Approval Required

**ALL commits require explicit human approval before execution.**

- **NEVER** auto-commit without user confirmation
- **ALWAYS** propose the commit and wait for approval
- **SHOW** the user what will be committed before executing

---

## When to Use This Skill

- Session reaches 100% completion
- User completes a work session
- Significant feature/fix implemented
- Before session archival
- User explicitly requests commit

---

## Commit Proposal Triggers

When ANY of these conditions are met, **PROPOSE** (not execute) a commit:

| Trigger | Condition | Action |
|---------|-----------|--------|
| Session Complete | TodoWrite shows 100% completion | Propose commit to user |
| Feature Done | Complete feature implementation | Propose commit to user |
| User Request | "commit", "save changes", "done" | Show proposed commit, ask for approval |
| Pre-Archive | Before archiving session file | Propose commit to user |

---

## Commit Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                     COMMIT WORKFLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. CHECK STATUS                                                 │
│     git status                                                   │
│     - Review all changed files                                   │
│     - Identify untracked files                                   │
│                                                                  │
│  2. ANALYZE CHANGES                                              │
│     git diff --staged                                            │
│     git diff                                                     │
│     - Understand what changed                                    │
│     - Group related changes                                      │
│                                                                  │
│  3. CLASSIFY CHANGES                                             │
│     - Determine commit type                                      │
│     - Identify scope                                             │
│     - Note breaking changes                                      │
│                                                                  │
│  4. PROPOSE TO USER ⚠️ STOP HERE                                 │
│     - Show files that would be staged                            │
│     - Show proposed commit message                               │
│     - ASK FOR EXPLICIT APPROVAL                                  │
│     - Wait for user to confirm                                   │
│                                                                  │
│  === ONLY AFTER USER APPROVAL ===                                │
│                                                                  │
│  5. STAGE FILES                                                  │
│     git add [files]                                              │
│     - Stage related files together                               │
│                                                                  │
│  6. COMMIT                                                       │
│     git commit -m "..."                                          │
│     - Use HEREDOC for multi-line                                 │
│                                                                  │
│  7. VERIFY                                                       │
│     git status                                                   │
│     git log -1                                                   │
│     - Confirm commit succeeded                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Commit Message Format

### Structure

```
{type}({scope}): {summary}

{body}

{footer}
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(auth): add user login` |
| `fix` | Bug fix | `fix(api): resolve timeout issue` |
| `refactor` | Code restructuring | `refactor(core): simplify handlers` |
| `docs` | Documentation | `docs(readme): update setup guide` |
| `test` | Tests | `test(auth): add service tests` |
| `chore` | Maintenance | `chore(deps): update dependencies` |
| `perf` | Performance | `perf(query): optimize search` |

### Summary Rules

- Imperative mood ("add" not "added")
- Lowercase (no capital first letter)
- No period at end
- Max 50 characters

---

## Examples

### Simple Feature

```bash
git commit -m "feat(user): add profile endpoint"
```

### Session Completion

```bash
git commit -m "$(cat <<'EOF'
feat(auth): implement user authentication - Session 001 completed

- Created User model with email validation
- Added login/logout API endpoints
- Implemented JWT token generation

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Bug Fix

```bash
git commit -m "$(cat <<'EOF'
fix(api): resolve memory leak in request handler

- Added proper cleanup in error paths
- Fixed buffer accumulation issue
- Added memory limit configuration

Fixes #123

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## HEREDOC Usage

**ALWAYS** use HEREDOC for multi-line commit messages:

```bash
git commit -m "$(cat <<'EOF'
feat: your commit summary

- Detail line 1
- Detail line 2
- Detail line 3

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Why HEREDOC?

- Preserves newlines correctly
- Handles special characters
- Works consistently across shells
- Avoids quote escaping issues

---

## What NOT to Commit

### Always Exclude

| Pattern | Reason |
|---------|--------|
| `.env` | Contains secrets |
| `.env.local` | Local configuration |
| `node_modules/` | Dependencies |
| `dist/` | Build output |
| `*.log` | Log files |
| `.DS_Store` | macOS metadata |

### Check .gitignore

Verify sensitive files are in `.gitignore` before committing.

---

## Pre-Commit Checklist

Before executing commit:

- [ ] `git status` shows expected files
- [ ] No sensitive files (secrets, credentials)
- [ ] Build passes
- [ ] Types generated (if applicable)
- [ ] TodoWrite reflects completed work
- [ ] Session file updated (if applicable)

---

## Post-Commit Verification

After commit:

```bash
# Verify commit
git log -1 --oneline

# Check status is clean
git status

# Verify message format
git log -1 --format="%B"
```

---

## Session Commit Integration

### When Session Completes

1. **Check TodoWrite**
   - All items should be `completed`

2. **Check Session File**
   - All checkboxes should be `[x]`
   - Implementation notes complete

3. **Propose Commit to User**
   - Show files that would be committed
   - Show proposed commit message (include session reference)
   - **ASK FOR APPROVAL** before executing
   - Wait for explicit user confirmation

4. **After User Approves**
   - Execute the commit
   - Archive session: Rename `session-current.md` to `session-N.md`

### Session Commit Format

```bash
git commit -m "$(cat <<'EOF'
feat: [feature summary] - Session [NUMBER] completed

[Bullet points from session work]

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

---

## Quick Reference

### Common Commands

```bash
# Check status
git status

# Stage all changes
git add .

# Stage specific files
git add path/to/file

# View staged changes
git diff --staged

# View unstaged changes
git diff

# Commit with message
git commit -m "message"

# View recent commits
git log --oneline -5

# Push to remote
git push
```

### Message Templates

```
# Feature
feat(scope): add new capability

# Fix
fix(scope): resolve issue with X

# Refactor
refactor(scope): restructure X for Y

# Session Complete
feat: implement X - Session N completed
```

### Commit Checklist

- [ ] Status checked
- [ ] Changes reviewed
- [ ] Files staged appropriately
- [ ] Message follows format
- [ ] No secrets included
- [ ] Build passes
- [ ] Commit verified
