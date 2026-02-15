"""
Sprint 2 — Keyword Classifier Engine tests.

Verifies that KeywordClassifier scores documents correctly against
keyword dictionaries and returns proper ClassificationResult objects.

Run:  PYTHONPATH=. .venv/Scripts/pytest tests/test_classifier.py -v
"""

import pytest

from src.classifiers.engine import KeywordClassifier, _EXCLUSION_PENALTY
from src.config.loader import load_categories, CategoryConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def classifier():
    return KeywordClassifier()


@pytest.fixture(scope="module")
def categories():
    return load_categories()


# ---------------------------------------------------------------------------
# Synthetic document texts for each category
# ---------------------------------------------------------------------------

INVOICE_TEXT = """
TAX INVOICE

Invoice Number: INV-2025-0042
Invoice No: INV-2025-0042
Inv No: INV-2025-0042
Invoice Date: 15/01/2025
Due Date: 15/02/2025
Payment Due: 15/02/2025

Bill To / Billed To:
  Acme Corp
  123 Main Street

Remit To:
  SupplierCo Ltd — Remittance Department
  Please Remit payment to the account below.

| Line Item     | Item Description | Quantity | Unit Price | Unit Cost |
|---------------|-----------------|----------|-----------|-----------|
| Widget A      | Premium widget  |       10 |    $25.00 |   $250.00 |
| Service Fee   | Consulting      |        1 |    $50.00 |    $50.00 |

Subtotal / Sub-Total: $300.00
Discount: $0.00
Freight / Shipping Charges: $0.00
Tax Rate: 10% (GST / VAT / Sales Tax)
Total Amount: $330.00
Amount Due: $330.00
Total Due: $330.00
Balance Due: $330.00

Payment Terms: Net 30
Vendor: SupplierCo Ltd
Supplier: SupplierCo Ltd
Account Number: 9876543210
PO Number: PO-2025-1001
Bank Transfer / Wire Transfer / ACH
IBAN: GB29NWBK60161331926819
SWIFT: NWBKGB2L
Beneficiary: SupplierCo Ltd
Please Pay within 30 days. Overdue invoices subject to late fee.
"""

RESUME_TEXT = """
RESUME / CURRICULUM VITAE (CV)

Jane Smith
Software Engineer

Contact Information:
Email: jane.smith@example.com
Phone / Mobile: (555) 123-4567
Address: 123 Main St, City, CA 94000
LinkedIn: linkedin.com/in/janesmith
GitHub: github.com/janesmith
Portfolio: janesmith.dev

Career Objective / Objective:
Seeking a senior position where I can leverage my core competencies.

Professional Summary / Career Summary:
Experienced software engineer with 8 years of professional experience
and strong qualifications in full-stack development.

Technical Skills / Skills:
  Python, Java, React, AWS, Docker, Kubernetes

Work Experience / Professional Experience / Employment History:
  Job Title: Senior Developer
  Position: Lead Engineer
  Company / Employer: TechCorp (Dates of Employment: 2019-Present)
  Responsibilities and Achievements:
  - Managed and led team of 5 engineers
  - Developed microservices architecture
  - Promoted to lead within 1 year
  - Accomplishments: Reduced latency by 40%

  Software Engineer, StartupXYZ (2015-2019)

Education / Academic Background:
  Degree: Bachelor of Science in Computer Science
  University / College / Institute: MIT, 2015
  GPA / CGPA: 3.8/4.0

Certifications / Certified / Training:
  AWS Solutions Architect (Licenses: SA-12345)
  Certified Kubernetes Administrator

Publications / Awards / Honors:
  - Best Paper Award, IEEE 2020

Languages Spoken: English, Spanish
Hobbies / Interests: Open source, hiking
Projects: Built a real-time dashboard

Volunteer: Code mentoring at local college

References Available Upon Request / References upon request.
"""

CONTRACT_TEXT = """
SERVICE AGREEMENT / CONTRACT

This Agreement is entered into as of the Effective Date between the Parties:

Party of the First Part: TechStar Solutions Inc. ("Provider"), hereinafter
referred to as "Provider".
Party of the Second Part: GlobalCo Ltd. ("Client"), hereinafter referred to
as "Client".

WHEREAS the Provider has expertise in software development services;
NOW THEREFORE the parties agree to the following terms and conditions:

1. Term: This contract shall commence on January 1, 2025 and continue
   for a period of 12 months unless terminated earlier. Renewal and
   extension options are available.

2. Termination: Either party may terminate with 30 days written notice.
   Upon breach, the non-breaching party may seek remedy and damages.

3. Governing Law / Jurisdiction: This agreement shall be governed by
   the laws of the State of California. Arbitration / Mediation shall
   be the primary dispute resolution mechanism.

4. Indemnification: Each party agrees to indemnify the other against
   all liability. Limitation of Liability: Neither party's aggregate
   liability shall exceed the total fees paid.

5. Force Majeure: Neither party shall be liable for failure to perform
   due to events beyond reasonable control.

6. Dispute Resolution: Any disputes shall be resolved through arbitration.

7. Entire Agreement: This constitutes the entire agreement between the
   parties. Any amendment or addendum must be in writing.

8. Confidentiality / Non-Disclosure / NDA: Each party agrees to maintain
   confidentiality of proprietary information. Intellectual Property / IP
   Ownership and Assignment shall be governed by Exhibit A.

9. Representations and Warranties: Each party represents and warrants that
   it has authority to execute this agreement. Severability and waiver
   provisions apply.

10. Scope of Work / Statement of Work / SOW: See Schedule A for deliverables,
    compensation, fees, payment schedule, and milestones.

11. Service Level / SLA: Provider shall maintain 99.9% uptime.

Notice: All notices shall be sent to the addresses listed in counterparts.
Signature: Each authorized signatory has executed this agreement.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the
Effective Date written above.
"""

PURCHASE_ORDER_TEXT = """
PURCHASE ORDER

PO Number / PO No / P.O. Number: PO-2025-1001
P.O.# PO-2025-1001
Order Number: ORD-2025-5678
Order Date: 2025-01-20
Delivery Date / Required Date / Promised Date: 2025-02-15

Ship To / Deliver To / Delivery Address:
  Acme Corp Warehouse / Receiving
  456 Industrial Blvd

Buyer: John Procurement
Procurement Department
Ordered By: Engineering Team
Approved By: Jane Director
Requisition Number / Requisition No: REQ-2025-0042
Order Confirmation: Confirmed

Vendor / Supplier: SupplierCo Ltd
Contact Person: Bob Sales
Phone: (555) 999-0000
Email: sales@supplierco.com
Billing Address: 789 Vendor St

| Item Number | Part Number / SKU | Description        | Quantity | Unit of Measure / UOM | Unit Price | Extended Price / Line Total |
|-------------|-------------------|--------------------|----------|-----------------------|-----------|-----------------------------|
| 001         | RAW-100           | Raw Material       |      100 | EA                    |    $10.00 | $1,000.00                   |

Subtotal / Total Value: $1,000.00
Shipping Terms / FOB / Incoterms: FOB Destination
Payment Terms: Net 30 / Net 60
Goods Received at Warehouse
Blanket Order / Release Number: N/A
"""

BANK_STATEMENT_TEXT = """
BANK STATEMENT / ACCOUNT STATEMENT / STATEMENT OF ACCOUNT

Bank: First National Bank
Branch: Downtown Branch
Account Holder: Jane Smith
Account Number: 1234567890
Checking Account / Current Account
Sort Code: 12-34-56
Routing Number: 021000021
IBAN: GB29NWBK60161331926819
SWIFT Code / BIC: NWBKGB2L
BSB Number: 062-000
IFSC: SBIN0001234

Statement Period: 01/01/2025 - 31/01/2025

Opening Balance / Brought Forward: $5,000.00
Available Balance / Current Balance / Ledger Balance: $7,300.00

Transactions / Transaction Date:
| Date       | Description / Reference Number | Debit      | Credit  | Balance   |
|------------|-------------------------------|------------|---------|-----------|
| 01/01/2025 | Direct Deposit / EFT          |            | $3,000  | $8,000.00 |
| 03/01/2025 | Direct Debit / Standing Order  |    $100.00 |         | $7,900.00 |
| 05/01/2025 | ATM / ATM Withdrawal          |    $200.00 |         | $7,700.00 |
| 10/01/2025 | POS / Point of Sale           |     $50.00 |         | $7,650.00 |
| 12/01/2025 | Wire Transfer / ACH           |    $150.00 |         | $7,500.00 |
| 15/01/2025 | Online Banking / Funds Transfer|    $200.00 |         | $7,300.00 |
| 20/01/2025 | Deposits                      |            |   $500  | $7,800.00 |

Closing Balance / Carried Forward: $7,300.00
Total Deposits: $3,500.00
Total Withdrawals: $700.00
Net Change: +$2,800.00
Withdrawals Summary
Interest Earned: $5.00
Interest Charged: $0.00
Annual Percentage Rate / APR: 0.05%
Overdraft / Overdraft Limit: $1,000.00
Savings Account linked.
"""

RECEIPT_TEXT = """
RECEIPT

Receipt Number: REC-2025-0099
Date: 15/01/2025

Payment Received from: Acme Corp
Payment Confirmation / Order Confirmation
Transaction Complete / Sale Confirmed
Your payment has been processed.
Your order has been placed.

Store / Merchant: WidgetMart
Cashier / Served By: Employee #42
Register / Till: #3
POS / Terminal ID: T-100
Authorization Code / Approval Code: AUTH-9876

Payment Method: Credit Card / Visa / Mastercard
Card Number (Last 4 Digits): **** 1234
Contactless payment

| Items Purchased | Qty  | Unit Price | Item Total |
|-----------------|------|-----------|------------|
| Widget A        |   10 |    $25.00 |    $250.00 |
| Service Fee     |    1 |    $50.00 |     $50.00 |

Subtotal: $300.00
Discount Applied / Coupon / Promo Code: None
Tax Included / Tax Collected: $30.00
Grand Total / Amount Paid / Total Paid: $330.00
Cash Received: $350.00
Change Given / Change Due: $20.00
Transaction ID / Transaction Number: TXN-ABC-12345

Loyalty Points / Reward Points: +33 points earned
Thank you for your purchase!
Thank you for your payment!
Paid — this is a receipt for your records.
Keep This Receipt for returns.
Return Policy: 30 days with receipt.
Exchange Policy: Same item only.
Table Number: N/A
Reference Number: REF-2025-0099
"""

REPORT_TEXT = """
QUARTERLY BUSINESS REPORT / ANNUAL REPORT

Report Number / Report ID: RPT-2025-Q4
Report Date / Date of Report: January 15, 2025
Prepared By / Submitted By: Analytics Team
Prepared For / Submitted To: Executive Board

Table of Contents
List of Figures
List of Tables

1. Executive Summary / Overview / Background:
This report provides a comprehensive analysis of Q4 2024 business
performance with key findings and recommendations for improvement.

2. Scope / Objective:
Evaluate fiscal year quarter 4 performance against KPI / Key Performance
Indicator targets and benchmark metrics.

3. Methodology / Data Analysis:
Data was collected from internal CRM and financial systems. Trend analysis
and forecast / projection models were applied. Assumptions and limitations
are documented in Appendix B.

4. Key Findings / Findings:
  - Revenue increased by 15% year to date (YTD)
  - Customer acquisition cost decreased by 8%
  - Variance from budget: +5%
  - Period performance exceeded expectations

5. Risk Assessment / Risk / Mitigation:
  Market risk: moderate. Mitigation strategies in place.

6. Recommendations / Action Items / Next Steps:
  Continue current marketing strategy. Observations suggest opportunity
  for expansion.

7. Conclusion:
The company showed strong growth in Q4 quarter. Stakeholders should
review the financial summary.

8. Appendix / Glossary / References / Bibliography:
  See attached data tables and status report.
  Progress Report on ongoing initiatives.
  Incident Report: None this period.
"""

GIBBERISH_TEXT = """
Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.
"""


# ---------------------------------------------------------------------------
# TestScoreCategory — unit tests for _score_category()
# ---------------------------------------------------------------------------

class TestScoreCategory:

    def test_invoice_primary_matches(self, classifier, categories):
        cfg = categories["invoice"]
        text = "invoice invoice number bill to due date total amount".lower()
        confidence, matched = classifier._score_category(text, cfg)
        assert confidence > 0
        assert "invoice" in matched
        assert "invoice number" in matched

    def test_min_primary_guard(self, classifier, categories):
        """Below min_primary_matches → confidence must be 0.0."""
        cfg = categories["invoice"]  # min_primary_matches = 2
        text = "invoice".lower()  # only 1 primary match
        confidence, matched = classifier._score_category(text, cfg)
        assert confidence == 0.0
        assert matched == []

    def test_exclusion_penalty(self, classifier, categories):
        cfg = categories["invoice"]
        # Text with enough primary matches but also exclusion keyword
        text = "invoice invoice number bill to due date payment received".lower()
        conf_with_exclusion, _ = classifier._score_category(text, cfg)

        text_no_exclusion = "invoice invoice number bill to due date amount due".lower()
        conf_without_exclusion, _ = classifier._score_category(text_no_exclusion, cfg)

        # Exclusion should reduce confidence by the penalty factor
        assert conf_with_exclusion < conf_without_exclusion
        assert conf_with_exclusion == pytest.approx(
            conf_without_exclusion * _EXCLUSION_PENALTY, abs=0.05
        )

    def test_empty_text_returns_zero(self, classifier, categories):
        cfg = categories["invoice"]
        confidence, matched = classifier._score_category("", cfg)
        assert confidence == 0.0
        assert matched == []

    def test_secondary_keywords_boost(self, classifier, categories):
        cfg = categories["invoice"]
        # Enough primary matches
        base_text = "invoice invoice number bill to due date total amount"
        conf_base, _ = classifier._score_category(base_text.lower(), cfg)

        # Add secondary keywords
        boosted_text = base_text + " vendor supplier account number subtotal tax"
        conf_boosted, matched_boosted = classifier._score_category(boosted_text.lower(), cfg)

        assert conf_boosted > conf_base
        # Secondary keywords should appear in matched list
        assert any(kw in matched_boosted for kw in ["vendor", "supplier", "subtotal"])

    def test_all_categories_scorable(self, classifier, categories):
        """Every category config can be scored without errors."""
        for slug, cfg in categories.items():
            confidence, matched = classifier._score_category("random text", cfg)
            assert isinstance(confidence, float)
            assert isinstance(matched, list)


# ---------------------------------------------------------------------------
# TestClassify — integration tests for classify()
# ---------------------------------------------------------------------------

class TestClassify:

    def test_invoice_classification(self, classifier):
        result = classifier.classify(INVOICE_TEXT)
        assert result.category == "invoice"
        assert result.method == "deterministic"
        assert result.confidence >= 0.60
        assert len(result.matched_keywords) > 0
        assert result.escalation_reason is None

    def test_resume_classification(self, classifier):
        result = classifier.classify(RESUME_TEXT)
        assert result.category == "resume"
        assert result.method == "deterministic"
        assert result.confidence >= 0.60

    def test_contract_classification(self, classifier):
        result = classifier.classify(CONTRACT_TEXT)
        assert result.category == "contract"
        assert result.method == "deterministic"
        assert result.confidence >= 0.55

    def test_purchase_order_classification(self, classifier):
        result = classifier.classify(PURCHASE_ORDER_TEXT)
        assert result.category == "purchase_order"
        assert result.method == "deterministic"

    def test_bank_statement_classification(self, classifier):
        result = classifier.classify(BANK_STATEMENT_TEXT)
        assert result.category == "bank_statement"
        assert result.method == "deterministic"

    def test_receipt_classification(self, classifier):
        result = classifier.classify(RECEIPT_TEXT)
        assert result.category == "receipt"
        assert result.method == "deterministic"

    def test_report_classification(self, classifier):
        result = classifier.classify(REPORT_TEXT)
        assert result.category == "report"
        assert result.method == "deterministic"

    def test_gibberish_unclassified(self, classifier):
        result = classifier.classify(GIBBERISH_TEXT)
        assert result.method == "unclassified"
        assert result.escalation_reason is not None
        assert len(result.escalation_reason) > 0

    def test_empty_string_unclassified(self, classifier):
        result = classifier.classify("")
        assert result.method == "unclassified"
        assert result.escalation_reason is not None

    def test_confidence_range(self, classifier):
        """Confidence must always be in [0.0, 1.0]."""
        for text in [INVOICE_TEXT, RESUME_TEXT, CONTRACT_TEXT, GIBBERISH_TEXT, ""]:
            result = classifier.classify(text)
            assert 0.0 <= result.confidence <= 1.0

    def test_matched_keywords_are_strings(self, classifier):
        result = classifier.classify(INVOICE_TEXT)
        assert all(isinstance(kw, str) for kw in result.matched_keywords)

    def test_deterministic_method_has_no_escalation(self, classifier):
        result = classifier.classify(INVOICE_TEXT)
        if result.method == "deterministic":
            assert result.escalation_reason is None
            assert result.llm_unavailable is False


# ---------------------------------------------------------------------------
# TestExtractFields — regex extraction tests
# ---------------------------------------------------------------------------

class TestExtractFields:

    def test_invoice_number_extraction(self, classifier, categories):
        cfg = categories["invoice"]
        fields = classifier.extract_fields(INVOICE_TEXT, cfg)
        assert "invoice_number" in fields
        assert "INV-2025-0042" in fields["invoice_number"]

    def test_invoice_date_extraction(self, classifier, categories):
        cfg = categories["invoice"]
        fields = classifier.extract_fields(INVOICE_TEXT, cfg)
        assert "invoice_date" in fields

    def test_resume_email_extraction(self, classifier, categories):
        cfg = categories["resume"]
        fields = classifier.extract_fields(RESUME_TEXT, cfg)
        assert "email" in fields
        assert fields["email"] == "jane.smith@example.com"

    def test_no_match_returns_empty(self, classifier, categories):
        cfg = categories["invoice"]
        fields = classifier.extract_fields("no matching content here", cfg)
        assert isinstance(fields, dict)
        # May be empty or have no invoice-specific fields
        assert "invoice_number" not in fields

    def test_extract_all_categories_no_crash(self, classifier, categories):
        """Extraction should not crash on any category with any text."""
        for slug, cfg in categories.items():
            fields = classifier.extract_fields("random text with no structure", cfg)
            assert isinstance(fields, dict)


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_case_insensitivity(self, classifier):
        """Classification should work regardless of text casing."""
        upper = classifier.classify(INVOICE_TEXT.upper())
        lower = classifier.classify(INVOICE_TEXT.lower())
        assert upper.category == lower.category == "invoice"

    def test_multiple_category_overlap_picks_best(self, classifier):
        """When text matches multiple categories, the highest confidence wins."""
        result = classifier.classify(INVOICE_TEXT)
        # Invoice text should not be classified as something else
        assert result.category == "invoice"

    def test_exclusion_keywords_can_demote(self, classifier):
        """Text with strong invoice keywords + exclusion should get lower confidence."""
        # Invoice text with "payment received" (exclusion keyword)
        modified = INVOICE_TEXT + "\nPayment Received. Paid in Full."
        result = classifier.classify(modified)
        # Either still invoice with lower confidence or unclassified
        if result.category == "invoice":
            normal = classifier.classify(INVOICE_TEXT)
            assert result.confidence < normal.confidence

    def test_result_is_classification_result(self, classifier):
        """Return type is always ClassificationResult."""
        from src.models.schemas import ClassificationResult
        result = classifier.classify(INVOICE_TEXT)
        assert isinstance(result, ClassificationResult)
