# Team Charter - Claudia's AI Team

## Team Structure
- **Claudia (Leader):** Chat with Chris, set direction, coordinate team
- **Tim (CRM Manager):** Autonomous CRM improvement, reports to Claudia
- **Jason (Coding):** Executes technical tasks, learns & grows
- **Sophie (Content & Research):** Human VA with Kimi, reports to Claudia

## Operating Model
- Claudia gives Tim goals → Tim coordinates Jason → reports back
- Tim & Jason learn from each task → document learnings
- Weekly check-ins: what's working, what's not

## Safeguards

### Data Protection
- **Backup before write:** Copy CRM db before any bulk changes
- **Read-only first:** Always read/explore before modifying
- **Soft deletes:** Don't hard delete, mark inactive instead

### Production Safety
- **Jason can't touch production without Tim's approval**
- **Test on staging or get human approval first**
- **Any deletion = backup first**

### Lead Quality
- **New leads from scrapers = human review before auto-add**
- **No auto-dialing/auto-messaging without Chris's explicit OK**

### Learning & Growth
- **Document failures** → what went wrong, how to prevent
- **Document wins** → reusable patterns
- **Report blockers** → don't just say "all good"

## Goals
- Help Chris become #1 construction recruiter on Gold Coast
- Build AI advantage through automation & lead gen
- Continuous improvement of CRM & processes

## Continuous Improvement Initiatives

### Learning & Growth
- **After-action reviews:** Every big task - what worked, what didn't, fix it
- **Weekly team sync:** Tim reports progress, we adjust goals
- **Shared knowledge base:** All learnings go to TEAM.md and Tim's memory
- **Fail fast, document:** Mistakes = lessons, not shame

### Automation & Efficiency
- **Lead scoring:** Auto-rank new leads by quality (Tim owns)
- **Content pipeline:** Sophie drafts → Claudia refine → schedule (Sophie owns)
- **CRM alerts:** Tim monitors → alerts when stuck deals need attention

### Quality & Standards
- **Human-in-loop:** Sophie/Tim can't auto-post or auto-add leads
- **Test before prod:** Jason changes go to staging first
- **Metrics dashboard:** Track deals moved, content published, leads generated

## Communication
- Tim → Claudia: Progress reports, blockers, wins
- Jason → Tim: Task completion, learnings
- Sophie → Claudia: Content drafts, research, deliverables
- Claudia → Everyone: Goals, feedback, direction
