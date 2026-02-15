"""Generate synthetic test PDF fixtures for the test suite."""

from fpdf import FPDF


def create_invoice():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "INVOICE", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 7, "Acme Corp Supplies Ltd.", ln=True)
    pdf.cell(0, 7, "123 Business Avenue, Suite 100", ln=True)
    pdf.cell(0, 7, "New York, NY 10001", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(95, 7, "Invoice Number: INV-2025-0042", ln=False)
    pdf.cell(95, 7, "Invoice Date: January 15, 2025", ln=True)
    pdf.cell(95, 7, "Due Date: February 14, 2025", ln=False)
    pdf.cell(95, 7, "PO Number: PO-8891", ln=True)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(95, 7, "Bill To:", ln=True)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(95, 7, "Global Industries Inc.", ln=True)
    pdf.cell(95, 7, "456 Corporate Drive", ln=True)
    pdf.cell(95, 7, "San Francisco, CA 94105", ln=True)
    pdf.ln(5)

    # Line items table
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(80, 7, "Description", border=1)
    pdf.cell(25, 7, "Qty", border=1, align="C")
    pdf.cell(35, 7, "Unit Price", border=1, align="R")
    pdf.cell(35, 7, "Total", border=1, align="R")
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    items = [
        ("Office Desk Chair - Ergonomic", "5", "$249.99", "$1,249.95"),
        ("Standing Desk Converter", "3", "$189.50", "$568.50"),
        ("Monitor Arm - Dual Mount", "5", "$79.99", "$399.95"),
        ("Keyboard Tray - Adjustable", "5", "$45.00", "$225.00"),
    ]
    for desc, qty, unit, total in items:
        pdf.cell(80, 7, desc, border=1)
        pdf.cell(25, 7, qty, border=1, align="C")
        pdf.cell(35, 7, unit, border=1, align="R")
        pdf.cell(35, 7, total, border=1, align="R")
        pdf.ln()

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(140, 7, "Subtotal:", align="R")
    pdf.cell(35, 7, "$2,443.40", align="R", ln=True)
    pdf.cell(140, 7, "Sales Tax (8.875%):", align="R")
    pdf.cell(35, 7, "$216.85", align="R", ln=True)
    pdf.cell(140, 7, "Total Amount:", align="R")
    pdf.cell(35, 7, "$2,660.25", align="R", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, "Payment Terms: Net 30", ln=True)
    pdf.cell(0, 7, "Please remit payment to: Acme Corp Supplies Ltd.", ln=True)
    pdf.cell(0, 7, "Bank Transfer: Chase Bank, Account: 1234567890, Routing: 021000021", ln=True)

    pdf.output("tests/fixtures/documents/invoice_digital.pdf")
    print("Created invoice_digital.pdf")


def create_resume():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "Jane Smith", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "jane.smith@email.com | +1 (555) 123-4567 | linkedin.com/in/janesmith | github.com/janesmith", ln=True, align="C")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Professional Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, "Senior Software Engineer with 8+ years of experience in building scalable cloud-native applications. Proficient in Python, Java, and TypeScript with expertise in microservices architecture, CI/CD pipelines, and distributed systems.")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Work Experience", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Senior Software Engineer - TechFlow Inc.", ln=True)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, "March 2021 - Present", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "- Led a team of 6 engineers to deliver a real-time data processing platform", ln=True)
    pdf.cell(0, 6, "- Reduced API response times by 40% through query optimization and caching", ln=True)
    pdf.cell(0, 6, "- Designed and implemented event-driven microservices using Kafka and Python", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Software Engineer - DataCore Solutions", ln=True)
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, "June 2017 - February 2021", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "- Built RESTful APIs serving 10M+ requests/day using FastAPI and PostgreSQL", ln=True)
    pdf.cell(0, 6, "- Implemented CI/CD pipelines with GitHub Actions reducing deployment time by 60%", ln=True)
    pdf.cell(0, 6, "- Developed automated testing framework achieving 95% code coverage", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Education", ln=True)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Bachelor's in Computer Science - MIT", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Graduated: May 2017 | GPA: 3.85/4.0", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Technical Skills", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Languages: Python, Java, TypeScript, SQL, Go", ln=True)
    pdf.cell(0, 6, "Frameworks: FastAPI, Spring Boot, React, Django", ln=True)
    pdf.cell(0, 6, "Tools: Docker, Kubernetes, Terraform, AWS, GCP", ln=True)
    pdf.cell(0, 6, "Certifications: AWS Solutions Architect, CKA", ln=True)

    pdf.output("tests/fixtures/documents/resume_standard.pdf")
    print("Created resume_standard.pdf")


def create_contract():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "SERVICE AGREEMENT", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, "This Service Agreement (\"Agreement\") is entered into as of the Effective Date of March 1, 2025, by and between:")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Party A: TechStar Solutions Inc.", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Address: 789 Innovation Parkway, Austin, TX 78701", ln=True)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Party B: Global Industries Inc.", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, "Address: 456 Corporate Drive, San Francisco, CA 94105", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "WHEREAS:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, "Party A is engaged in the business of providing software development and consulting services, and Party B desires to engage Party A to provide such services under the terms and conditions set forth herein.")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "NOW THEREFORE, the parties agree as follows:", ln=True)
    pdf.ln(2)

    sections = [
        ("1. Term", "This Agreement shall commence on the Effective Date of March 1, 2025, and shall continue for a period of twelve (12) months unless terminated earlier in accordance with Section 5. Termination Date: February 28, 2026."),
        ("2. Scope of Work", "Party A shall provide software development services as detailed in Exhibit A attached hereto, including system design, implementation, testing, and deployment."),
        ("3. Compensation", "Party B shall pay Party A a total contract value of $240,000.00, payable in monthly installments of $20,000.00 within 30 days of receipt of invoice."),
        ("4. Confidentiality", "Each party agrees to maintain the confidentiality of all proprietary information received from the other party and shall not disclose such information to third parties without prior written consent."),
        ("5. Termination", "Either party may terminate this Agreement with 30 days written notice. In the event of material breach, the non-breaching party may terminate immediately upon written notice."),
        ("6. Governing Law", "This Agreement shall be governed by and construed in accordance with the laws of the State of Texas, without regard to its conflict of law principles."),
    ]
    for title, body in sections:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 6, title, ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, body)
        pdf.ln(2)

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.", ln=True)
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 6, "Authorized Signatory - Party A", ln=False)
    pdf.cell(95, 6, "Authorized Signatory - Party B", ln=True)

    pdf.output("tests/fixtures/documents/contract_service.pdf")
    print("Created contract_service.pdf")


if __name__ == "__main__":
    create_invoice()
    create_resume()
    create_contract()
