# ContinuuAI Service Agreement
## Decision Continuity System - Standard Contract Template

**AGREEMENT DATE:** [Date]  
**PARTIES:**  
- **Provider:** ContinuuAI, Inc. (Delaware Corporation)  
- **Customer:** [Organization Name]  
**EFFECTIVE DATE:** [Date]  
**INITIAL TERM:** 12 months

---

## 1. SERVICE DESCRIPTION

### 1.1 Core Service
ContinuuAI provides a private, cloud-hosted decision continuity system ("Service") that:
- Preserves decision rationale, tradeoffs, and context
- Reflects patterns in organizational decision-making
- Maintains audit trails of strategic reasoning
- Provides query interfaces for decision recall

### 1.2 Service Boundaries
ContinuuAI explicitly **does not**:
- Make recommendations or direct decisions
- Optimize or nudge user behavior
- Passively ingest data without explicit user recording
- Share data across organizations
- Use Customer data to train models for other customers

### 1.3 Human Judgment Primacy Clause
**Critical Principle:** If at any time Customer determines that the Service is reducing human judgment capacity instead of supporting it, Customer may terminate this Agreement immediately under Section 8.3 with full data export and no penalty.

---

## 2. PRICING & PAYMENT

### 2.1 Fees
**Monthly Fee:** $10,000 USD  
**Annual Fee (if prepaid):** $114,000 USD (5% discount)  
**Pilot Option (if applicable):** $30,000 USD for 90 days, credited toward annual fee if continued

### 2.2 Payment Terms
- Monthly: Due on 1st of each month, net 15 days
- Annual: Due upon contract execution
- Late payments subject to 1.5% monthly interest

### 2.3 Fee Adjustments
Fees may increase upon renewal by no more than 8% annually, with 90 days notice.

---

## 3. DATA OWNERSHIP & PRIVACY

### 3.1 Customer Data Ownership
**Absolute Principle:** Customer retains complete ownership of all data recorded in the Service, including:
- Decision records
- Context annotations
- User inputs
- Generated reflections

### 3.2 Data Usage by Provider
Provider may access Customer data only for:
- Service delivery and support
- Aggregate, anonymized performance analytics (no customer identification)
- Security and abuse prevention

Provider **shall not**:
- Use Customer data to train models for other customers
- Share Customer data with third parties (except subprocessors listed in Exhibit A)
- Retain Customer data beyond contract termination (see Section 3.5)

### 3.3 Data Storage & Security
- Data stored in SOC 2 Type II compliant infrastructure
- Encryption at rest (AES-256) and in transit (TLS 1.3)
- Access controls: role-based, audit-logged
- Geographic storage: [Customer-selected region]

### 3.4 Data Portability
Customer may export all data at any time in machine-readable JSON format at no charge.

### 3.5 Data Deletion
Upon contract termination:
- Provider shall delete all Customer data within 30 days
- Customer may request immediate deletion (completed within 7 days)
- Provider shall provide written certification of deletion
- Backups deleted within 90 days

---

## 4. ACCESS CONTROL & SECURITY

### 4.1 Authentication
- SSO integration required (SAML 2.0 or OAuth 2.0)
- Multi-factor authentication enforced
- Role-based access control configured by Customer

### 4.2 Audit Logging
All access and changes logged with:
- User identity
- Timestamp
- Action performed
- IP address

Logs retained for 13 months and accessible to Customer.

### 4.3 Security Incidents
Provider shall notify Customer within 24 hours of confirmed security incident affecting Customer data.

---

## 5. SERVICE LEVEL AGREEMENT (SLA)

### 5.1 Availability
**Target:** 99.5% monthly uptime (excluding planned maintenance)

**Planned Maintenance:**
- Maximum 4 hours per month
- Scheduled during off-peak hours
- 72 hours advance notice

### 5.2 SLA Credits
If availability < 99.5% in a month:
- 99.0% - 99.5%: 10% monthly fee credit
- 98.0% - 99.0%: 25% monthly fee credit
- < 98.0%: 50% monthly fee credit

### 5.3 Support
**Response Times:**
- Critical (system down): 4 hours
- High (major function impaired): 8 business hours
- Medium (minor issue): 2 business days
- Low (question, feature request): 5 business days

**Support Channels:** Email, with optional Slack channel for pilot customers

---

## 6. INTELLECTUAL PROPERTY

### 6.1 Provider IP
Provider retains all rights to:
- ContinuuAI software and platform
- Algorithms and methodologies
- General product improvements

### 6.2 Customer IP
Customer retains all rights to:
- Decision content
- Organizational knowledge
- Business strategies recorded in Service

### 6.3 Feedback License
Customer grants Provider non-exclusive license to use feedback and feature requests to improve the Service, but not to disclose Customer identity without permission.

---

## 7. WARRANTIES & DISCLAIMERS

### 7.1 Provider Warranties
Provider warrants that:
- Service will perform materially as described in documentation
- Provider has authority to enter this Agreement
- Service will comply with applicable data protection laws

### 7.2 Customer Warranties
Customer warrants that:
- Customer has rights to data uploaded to Service
- Customer will comply with acceptable use policy (Exhibit B)
- Customer will not use Service for illegal purposes

### 7.3 DISCLAIMER
**SERVICE PROVIDED "AS IS" BEYOND SECTION 7.1 WARRANTIES.**

Provider does not warrant that:
- Service will prevent all decision-making errors
- Service will improve organizational outcomes
- Service operation will be uninterrupted or error-free

---

## 8. TERM & TERMINATION

### 8.1 Initial Term
12 months from Effective Date, unless terminated earlier per this Section.

### 8.2 Renewal
Automatically renews for successive 12-month terms unless either party provides 90 days written notice of non-renewal.

### 8.3 Termination for Cause
Either party may terminate if:
- Other party materially breaches and fails to cure within 30 days of notice
- Other party becomes insolvent or files for bankruptcy

### 8.4 Termination for Reduced Judgment (Customer Right)
**Ethical Termination Clause:**  
Customer may terminate immediately without penalty if Customer determines the Service is reducing human judgment capacity. Customer must provide written notice stating this rationale.

### 8.5 Effects of Termination
Upon termination:
- Customer access ends on termination date
- Provider provides data export within 7 days
- Provider deletes all Customer data per Section 3.5
- Customer pays fees prorated to termination date (unless terminating under 8.4)

---

## 9. LIABILITY & INDEMNIFICATION

### 9.1 Limitation of Liability
**Provider's maximum aggregate liability: 12 months of fees paid**

Exceptions (no liability cap):
- Gross negligence or willful misconduct
- Data breach due to Provider's security failures
- Violation of data ownership rights (Section 3)
- IP indemnification (Section 9.3)

### 9.2 Excluded Damages
Neither party liable for indirect, incidental, consequential, or punitive damages, **except**:
- Damages from Provider's data breach or misuse
- Damages from Provider's IP infringement

### 9.3 Provider Indemnification
Provider shall indemnify Customer against claims that the Service infringes third-party IP rights, provided:
- Customer promptly notifies Provider
- Provider controls defense
- Customer cooperates reasonably

### 9.4 Customer Indemnification
Customer shall indemnify Provider against claims arising from:
- Customer's data content
- Customer's violation of acceptable use policy
- Customer's breach of law

---

## 10. CONFIDENTIALITY

### 10.1 Confidential Information
Each party shall protect the other's confidential information with same care as its own (minimum: reasonable care).

### 10.2 Exceptions
Confidentiality obligations do not apply to information that:
- Is publicly available (not through breach)
- Was known prior to disclosure
- Is independently developed
- Must be disclosed by law (with notice if possible)

---

## 11. COMPLIANCE & REGULATORY

### 11.1 Data Protection Laws
Provider shall comply with:
- GDPR (for EU customer data)
- CCPA (for California customer data)
- Applicable data protection laws in Customer's jurisdiction

### 11.2 Subprocessors
Provider shall:
- Maintain list of subprocessors (Exhibit A)
- Provide 30 days notice of subprocessor changes
- Allow Customer objection to new subprocessors

### 11.3 Audit Rights
Customer may audit Provider's compliance once annually upon 30 days notice. Provider shall cooperate reasonably at no charge.

---

## 12. GENERAL PROVISIONS

### 12.1 Governing Law
This Agreement governed by laws of [State of Delaware / Customer's State], without regard to conflict of law principles.

### 12.2 Dispute Resolution
**Step 1:** Good faith negotiation (30 days)  
**Step 2:** Mediation (if negotiation fails)  
**Step 3:** Binding arbitration (JAMS rules, single arbitrator)

**Exception:** Either party may seek injunctive relief in court for IP or confidentiality breaches.

### 12.3 Assignment
Neither party may assign without written consent, except:
- Provider may assign to affiliate or acquirer
- Customer may assign to successor entity

### 12.4 Force Majeure
Neither party liable for delays due to events beyond reasonable control (natural disasters, war, pandemic, infrastructure failures).

### 12.5 Entire Agreement
This Agreement, including Exhibits, constitutes entire agreement and supersedes all prior discussions.

### 12.6 Amendments
Amendments must be in writing, signed by both parties.

### 12.7 Severability
If any provision held invalid, remainder continues in effect.

### 12.8 Notices
Notices sent to:
- **Provider:** legal@continuuai.com and [physical address]
- **Customer:** [Customer email and physical address]

### 12.9 Counterparts
Agreement may be signed in counterparts (including electronic signatures).

---

## SIGNATURE

**CONTINUUAI, INC.**

Signature: ___________________________  
Name: [Authorized Signatory]  
Title: [Title]  
Date: _______________

**[CUSTOMER NAME]**

Signature: ___________________________  
Name: [Authorized Signatory]  
Title: [Title]  
Date: _______________

---

## EXHIBIT A: SUBPROCESSORS

| Subprocessor | Service | Location | Purpose |
|--------------|---------|----------|---------|
| AWS | Cloud Infrastructure | [Region] | Hosting, compute, storage |
| Stripe | Payment Processing | USA | Subscription billing |
| [Other] | [Service] | [Location] | [Purpose] |

**Last Updated:** [Date]

---

## EXHIBIT B: ACCEPTABLE USE POLICY

Customer shall not:
1. Use Service for illegal purposes
2. Upload malicious code or attempt to compromise security
3. Violate third-party rights (IP, privacy, etc.)
4. Impersonate others or provide false information
5. Attempt to reverse-engineer the Service
6. Use Service to store illegal, defamatory, or obscene content
7. Exceed reasonable usage (Provider will notify before enforcing)
8. Share access credentials with unauthorized users

---

## EXHIBIT C: DATA PROCESSING ADDENDUM (DPA)

*(For EU customers or those subject to GDPR)*

This Data Processing Addendum incorporates:
- Standard Contractual Clauses (SCCs) for EU data transfers
- GDPR compliance requirements
- Data subject rights procedures
- Security measures detail

*(Full DPA available as separate document)*

---

## NOTES FOR CUSTOMER LEGAL REVIEW

**Key Differentiators in This Contract:**
1. **Section 1.3** - Ethical termination right (Customer may leave if Service reduces judgment)
2. **Section 3** - Absolute Customer data ownership, zero cross-customer data usage
3. **Section 7.3** - Explicit disclaimer that Service doesn't guarantee better outcomes
4. **Section 8.4** - Customer termination right for ethical reasons
5. **Section 9.1** - Liability exceptions for data breaches (no cap)

**Questions for Provider:**
1. Confirm subprocessors in Exhibit A
2. Review data retention beyond 90-day backup window
3. Clarify "aggregate anonymized analytics" scope
4. Confirm Customer's data export format and frequency limits

---

**Document Control:**  
Template Version: 2.0  
Last Updated: January 2025  
Reviewed by: ContinuuAI Legal Counsel  
**Note:** This is a template. Final contract subject to negotiation and Customer-specific modifications.
