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
            
            pe.flags.ignore_mandatory = True
            pe.flags.ignore_validate = True

            pe.insert(ignore_permissions=True)
            
    return True