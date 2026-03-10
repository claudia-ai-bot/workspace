# CODE.md - Coding Rules

## Golden Rule: Always Save to GitHub

**Every piece of code created or modified goes to GitHub.**

No exceptions. Local-only code is lost code.

### Workflow

1. **Create/modify code** → Save locally first (test, verify)
2. **Commit to git** → `git add . && git commit -m "descriptive message"`
3. **Push to GitHub** → `git push origin main`
4. **Log in MEMORY.md** → Document what was built & where (GitHub link)

### Repository Structure

- **Main repo:** `https://github.com/claudia-ai-bot/workspace`
- **Subdirectories:**
  - `skills/` — Agent skills & tools
  - `projects/` — Standalone projects (trading, recruitment, etc.)
  - `scripts/` — Utilities & automation
  - `docs/` — Documentation & guides

### Before Pushing

- ✅ Code is tested & working
- ✅ Commit message is clear ("Add trading scanner", not "update")
- ✅ No secrets/API keys in code (use .env or comments like `# API_KEY`)
- ✅ README.md updated if new project

### Backup Rule

If code exists only locally and something breaks:
- It's gone
- You can't recover it
- The pain is real

**GitHub is source of truth. Always.**

## Tools

- `git status` — Check what's changed
- `git log` — View commit history
- `gh repo view` — Check repo on GitHub
- `gh repo create` — New repos (if needed)

## Example

```bash
# After building code
git add skills/reminders/
git commit -m "Add AEST-aware reminder system with heartbeat integration"
git push origin main

# Update MEMORY.md
# Added: Reminder automation to GitHub repo
```

That's it. Simple, consistent, safe.
