#!/usr/bin/env python3
"""
Email Template Generator for Recruitment
Quick templates for common outreach scenarios
"""
from datetime import datetime

TEMPLATES = {
    "initial_outreach": {
        "subject": "Reaching out regarding {company}",
        "body": """Hi {contact_name},

I hope you're having a great week.

I'm Chris Martin, working with construction companies across SEQ to place senior professionals in Project Director, Construction Manager, Senior PM, and Estimating roles.

I'm reaching out because we're working with several clients who are actively hiring for senior construction roles, and given your role at {company}, I thought you might know someone - or perhaps you might be open to a conversation yourself.

No pressure at all - happy to chat informally about the market, or if you know anyone who's currently looking for their next opportunity, I'd love to hear from them.

Would you be open to a quick 5-minute call this week?

Best regards,
Chris Martin
Principal Consultant - Construction
0422 123 456
"""
    },
    
    "candidate_interest": {
        "subject": "Senior Construction Opportunity - {location}",
        "body": """Hi {candidate_name},

I came across your profile and thought you'd be a great fit for an opportunity I'm working on.

Role: {role_title}
Company: {client_company}
Location: {location}
Salary: {salary_range}
Experience needed: {years_exp} years+

The client is a {tier} construction company working on some great projects in SEQ. They're looking for someone who can {key_requirement}.

Is this of interest? Happy to share more details over a quick call.

Best regards,
Chris Martin
Principal Consultant - Construction
0422 123 456
"""
    },
    
    "follow_up": {
        "subject": "Following up - {topic}",
        "body": """Hi {name},

Just following up on my previous message regarding {topic}.

I understand you're busy, so I'll keep this brief. If now isn't the right time, no worries at all - happy to reconnect in a few weeks.

If you'd like to chat, just let me know a time that works for you.

Best regards,
Chris Martin
Principal Consultant - Construction
0422 123 456
"""
    },
    
    "meeting_request": {
        "subject": "Meeting to discuss {company}'s hiring needs",
        "body": """Hi {contact_name},

Following up from our recent conversation about {company}'s hiring needs.

I'd love to schedule a 20-minute meeting to:
- Discuss your current and upcoming hiring requirements
- Understand your team structure and growth plans
- Explain how we help construction companies find exceptional talent

Would any of these times work for you?
- Tuesday 10am
- Wednesday 2pm
- Thursday 11am

Or feel free to suggest a time that suits you better.

Best regards,
Chris Martin
Principal Consultant - Construction
0422 123 456
"""
    },
    
    "candidate_submission": {
        "subject": "Candidate Submission - {role} for {client}",
        "body": """Hi {client_name},

Please find below my candidate submission for the {role} position.

CANDIDATE: {candidate_name}
CURRENT ROLE: {current_role} at {current_company}
EXPERIENCE: {years} years
SALARY EXPECTATION: {salary}
NOTICE PERIOD: {notice}

KEY STRENGTHS:
- {strength_1}
- {strength_2}
- {strength_3}

RELEVANT PROJECTS:
- {project_1}
- {project_2}

I believe this candidate would be an excellent fit for your team. Happy to arrange an interview at your convenience.

Best regards,
Chris Martin
Principal Consultant - Construction
0422 123 456
"""
    }
}

def list_templates():
    print("=" * 60)
    print("📧 RECRUITMENT EMAIL TEMPLATES")
    print("=" * 60)
    for name, template in TEMPLATES.items():
        print(f"\n{name.replace('_', ' ').title()}:")
        print(f"  Subject: {template['subject']}")
    print("\n" + "=" * 60)
    print("Usage: python3 email-templates.py <template_name>")
    print("Example: python3 email-templates.py initial_outreach")
    print("=" * 60)

def show_template(name):
    if name not in TEMPLATES:
        print(f"Template '{name}' not found.")
        print("Available: " + ", ".join(TEMPLATES.keys()))
        return
    
    template = TEMPLATES[name]
    print(f"\n=== {name.replace('_', ' ').upper()} ===")
    print(f"\nSUBJECT: {template['subject']}")
    print("\nBODY:")
    print(template['body'])

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        show_template(sys.argv[1])
    else:
        list_templates()
