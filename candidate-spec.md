# Candidate Intelligence System - SPEC.md

## Overview
Build a deep candidate intelligence system for SEQ Construction CRM that helps Chris understand candidates at a fundamental level, match them to projects, and win candidates before clients even ask.

## Design Decisions

### 1. Candidate Data Model
**Decision:** Extend existing candidates table instead of creating new table
- Keep existing columns (name, current_company, title, etc.)
- Add new columns for deep intelligence

**New candidate fields:**
- `status` (existing) → Pipeline: Prospect → Engaged → Placed → Alumni
- `email`, `phone`, `linkedin` - Contact details
- `availability` - Current availability status
- `tags` - Fit tags (fast-paced, methodical, residential, civil, etc.)
- `preferences_loved` - What they loved about past roles
- `preferences_hated` - What they hated
- `dealbreakers` - Hard no's
- `aspirations_role` - Target next role
- `aspirations_salary` - Target salary
- `aspirations_location` - Preferred location
- `signals` - What's making them tick NOW (salary, bored, growth, culture, commute)
- `relationship_score` (existing) - Keep 1-5 scale

### 2. Work History (Candidate Projects)
**Decision:** Create separate `candidate_projects` table
- Links to candidate via candidate_id
- Tracks: project_name, company, duration, role, keyachievements
- Allows multiple project histories per candidate

### 3. Project Intelligence
**Decision:** Create `project_intelligence` table linked to existing projects
- `project_id` - Links to existing projects table
- `what_makes_it_interesting` - Why candidates would want this
- `ideal_candidate_profile` - Who thrives here
- `team_culture` - Culture description
- `hiring_manager_style` - PM/GM's management style
- `pace` - Fast-paced, steady, etc.
- `project_type` - Residential, commercial, civil, industrial
- `key_skill_requirements` - Must-have skills
- `nice_to_have` - Bonus skills

### 4. Matching Logic
**Decision:** Simple scoring algorithm based on:
- Role alignment (title matches job type)
- Location preference match
- Salary band overlap
- Tag compatibility (candidate tags vs project requirements)
- Signal alignment (what candidate wants vs what project offers)

**Score 1-10 with reason:** "Great fit: Residential PM with Gold Coast location preference matches this Brisbane high-rise"

## Visual Design
- **Background:** Dark slate theme (#1a1a2e base, not the light theme in base.html)
- **Accent color:** Teal/Cyan (#00d4ff) - differentiates from leads
- **Consistent pattern:** Filter bars, status pills, company links
- **Mobile-friendly:** Responsive grid layouts

## Page Structure

### 1. /candidates - List View
- Filter bar (status, location, salary, specialism, tags)
- Search
- Cards showing: Name, current role/company, status, last contact, match score
- Quick actions: View, Edit, Add to pipeline

### 2. /candidates/<id> - Deep Profile
- Header: Name, title, company, status pill
- Contact details panel
- **Left column:** Profile (role, experience, salary, location)
- **Middle column:** 
  - Preferences (loved/hated/dealbreakers)
  - Aspirations (next role, salary, location)
  - Current Signals
  - Fit tags
- **Right column:** Work history timeline
- **Sidebar:** Best-fit projects with match scores and reasons

### 3. /candidates/add - Add/Edit Form
- Multi-section form: Basic info, Contact, Preferences, Aspirations, Signals, Tags
- Work history entry (add multiple)
- Save/Cancel actions

### 4. /project-intelligence - Projects List
- List of projects with intelligence summary
- Shows: Project name, company, type, candidate fit count
- Quick view of intel summary

### 5. /project-intelligence/<id> - Project Detail
- Project overview (from existing projects table)
- Intelligence panel: What makes it interesting, ideal candidate, team culture
- Hiring needs: Current roles needed
- **Sidebar:** Best-fit candidates with scores and reasons

## Routes to Add
- `GET /candidates` - List (already exists, enhance)
- `GET /candidates/<id>` - Detail
- `POST /candidates/add` - Add new
- `POST /candidates/<id>/edit` - Update
- `GET /project-intelligence` - List
- `GET /project-intelligence/<id>` - Detail
- `POST /project-intelligence/<id>/edit` - Update intel

## Database Migration
Add columns to existing candidates table:
- email, phone, linkedin, availability
- preferences_loved, preferences_hated, dealbreakers
- aspirations_role, aspirations_salary, aspirations_location
- signals

Create new tables:
- candidate_projects (id, candidate_id, project_name, company, start_date, end_date, role, achievements)
- project_intelligence (id, project_id, what_makes_interesting, ideal_profile, team_culture, manager_style, pace, project_type, key_skills, nice_to_have)

## Acceptance Criteria
1. ✅ Candidates list shows with filter bar, status pills, search
2. ✅ Candidate profile shows deep info: preferences, aspirations, signals, tags
3. ✅ Work history displays as timeline
4. ✅ Project intelligence page shows all projects with intel
5. ✅ Matching sidebar on candidate shows best-fit projects
6. ✅ Matching sidebar on project shows best-fit candidates
7. ✅ Dark theme with teal accent throughout
8. ✅ Mobile responsive