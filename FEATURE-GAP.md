# SEQ CRM Feature Gap Analysis

## What We Have (vs JobAdder/Bullhorn)

| Feature | Status | Notes |
|---------|--------|-------|
| Companies | ✅ | Full CRUD |
| Decision Makers | ✅ | With relationship score |
| Candidates | ✅ | Status, tags, availability |
| Deals (Pipeline) | ✅ | Stages, probability |
| Contacts | ✅ | Activity logging |
| Leads | ✅ | Intel tracking |
| Projects | ✅ | Linked to companies |
| Activities | ✅ | Calls, meetings, visits |
| Submissions | ✅ | Candidate→Deal flow |
| Job Adverts | ✅ | Post tracking |

## Missing / Needs Improvement

### High Priority

1. **Activity Timeline** 
   - Need: Chronological view of all activities per company/candidate
   - Current: Activities exist but no unified timeline
   - *Implement: Add timeline view to company detail page*

2. **Automated Follow-up Reminders**
   - Need: System reminds when next_action date passes
   - Current: next_action dates exist but no reminder system
   - *Implement: Reminder checker (like trading reminders)*

3. **Deal Stage Visual Pipeline**
   - Need: Kanban-style pipeline view
   - Current: List view only
   - *Implement: Drag-drop pipeline board*

4. **Quick Actions**
   - Need: One-click "Log Call", "Schedule Follow-up"
   - Current: Forms only
   - *Implement: Quick action buttons on company/candidate cards*

### Medium Priority

5. **Candidate-Job Matching** - Better search/filter
6. **Email Integration** - (Maybe skip - keep simple)
7. **Reporting Dashboard** - Weekly metrics summary

## Best Practices to Steal

From JobAdder/Bullhorn reviews:
- **Clean, intuitive UI** - Don't overcomplicate
- **One-click job distribution** - Quick post to multiple boards
- **Strong search** - Fast filtering across candidates/companies
- **Activity auto-log** - Track everything against records

## Implementation Plan

**Tonight (Jason):**
1. Activity timeline component
2. Quick action buttons
3. Reminder system for follow-ups

**Later:**
4. Pipeline board
5. Enhanced search
