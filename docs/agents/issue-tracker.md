# Issue Tracker

Issues live in GitHub at **BechtC/Stundenerfassung**.

## Usage

Use the `gh` CLI for all issue operations:

```bash
# Create
gh issue create --title "..." --body "..." --label "needs-triage"

# List
gh issue list

# View
gh issue view <number>

# Update
gh issue edit <number> --add-label "ready-for-agent"
gh issue close <number>
```

## Conventions

- One issue = one vertical slice of work (independently deployable)
- Title format: `[Feature] ...` / `[Bug] ...` / `[Chore] ...`
- Body: what, why, acceptance criteria
- Milestones map to named releases (e.g. `v1.1-live-tracker`)
