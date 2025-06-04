# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import nowdate

class SiteViolationCharges(Document):
    def validate(self):
        seen = set()
        for row in self.violation_charges:
            if row.supplier in seen:
                frappe.throw(f"Duplicate supplier '{row.supplier}' found in Violation Charges.")
            seen.add(row.supplier)
       
        self.set_paid_amounts()
        
    
    def set_paid_amounts(self):
        if not self.penalty_amount:
            return

        for row in self.violation_charges:
            if row.percentage_on_total and row.no_of_distribution:
                percentage = row.percentage_on_total or 0
                distribution = row.no_of_distribution or 1

                total_amount = (self.penalty_amount * percentage) / 100
                row.paid_amount = total_amount / distribution
                
            # frappe.msgprint(f"Set paid_amount to {row.paid_amount} for supplier {row.supplier}")


@frappe.whitelist()
def create_payment_entries_for_violation(docname):
    # Get the Site Violation Charges document
    doc = frappe.get_all("Payment Entry",filters={"site_violation_charges":docname})
    if doc:
        frappe.throw("Payment entry is already created")
    doc = frappe.get_doc("Site Violation Charges", docname)

    # Validate if penalty amount exists
    if not doc.penalty_amount:
        frappe.throw("Penalty amount is missing.")
    
    if not doc.project_site_violation:
        frappe.throw("Project Site Violation is not linked in this document.")

    project_violation_doc = frappe.get_doc("Project Site Violation", doc.project_site_violation)

    sadad_no = project_violation_doc.sadad_no
    payment_due_date = project_violation_doc.payment_due_date
    # frappe.throw(str(payment_due_date))

    # Loop through the violation charges child table
    for row in doc.violation_charges:
        supplier = row.supplier
        supplier_name = row.supplier_name
        supplier_account = row.supplier_account
        percentage = row.percentage_on_total or 0
        no_of_distribution = row.no_of_distribution or 1
        
        # Calculate the total amount to be paid based on the penalty and percentage
        total_amount = (doc.penalty_amount * percentage) / 100
        amount_per_distribution = total_amount / no_of_distribution

        # Create Payment Entries for each distribution
        for i in range(no_of_distribution):
            pe = frappe.new_doc("Payment Entry")
            pe.payment_type = "Receive"
            # pe.posting_date = doc.penalty_date
            pe.company = doc.company
            pe.party_type = "Supplier"
            pe.party = supplier
            pe.site_violation_charges = docname
            pe.party_name = supplier_name
            pe.paid_from = supplier_account
            pe.paid_to = doc.account_paid_to
            pe.paid_amount = amount_per_distribution
            pe.paid_from_account_currency = "SAR"
            pe.paid_to_account_currency = "SAR"
            pe.received_amount = amount_per_distribution
            pe.reference_no = sadad_no
            pe.reference_date = payment_due_date
            
            pe.flags.ignore_mandatory = True
            pe.flags.ignore_validate = True

            pe.insert(ignore_permissions=True)
            
            
    # Step 1: Count total payment entries created
    total_entries = sum(row.no_of_distribution or 1 for row in doc.violation_charges)

    # Step 2: Construct document URL
    site_url = frappe.utils.get_url()
    document_url = f"{site_url}/app/site-violation-charges/{doc.name}"

    # Step 3: Compose email
    subject = f"Payment Entries Created for Site Violation Charges: {doc.name}"
    message = f"""
    Dear Team,<br><br>

    A total of <b>{total_entries}</b> Payment Entries have been created for the Site Violation Charges document: 
    <a href="{document_url}">{doc.name}</a>.<br><br>

    You can view the document here: <a href="{document_url}">{document_url}</a><br><br>

    Regards,<br>
    System Notification
    """

    # Step 4: Fetch emails of users with specific roles
    roles_to_notify = ["Accounts Manager", "Finance Manager", "Accounts User"]
    recipients = []

    for role in roles_to_notify:
        users = frappe.get_all(
            "Has Role",
            filters={"role": role},
            fields=["parent"]
        )
        for user in users:
            user_email = frappe.db.get_value("User", user.parent, "email")
            if user_email and user_email not in recipients:
                recipients.append(user_email)
                
    # frappe.throw(str(recipients))

    # Step 5: Send the email
    if recipients:
        frappe.sendmail(
            recipients=recipients,
            subject=subject,
            message=message
        )

            
    return True