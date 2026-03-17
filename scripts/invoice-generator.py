#!/usr/bin/env python3
"""
Invoice Generator - Creates simple recruitment invoices
Usage: python3 invoice-generator.py <candidate_name> <client_name> <fee>
"""
import sys
from datetime import datetime
from pathlib import Path

INVOICES_DIR = Path("/home/chris/.openclaw/workspace/memory/invoices")
INVOICES_DIR.mkdir(exist_ok=True)

def generate_invoice(candidate, client, fee, days=30):
    """Generate a simple invoice"""
    invoice_num = datetime.now().strftime("%Y%m%d%H%M")
    date = datetime.now().strftime("%Y-%m-%d")
    due = datetime.now().strftime("%Y-%m-%d")
    
    invoice = f"""RECRUITMENT INVOICE
{'='*50}

Invoice #: INV-{invoice_num}
Date: {date}
Due: {due}

FROM: Chris M - Recruitment Services
TO: {client}

{'='*50}

Candidate: {candidate}
Placement Fee: ${float(fee):,.2f}
GST (10%): ${float(fee)*0.1:,.2f}
{'='*50}
TOTAL: ${float(fee)*1.1:,.2f}

Payment Terms: {days} days
BSB: [YOUR BSB]
Account: [YOUR ACCOUNT]

Thank you for your business!
"""
    
    filename = INVOICES_DIR / f"INV-{invoice_num}.txt"
    with open(filename, 'w') as f:
        f.write(invoice)
    
    print(invoice)
    print(f"\n✅ Saved to: {filename}")
    return filename

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 invoice-generator.py <candidate> <client> <fee>")
        print("Example: python3 invoice-generator.py 'John Smith' 'Hutchinson Builders' 15000")
        sys.exit(1)
    
    generate_invoice(sys.argv[1], sys.argv[2], sys.argv[3])
