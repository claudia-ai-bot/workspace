#!/usr/bin/env python3
"""
Quick Call Script for Construction Recruitment
Best-practice questions for discovery calls
"""
from datetime import datetime

SCRIPTS = {
    "initial_client_call": {
        "purpose": "First call with a new client to understand their hiring needs",
        "questions": [
            "Thanks for making time to chat today. Mind if I ask a few quick questions?",
            "What projects are you currently working on, or have coming up?",
            "Who's the biggest challenge to hire at the moment?",
            "What's your hiring timeline for this role?",
            "Have you used a recruiter before, or is this your first time?",
            "What's the most important thing for someone in this role to succeed?",
            "What's the budget range for this role?",
            "Who will they report to, and what's the team structure?",
            "What's the next step if we find the right person?",
            "Is there anything else I should know about the role or company?"
        ],
        "tips": [
            "Listen 80%, talk 20%",
            "Take notes on their words, use them back",
            "Ask 'tell me more' to get details",
            "Don't pitch yet - just learn",
            "End by summarising what you heard and next steps"
        ]
    },
    
    "candidate_call": {
        "purpose": "Screening call with a potential candidate",
        "questions": [
            "Thanks for speaking with me today. What made you interested in this opportunity?",
            "Can you tell me about your current role and what you're responsible for?",
            "What type of projects have you worked on recently?",
            "What's your notice period?",
            "What's your salary expectation for your next role?",
            "Are you open to moving, or are you location-specific?",
            "What are you looking for in your next role that's different from your current one?",
            "Who have you reported to, and what was that relationship like?",
            "What's your ideal company culture?",
            "Any other roles or companies you're speaking with?",
            "What questions do you have for me about the role?"
        ],
        "tips": [
            "Build rapport first - people buy from people",
            "Match their energy",
            "Don't rush - let them talk",
            "Take notes - you'll forget",
            "Sell the opportunity, not just the job",
            "Always ask for referrals at the end"
        ]
    },
    
    "reference_check": {
        "purpose": "Calling a referee to verify a candidate",
        "questions": [
            "Hi, I'm calling from Lead Group. Is now a convenient time?",
            "How do you know [candidate name] and in what capacity?",
            "What was their role and responsibilities?",
            "What were their key strengths?",
            "Can you give me an example of where they excelled?",
            "How did they handle conflict or difficult situations?",
            "What areas would they need to develop?",
            "Would you hire them again? Why or why not?",
            "Is there anything else I should know?",
            "Thanks for your time. Can I use your name as a referee?"
        ],
        "tips": [
            "Always ask permission to record",
            "Get specific examples, not just opinions",
            "Listen between the lines",
            "Ask 'would you hire them again' twice",
            "Thank them for their honesty"
        ]
    }
}

def list_scripts():
    print("=" * 60)
    print("📞 RECRUITMENT CALL SCRIPTS")
    print("=" * 60)
    for name, script in SCRIPTS.items():
        print(f"\n{name.replace('_', ' ').title()}:")
        print(f"  Purpose: {script['purpose']}")
        print(f"  Questions: {len(script['questions'])}")
    print("\n" + "=" * 60)
    print("Usage: python3 call-scripts.py <script_name>")
    print("Example: python3 call-scripts.py initial_client_call")
    print("=" * 60)

def show_script(name):
    if name not in SCRIPTS:
        print(f"Script '{name}' not found.")
        print("Available: " + ", ".join(SCRIPTS.keys()))
        return
    
    script = SCRIPTS[name]
    print(f"\n=== {name.replace('_', ' ').upper()} ===")
    print(f"Purpose: {script['purpose']}\n")
    
    print("QUESTIONS:")
    for i, q in enumerate(script['questions'], 1):
        print(f"  {i}. {q}")
    
    print("\nTIPS:")
    for tip in script['tips']:
        print(f"  • {tip}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        show_script(sys.argv[1])
    else:
        list_scripts()
