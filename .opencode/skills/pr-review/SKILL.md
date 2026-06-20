---
name: pr-review
description: Handle GitHub PR review comments — fetch, fix, commit, reply, and verify. Use when review feedback arrives on a pull request.
license: MIT
metadata:
  author: Claude
  version: "1.0"
---

# PR Review Workflow

Handle GitHub PR review comments systematically: fetch all comments, fix each issue in a separate commit, reply with commit SHA, and run quality checks.

**Input**: PR number (or auto-detected from current branch).
**Prerequisites**: `gh` CLI authenticated, git push access.

## Steps

### 1. Fetch all review comments

Get all review comments with full metadata (IDs, paths, line numbers, diff hunks):

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments --paginate
```

Key fields to extract per comment:
- `id` — comment ID for replying
- `path` — file path
- `line` / `original_line` — line number
- `body` — the review text
- `diff_hunk` — context snippet

### 2. Read affected files

Read each file referenced in the comments in full to understand the surrounding context before making changes.

### 3. Fix each issue in a separate commit

- Create one commit per logical fix
- Use descriptive commit messages: `fix: short description`
- Keep commits focused and atomic
- Reference the review context in the commit body if helpful

### 4. Reply to each review comment

For each comment, post a reply referencing the fix commit:

```bash
gh api repos/{owner}/{repo}/pulls/{number}/comments/{comment_id}/replies \
  -f body="Fixed in {sha} — short description of the fix"
```

### 5. Push and run quality checks

```bash
git push origin {branch}
```

Then run project checks:
- Backend: ruff check, ruff format --check, pytest
- Frontend: ESLint, TypeScript build, Vitest
- Docker Compose: config --quiet

## Output On Success

```text
## PR Review Complete ✓

**Changes (N commits):**
- `{sha}` fix: description
- ...

**Quality Checks:**
- Backend: ruff ✓, pytest ✓ (N tests)
- Frontend: ESLint ✓, build ✓, Vitest ✓ (N tests)
- Docker: ✓

All review comments replied to.
```

## Tips

- For Copilot reviews, the author is typically "github-actions[bot]" or "Copilot"
- Always reply in German if the PR/project uses German
- When multiple comments affect the same file, consider batching them in one commit but reply to each individually
- If a comment is a question rather than a fix request, answer rather than commit
